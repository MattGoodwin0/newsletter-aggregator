"""
Serifdigest API Server
"""

import os
import asyncio
import tempfile
import feedparser
import requests
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from main import fetch_articles, build_pdf, scrape_article

app = Flask(__name__)

# In dev, allow all origins. Lock down via CORS_ORIGINS env var in production.
_cors_origins = os.getenv("CORS_ORIGINS", "*")
CORS(app, origins=_cors_origins, supports_credentials=False)

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


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/api/validate")
def validate():
    body = request.get_json(silent=True) or {}
    url  = (body.get("url") or "").strip()

    if not url:
        return jsonify({"error": "A feed URL is required."}), 400

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
    sample_entry = next((e for e in entries[:5] if e.get("link")), None)
    if not sample_entry:
        report["checks"]["scrapeable"] = {"ok": False, "detail": "No article links in feed", "sample_title": ""}
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
                "ok": False,
                "detail": "Could not extract body (paywalled or JS-rendered?)",
                "sample_title": sample_title,
            }
            if report["status"] == "ok":
                report["status"] = "partial"

    all_ok = all(c["ok"] for c in report["checks"].values())
    any_ok = any(c["ok"] for c in report["checks"].values())
    report["status"] = "ok" if all_ok else ("partial" if any_ok else "error")

    return jsonify(report)


@app.post("/api/generate")
def generate():
    body      = request.get_json(silent=True) or {}
    feeds     = body.get("feeds", [])
    days_back = int(body.get("days_back", 3))

    if not feeds:
        return jsonify({"error": "At least one feed URL is required."}), 400
    if not (1 <= days_back <= 30):
        return jsonify({"error": "'days_back' must be between 1 and 30."}), 400

    try:
        articles = fetch_articles(feeds, days_back=days_back)
    except Exception as e:
        return jsonify({"error": f"Scraping failed: {str(e)}"}), 500

    if not articles:
        return jsonify({"error": "No articles found."}), 404

    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            pdf_path = tmp.name
        asyncio.run(build_pdf(articles, output_path=pdf_path))
    except Exception as e:
        return jsonify({"error": f"PDF generation failed: {str(e)}"}), 500

    return send_file(pdf_path, mimetype="application/pdf", as_attachment=True, download_name="Tech_Weekly_Pro.pdf")

@app.get("/")
def index():
    return send_from_directory("../frontend/dist", "index.html")

@app.get("/<path:path>")
def static_files(path):
    return send_from_directory("../frontend/dist", path)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5002)), debug=os.getenv("FLASK_DEBUG", "false") == "true")
