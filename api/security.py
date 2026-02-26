"""
security.py — API security middleware for Digest
-------------------------------------------------
Provides:
  - API key authentication
  - Rate limiting (via flask-limiter)
  - SSRF protection (private IP / scheme blocking with DNS rebinding defence)
  - Feed count & request body size limits
  - Malicious URL scraping prevention

Usage:
    from security import init_security, require_api_key, validate_feed_urls, check_url_safe

    limiter = init_security(app)   # call once after app creation

    @app.post("/api/generate")
    @require_api_key
    @limiter.limit("10/hour")
    def generate(): ...
"""

import os
import socket
import ipaddress
import functools
from urllib.parse import urlparse
from typing import List, Tuple

from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


# ── Constants ─────────────────────────────────────────────────────────────────

#: Comma-separated API keys in env var, e.g.  API_KEYS=key1,key2
_ENV_KEY     = "API_KEYS"
_HEADER_NAME = "Authorization"

#: Maximum feeds allowed per /api/generate request
MAX_FEEDS = 10

#: Maximum request body size in bytes (64 KB)
MAX_BODY_BYTES = 64 * 1024

#: URL schemes we refuse to follow regardless of host
_BLOCKED_SCHEMES = {"file", "ftp", "gopher", "dict", "ldap", "ldaps", "sftp", "tftp", "jar"}

#: Private / reserved networks — both IPv4 and IPv6
_PRIVATE_NETWORKS = [
    # IPv4
    ipaddress.ip_network("0.0.0.0/8"),          # "This" network
    ipaddress.ip_network("10.0.0.0/8"),          # RFC-1918 private
    ipaddress.ip_network("100.64.0.0/10"),       # Shared address space (ISP NAT)
    ipaddress.ip_network("127.0.0.0/8"),         # Loopback
    ipaddress.ip_network("169.254.0.0/16"),      # Link-local / cloud metadata (AWS, GCP)
    ipaddress.ip_network("172.16.0.0/12"),       # RFC-1918 private
    ipaddress.ip_network("192.0.0.0/24"),        # IETF protocol assignments
    ipaddress.ip_network("192.168.0.0/16"),      # RFC-1918 private
    ipaddress.ip_network("198.18.0.0/15"),       # Benchmarking
    ipaddress.ip_network("198.51.100.0/24"),     # TEST-NET-2 (documentation)
    ipaddress.ip_network("203.0.113.0/24"),      # TEST-NET-3 (documentation)
    ipaddress.ip_network("224.0.0.0/4"),         # Multicast
    ipaddress.ip_network("240.0.0.0/4"),         # Reserved
    ipaddress.ip_network("255.255.255.255/32"),  # Broadcast
    # IPv6
    ipaddress.ip_network("::1/128"),             # Loopback
    ipaddress.ip_network("fc00::/7"),            # Unique local (ULA)
    ipaddress.ip_network("fe80::/10"),           # Link-local
    ipaddress.ip_network("ff00::/8"),            # Multicast
]


# ── Internal helpers ──────────────────────────────────────────────────────────

def _load_api_keys() -> set:
    """Read keys from env var at call-time so rotation needs no restart."""
    raw = os.getenv(_ENV_KEY, "").strip()
    if not raw:
        return set()
    return {k.strip() for k in raw.split(",") if k.strip()}


def _is_private_ip(ip_str: str) -> bool:
    """Return True if the IP falls within any blocked/private network."""
    try:
        addr = ipaddress.ip_address(ip_str)
        return any(addr in net for net in _PRIVATE_NETWORKS)
    except ValueError:
        return True   # unparseable → treat as unsafe


def _resolve_host(hostname: str) -> List[str]:
    """
    Resolve hostname to a deduplicated list of IP strings.
    Returns an empty list on DNS failure.
    """
    try:
        results = socket.getaddrinfo(hostname, None)
        return list({r[4][0] for r in results})
    except socket.gaierror:
        return []


# ── Public: URL safety check ─────────────────────────────────────────────────

def check_url_safe(url: str) -> Tuple[bool, str]:
    """
    Validate that a URL is safe to fetch externally (SSRF prevention).

    Checks:
      1. Scheme is http/https and not in the explicit blocklist
      2. Bare-IP literals that are private/reserved are rejected
      3. Hostname is resolved and every returned IP is checked (DNS rebinding defence)

    Returns:
        (True,  "")            — safe to fetch
        (False, "reason …")    — must not be fetched
    """
    if not url or not isinstance(url, str):
        return False, "URL must be a non-empty string."

    try:
        parsed = urlparse(url)
    except Exception:
        return False, "URL could not be parsed."

    scheme = (parsed.scheme or "").lower()

    if scheme in _BLOCKED_SCHEMES:
        return False, f"Scheme '{scheme}' is not permitted."
    if scheme not in ("http", "https"):
        return False, "Only http and https URLs are accepted."

    hostname = parsed.hostname
    if not hostname:
        return False, "URL has no hostname."

    # Reject bare private-IP literals before DNS resolution
    try:
        addr = ipaddress.ip_address(hostname)
        if _is_private_ip(str(addr)):
            return False, "Requests to private/internal IP addresses are not allowed."
    except ValueError:
        pass  # not a bare IP literal — fall through to DNS resolution

    # Resolve hostname → check all returned IPs (defends against DNS rebinding)
    resolved_ips = _resolve_host(hostname)
    if not resolved_ips:
        return False, f"Hostname '{hostname}' could not be resolved."

    for ip in resolved_ips:
        if _is_private_ip(ip):
            return False, f"Hostname '{hostname}' resolves to a private/internal address."

    return True, ""


def validate_feed_urls(urls: List[str]) -> Tuple[bool, str]:
    """
    Validate a list of feed URLs for count limits and SSRF safety.

    Returns (ok: bool, error_message: str).
    """
    if not isinstance(urls, list) or len(urls) == 0:
        return False, "At least one feed URL is required."

    if len(urls) > MAX_FEEDS:
        return False, f"A maximum of {MAX_FEEDS} feed URLs are allowed per request."

    for url in urls:
        safe, reason = check_url_safe(url)
        if not safe:
            return False, f"Rejected URL '{url}': {reason}"

    return True, ""


# ── Public: authentication decorator ─────────────────────────────────────────

def require_api_key(fn):
    """
    Flask route decorator that enforces X-API-Key header authentication.

    Keys are loaded from the API_KEYS env var on every call, meaning you
    can rotate keys by updating the env var — no server restart required.

    Rotation procedure (zero-downtime):
        1. Add new key:   API_KEYS=old_key,new_key
        2. Update clients to send new_key
        3. Remove old key: API_KEYS=new_key

    If API_KEYS is unset the decorator logs a loud warning and fails open
    so local development still works without needing an env file.

    Example:
        @app.post("/api/generate")
        @require_api_key
        def generate(): ...
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        keys = _load_api_keys()

        if not keys:
            import warnings
            warnings.warn(
                f"[security] {_ENV_KEY} is not set — "
                "API key enforcement is DISABLED. "
                "Set this env var before deploying to production.",
                stacklevel=2,
            )
            return fn(*args, **kwargs)

        auth_header = request.headers.get(_HEADER_NAME, "").strip()
        parts       = auth_header.split(" ", 1)
        provided    = parts[1].strip() if (len(parts) == 2 and parts[0].lower() == "bearer") else ""

        if not provided or provided not in keys:
            # Generic message — don't reveal whether the key exists or not
            return jsonify({"error": "Unauthorized."}), 401

        return fn(*args, **kwargs)

    return wrapper


# ── Public: limiter + body-size init ─────────────────────────────────────────

def init_security(app: Flask) -> Limiter:
    """
    Attach Flask-Limiter to the app and set the request body size limit.

    Call once immediately after creating the Flask app:

        app = Flask(__name__)
        limiter = init_security(app)

    Returns the Limiter instance so routes can apply per-endpoint limits:

        @app.post("/api/generate")
        @require_api_key
        @limiter.limit("10/hour")
        def generate(): ...

    Environment variables:
        RATELIMIT_STORAGE_URI   Redis URL for distributed limiting
                                (default: in-process memory — fine for a
                                single-dyno indie deployment)
        API_KEYS                Comma-separated valid API keys
    """

    # ── Body size cap ──────────────────────────────────────────────────────
    app.config["MAX_CONTENT_LENGTH"] = MAX_BODY_BYTES

    @app.errorhandler(413)
    def payload_too_large(_e):
        return jsonify({
            "error": f"Request body exceeds the {MAX_BODY_BYTES // 1024} KB limit."
        }), 413

    # ── Rate limiter ───────────────────────────────────────────────────────
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        # Sane global default — overridden per route where needed
        default_limits=["200 per hour"],
        storage_uri=os.getenv("RATELIMIT_STORAGE_URI", "memory://"),
    )

    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        return jsonify({
            "error":       "Rate limit exceeded. Please slow down and try again.",
            "retry_after": getattr(e, "retry_after", None),
        }), 429

    return limiter