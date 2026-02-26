from dotenv import load_dotenv
load_dotenv()


import os
import asyncio
import tempfile
import feedparser
import requests
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS

from main import fetch_articles, build_pdf, scrape_article
from security import init_security, require_api_key, validate_feed_urls, check_url_safe

app = Flask(__name__)

_cors_origins = os.getenv("CORS_ORIGINS", "*")
CORS(app, origins=_cors_origins, supports_credentials=False)

limiter = init_security(app)

# Realistic browser headers — many RSS endpoints 403 bot user-agents
FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control":   "no-cache",
}


# ── Health ────────────────────────────────────────────────────────────────────
# Public — no auth, no tight rate limit.  Used by uptime monitors.

@app.get("/api/health")
@require_api_key
@limiter.limit("60/minute")
def health():
    return jsonify({"status": "ok"})


# ── Validate ──────────────────────────────────────────────────────────────────
# Auth-protected.  Tighter limit because it makes real outbound HTTP calls.

@app.post("/api/validate")
@require_api_key
@limiter.limit("30/hour")
def validate():
    body = request.get_json(silent=True) or {}
    url  = (body.get("url") or "").strip()

    if not url:
        return jsonify({"error": "A feed URL is required."}), 400

    # ── SSRF check before we touch the network ─────────────────────────────
    safe, reason = check_url_safe(url)
    if not safe:
        return jsonify({"error": f"URL rejected: {reason}"}), 400

    report = {
        "url":    url,
        "status": "ok",
        "checks": {
            "reachable":  {"ok": False, "detail": ""},
            "parseable":  {"ok": False, "detail": "", "entry_count": 0},
            "has_dates":  {"ok": False, "detail": ""},
            "scrapeable": {"ok": False, "detail": "", "sample_title": ""},
        },
        "sample_article": None,
    }

    # 1 — Reachable
    try:
        resp = requests.get(url, timeout=10, headers=FETCH_HEADERS)
        resp.raise_for_status()
        report["checks"]["reachable"] = {"ok": True, "detail": f"HTTP {resp.status_code}"}
    except requests.exceptions.Timeout:
        report["checks"]["reachable"] = {"ok": False, "detail": "Timed out after 10s"}
        report["status"] = "error"
        return jsonify(report)
    except requests.exceptions.RequestException as e:
        report["checks"]["reachable"] = {"ok": False, "detail": str(e)}
        report["status"] = "error"
        return jsonify(report)

    # 2 — Parseable
    try:
        feed    = feedparser.parse(url, agent=FETCH_HEADERS["User-Agent"])
        entries = feed.entries
        count   = len(entries)
        if feed.bozo and not entries:
            raise ValueError(str(feed.bozo_exception))
        report["checks"]["parseable"] = {
            "ok":          count > 0,
            "detail":      f"{count} {'entry' if count == 1 else 'entries'} found" if count > 0 else "No entries found",
            "entry_count": count,
        }
        if count == 0:
            report["status"] = "error"
            return jsonify(report)
    except Exception as e:
        report["checks"]["parseable"] = {"ok": False, "detail": str(e), "entry_count": 0}
        report["status"] = "error"
        return jsonify(report)

    # 3 — Has dates
    sample_size = min(len(entries), 10)
    dated = sum(
        1 for e in entries[:sample_size]
        if any(getattr(e, a, None) for a in ("published", "updated", "published_parsed", "updated_parsed"))
    )
    report["checks"]["has_dates"] = {
        "ok":    dated > 0,
        "detail": f"{dated}/{sample_size} entries have timestamps" if dated > 0 else "No date fields found",
    }
    if dated == 0 and report["status"] == "ok":
        report["status"] = "partial"

    # 4 — Scrapeable
    # Only scrape article URLs that also pass the SSRF check
    sample_entry = next(
        (e for e in entries[:5] if e.get("link") and check_url_safe(e["link"])[0]),
        None,
    )
    if not sample_entry:
        report["checks"]["scrapeable"] = {"ok": False, "detail": "No safe article links in feed", "sample_title": ""}
        report["status"] = "partial" if report["status"] == "ok" else report["status"]
    else:
        sample_url   = sample_entry.get("link", "")
        sample_title = sample_entry.get("title", "(No title)")
        scraped      = scrape_article(sample_url)
        if scraped["summary"]:
            report["checks"]["scrapeable"] = {"ok": True, "detail": "Article body extracted", "sample_title": sample_title}
            report["sample_article"] = {
                "title":   sample_title,
                "url":     sample_url,
                "image":   scraped["top_image"],
                "summary": scraped["summary"][:280] + ("…" if len(scraped["summary"]) > 280 else ""),
            }
        else:
            report["checks"]["scrapeable"] = {
                "ok":          False,
                "detail":      "Could not extract body (paywalled or JS-rendered?)",
                "sample_title": sample_title,
            }
            if report["status"] == "ok":
                report["status"] = "partial"

    all_ok = all(c["ok"] for c in report["checks"].values())
    any_ok = any(c["ok"] for c in report["checks"].values())
    report["status"] = "ok" if all_ok else ("partial" if any_ok else "error")

    return jsonify(report)


# ── Generate ──────────────────────────────────────────────────────────────────
# Most expensive endpoint — tightest rate limit.

@app.post("/api/generate")
@require_api_key
@limiter.limit("10/hour")
def generate():
    body      = request.get_json(silent=True) or {}
    feeds     = body.get("feeds", [])
    days_back = body.get("days_back", 3)

    # ── Input validation ───────────────────────────────────────────────────
    if not isinstance(days_back, int) or not (1 <= days_back <= 30):
        return jsonify({"error": "'days_back' must be an integer between 1 and 30."}), 400

    ok, err = validate_feed_urls(feeds)
    if not ok:
        return jsonify({"error": err}), 400

    # ── Scrape ────────────────────────────────────────────────────────────
    try:
        articles = fetch_articles(feeds, days_back=days_back)
    except Exception as e:
        return jsonify({"error": f"Scraping failed: {str(e)}"}), 500

    if not articles:
        return jsonify({"error": "No articles found in the requested time window."}), 404

    # ── Build PDF & stream it back (temp file always cleaned up) ──────────
    pdf_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            pdf_path = tmp.name
        asyncio.run(build_pdf(articles, output_path=pdf_path))
        return send_file(
            pdf_path,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="Tech_Weekly_Pro.pdf",
        )
    except Exception as e:
        return jsonify({"error": f"PDF generation failed: {str(e)}"}), 500
    finally:
        # Always clean up the temp file — even if send_file raises
        if pdf_path and os.path.exists(pdf_path):
            try:
                os.unlink(pdf_path)
            except OSError:
                pass


# ── Static (frontend) ─────────────────────────────────────────────────────────

@app.get("/")
def index():
    return send_from_directory("../frontend/dist", "index.html")

@app.get("/<path:path>")
def static_files(path):
    return send_from_directory("../frontend/dist", path)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5002)),
        debug=os.getenv("FLASK_DEBUG", "false") == "true",
    )