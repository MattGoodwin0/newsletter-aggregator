"""
security.py — API security middleware for Digest
-------------------------------------------------
Provides:
  - CSRF token authentication (single-use + expiring)
  - Rate limiting via flask-limiter
  - SSRF protection (private IP / scheme blocking + DNS rebinding defence)
  - Feed count and request body size limits
  - Malicious URL scraping prevention

Typical setup in server.py:

    from security import init_security, issue_csrf_token, require_csrf
    from security import validate_feed_urls, check_url_safe

    limiter = init_security(app)

    @app.get("/api/csrf-token")
    @limiter.limit("30/minute")
    def get_token():
        return jsonify({"token": issue_csrf_token()})

    @app.post("/api/generate")
    @require_csrf
    @limiter.limit("10/hour")
    def generate():
        ...
"""

import os
import time
import secrets
import socket
import ipaddress
import functools
from urllib.parse import urlparse
from typing import Dict, List, Tuple

from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


# ── Constants ─────────────────────────────────────────────────────────────────

#: How long (seconds) a CSRF token remains valid after issue.
#: User must complete their request within this window.
TOKEN_TTL_SECONDS = 300   # 5 minutes

#: Header the Vite app sends the token in.
CSRF_HEADER = "X-CSRF-Token"

#: Maximum feeds allowed per /api/generate request.
MAX_FEEDS = 10

#: Maximum request body size (64 KB) — stops payload bloat attacks.
MAX_BODY_BYTES = 64 * 1024

#: URL schemes we refuse to follow regardless of host.
_BLOCKED_SCHEMES = {"file", "ftp", "gopher", "dict", "ldap", "ldaps", "sftp", "tftp", "jar"}

#: Private / reserved networks — both IPv4 and IPv6.
_PRIVATE_NETWORKS = [
    # IPv4
    ipaddress.ip_network("0.0.0.0/8"),          # "This" network
    ipaddress.ip_network("10.0.0.0/8"),          # RFC-1918 private
    ipaddress.ip_network("100.64.0.0/10"),       # Shared address space (ISP NAT)
    ipaddress.ip_network("127.0.0.0/8"),         # Loopback
    ipaddress.ip_network("169.254.0.0/16"),      # Link-local / AWS & GCP metadata
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


# ── CSRF token store ──────────────────────────────────────────────────────────
#
# Simple in-memory dict: { token: expires_at_unix_timestamp }
# Fine for a single-dyno deployment. If you ever scale to multiple dynos,
# swap this for a Redis-backed store using RATELIMIT_STORAGE_URI.

_token_store: Dict[str, float] = {}


def _purge_expired_tokens() -> None:
    """Remove stale tokens from the store (called on every issue + verify)."""
    now = time.time()
    expired = [t for t, exp in _token_store.items() if exp < now]
    for t in expired:
        del _token_store[t]


def issue_csrf_token() -> str:
    """
    Generate a new single-use CSRF token, store it with an expiry timestamp,
    and return the token string for the client.

    Call this inside your /api/csrf-token route:

        @app.get("/api/csrf-token")
        @limiter.limit("30/minute")
        def get_token():
            return jsonify({"token": issue_csrf_token()})
    """
    _purge_expired_tokens()
    token = secrets.token_hex(32)
    _token_store[token] = time.time() + TOKEN_TTL_SECONDS
    return token


def _consume_csrf_token(token: str) -> bool:
    """
    Validate and immediately consume a CSRF token (one-time use).

    Returns True if the token was valid and unexpired, False otherwise.
    """
    _purge_expired_tokens()

    if not token or token not in _token_store:
        return False

    if time.time() > _token_store[token]:
        del _token_store[token]
        return False

    # Valid — consume it so it can never be reused
    del _token_store[token]
    return True


# ── CSRF decorator ────────────────────────────────────────────────────────────

def require_csrf(fn):
    """
    Flask route decorator that enforces single-use CSRF token authentication.

    The Vite app must:
      1. Fetch a token from GET /api/csrf-token
      2. Include it as:  X-CSRF-Token: <token>
      3. Use it within TOKEN_TTL_SECONDS (default 5 minutes)

    Tokens are single-use — consumed on first valid use, preventing replays.
    Expired tokens in the store are purged automatically on each call.

    Example:
        @app.post("/api/generate")
        @require_csrf
        @limiter.limit("10/hour")
        def generate(): ...
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        token = request.headers.get(CSRF_HEADER, "").strip()

        if not _consume_csrf_token(token):
            return jsonify({"error": "Unauthorized."}), 401

        return fn(*args, **kwargs)

    return wrapper


# ── SSRF protection ───────────────────────────────────────────────────────────

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


def check_url_safe(url: str) -> Tuple[bool, str]:
    """
    Validate that a URL is safe to fetch externally (SSRF prevention).

    Checks:
      1. Scheme is http/https and not in the explicit blocklist
      2. Bare IP literals that are private/reserved are rejected immediately
      3. Hostname is resolved and every returned IP is checked
         (defends against DNS rebinding attacks)

    Returns:
        (True,  "")           — safe to fetch
        (False, "reason …")   — must not be fetched
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

    # Resolve hostname → check all returned IPs (DNS rebinding defence)
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


# ── Flask-Limiter init ────────────────────────────────────────────────────────

def init_security(app: Flask) -> Limiter:
    """
    Attach Flask-Limiter to the app and enforce a request body size limit.

    Call once immediately after creating the Flask app:

        app = Flask(__name__)
        limiter = init_security(app)

    Returns the Limiter instance so routes can apply per-endpoint overrides:

        @app.post("/api/generate")
        @require_csrf
        @limiter.limit("10/hour")
        def generate(): ...

    Environment variables:
        RATELIMIT_STORAGE_URI   Redis URL for distributed rate limiting.
                                Defaults to in-process memory — perfectly
                                fine for a single-dyno indie deployment.
        FLASK_SECRET_KEY        Required for session support. Generate with:
                                  openssl rand -hex 32
    """

    # Warn loudly if secret key is missing
    if not app.secret_key and not os.getenv("FLASK_SECRET_KEY"):
        import warnings
        warnings.warn(
            "[security] FLASK_SECRET_KEY is not set. "
            "Set this env var before deploying to production.",
            stacklevel=2,
        )
    app.secret_key = app.secret_key or os.getenv("FLASK_SECRET_KEY")

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