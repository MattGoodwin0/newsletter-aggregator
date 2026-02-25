"""
Serifdigest — Core scraper & PDF builder
------------------------------------
Callable directly (CLI) or imported by server.py (API mode).
"""

import feedparser
import asyncio
import datetime
import unicodedata
import nltk
import os
from typing import Optional, List, Dict
from newspaper import Article
from email.utils import parsedate_to_datetime
from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright
import requests
from bs4 import BeautifulSoup

# ── NLTK bootstrap ────────────────────────────────────────────────────────────

for _resource in ("punkt", "punkt_tab", "stopwords"):
    try:
        nltk.download(_resource, quiet=True)
    except Exception:
        pass


# ── Config (CLI defaults — overridden by API caller) ─────────────────────────

DEFAULT_FEEDS = [
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml",
    "https://www.wired.com/feed/rss",
]

DEFAULT_DAYS_BACK      = 3
DEFAULT_SUMMARY_SENTENCES = 3
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
DEFAULT_OUTPUT = os.path.join(os.path.dirname(__file__), "outputs", "Tech_Weekly_Pro.pdf")


# ── Helpers ───────────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    for old, new in {
        "\u2013": "-", "\u2014": "-",
        "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"',
    }.items():
        text = text.replace(old, new)
    return text.strip()


def parse_entry_date(entry) -> Optional[datetime.datetime]:
    for attr in ("published", "updated"):
        raw = getattr(entry, attr, None)
        if raw:
            try:
                return parsedate_to_datetime(raw)
            except Exception:
                pass
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            try:
                return datetime.datetime(*parsed[:6], tzinfo=datetime.timezone.utc)
            except Exception:
                pass
    return None




META_PRIORITY = [
    "og:description",
    "twitter:description",
    "description"
]

AUTHOR_META_KEYS = [
    "author",
    "article:author"
]

IMAGE_META_KEYS = [
    "og:image",
    "twitter:image"
]

TITLE_META_KEYS = [
    "og:title",
    "twitter:title"
]


def extract_meta(soup: BeautifulSoup, keys):
    for key in keys:
        tag = soup.find("meta", property=key) or soup.find("meta", attrs={"name": key})
        if tag and tag.get("content"):
            return tag["content"].strip()
    return None


def extract_all_meta_authors(soup: BeautifulSoup):
    authors = set()
    for key in AUTHOR_META_KEYS:
        for tag in soup.find_all("meta", attrs={"name": key}) + soup.find_all("meta", property=key):
            if tag.get("content"):
                authors.add(tag["content"].strip())
    return list(authors)


def scrape_article(url: str, summary_sentences: int = DEFAULT_SUMMARY_SENTENCES) -> Dict:
    result: Dict = {
        "title": None,
        "top_image": None,
        "summary": "",
        "authors": [],
        "published_at": None,
        "site_name": None
    }

    try:
        # --- Fetch raw HTML first ---
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        }
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # --- META TAG EXTRACTION (PRIMARY) ---
        result["title"]       = extract_meta(soup, TITLE_META_KEYS)
        result["summary"]     = extract_meta(soup, META_PRIORITY) or ""
        result["top_image"]   = extract_meta(soup, IMAGE_META_KEYS)
        result["site_name"]   = extract_meta(soup, ["og:site_name"])
        result["published_at"] = extract_meta(
            soup,
            ["article:published_time", "og:published_time", "pubdate"]
        )
        result["authors"] = extract_all_meta_authors(soup)

        if result["summary"]:
            result["summary"] = clean_text(result["summary"])

        # --- NEWSPAPER3K FALLBACK ---
        art = Article(url)
        art.download(input_html=resp.text)
        art.parse()

        result["title"]     = result["title"] or art.title or None
        result["top_image"] = result["top_image"] or art.top_image or None
        result["authors"]   = result["authors"] or art.authors or []

        # --- NLP ONLY IF STILL NO SUMMARY ---
        if not result["summary"]:
            try:
                art.nlp()
                if art.summary and len(art.summary) > 80:
                    result["summary"] = clean_text(art.summary)
            except Exception:
                pass

        # --- TEXT FALLBACK ---
        if not result["summary"]:
            paragraphs = [
                p.strip()
                for p in art.text.split("\n")
                if len(p.strip()) > 60
            ]
            result["summary"] = clean_text(
                " ".join(paragraphs[:summary_sentences])
            )

    except Exception as e:
        print(f"  [!] Could not scrape {url}: {e}")

    return result

# ── Core fetch ────────────────────────────────────────────────────────────────

def fetch_articles(feeds: List[str], days_back: int = DEFAULT_DAYS_BACK) -> List[Dict]:
    cutoff = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=days_back)
    all_articles: List[Dict] = []

    for feed_url in feeds:
        print(f"\n=== Feed: {feed_url} ===")
        feed       = feedparser.parse(feed_url)
        feed_title = feed.feed.get("title", feed_url)

        for entry in feed.entries:
            pub_date = parse_entry_date(entry)

            if pub_date is not None and pub_date < cutoff:
                continue
            if pub_date is None:
                print(f"  [?] No date for '{entry.get('title', '(no title)')}' — including anyway")

            title      = clean_text(entry.get("title", "(No title)"))
            source_url = entry.get("link", "")

            print(f"  Scraping: {title[:70]}...")
            scraped = scrape_article(source_url)

            all_articles.append({
                "feed":       feed_title,
                "title":      title,
                "url":        source_url,
                "source_url": source_url,
                "date":       pub_date.strftime("%B %d, %Y") if pub_date else "Unknown",
                "authors":    scraped["authors"],
                "image":      scraped["top_image"],
                "paragraphs": [scraped["summary"]] if scraped["summary"] else [],
            })

    print(f"\n✓ Collected {len(all_articles)} articles from {len(feeds)} feed(s).")
    return all_articles


# ── PDF generation ────────────────────────────────────────────────────────────

async def build_pdf(articles: List[Dict], output_path: str = DEFAULT_OUTPUT) -> str:
    """Render Jinja2 templates and export a PDF via Playwright. Returns output_path."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

    css_path = os.path.join(TEMPLATES_DIR, "master.css")
    with open(css_path, "r", encoding="utf-8") as f:
        css_styling = f.read()

    final_html = env.get_template("layout.html").render(
        articles=articles,
        custom_css=css_styling,
        date=datetime.datetime.now(),
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page    = await browser.new_page()
        await page.set_content(final_html)
        await page.wait_for_timeout(3000)
        await page.pdf(path=output_path, format="A4", print_background=True)
        await browser.close()

    print(f"✓ PDF saved → {output_path}", flush=True)
    return output_path


# ── CLI entry point ───────────────────────────────────────────────────────────

async def _cli() -> None:
    raw  = input(f"Days back to fetch? [default {DEFAULT_DAYS_BACK}]: ").strip()
    days = int(raw) if raw else DEFAULT_DAYS_BACK

    articles = fetch_articles(DEFAULT_FEEDS, days_back=days)

    if not articles:
        print("No articles found in the requested window.")
        return

    print("\n" + "=" * 70)
    for i, a in enumerate(articles, 1):
        preview = a["paragraphs"][0][:200] if a["paragraphs"] else "N/A"
        print(f"\n[{i}] {a['title']}")
        print(f"    Feed    : {a['feed']}")
        print(f"    Date    : {a['date']}")
        print(f"    Authors : {', '.join(a['authors']) or 'N/A'}")
        print(f"    URL     : {a['url']}")
        print(f"    Summary : {preview}...")

    await build_pdf(articles)


if __name__ == "__main__":
    asyncio.run(_cli())
