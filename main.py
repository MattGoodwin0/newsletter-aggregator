import feedparser
import asyncio
import datetime
import requests
import unicodedata
import nltk
from typing import Optional, List, Dict
from bs4 import BeautifulSoup
from newspaper import Article
from email.utils import parsedate_to_datetime
from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright


# ── NLTK bootstrap (run once, safe to repeat) ─────────────────────────────────

for _resource in ("punkt", "punkt_tab", "stopwords"):
    try:
        nltk.download(_resource, quiet=True)
    except Exception:
        pass


# ── Config ────────────────────────────────────────────────────────────────────

RSS_FEEDS = [
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml",
    "https://www.wired.com/feed/rss",
    # Add as many feeds as you like
]

DAYS_BACK = 3          # How many days of articles to fetch
SUMMARY_SENTENCES = 3  # Fallback paragraph count when NLP summary is unavailable


# ── Helpers ───────────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    """Normalise unicode and replace typographic characters."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    replacements = {
        "\u2013": "-", "\u2014": "-",
        "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.strip()


def parse_entry_date(entry) -> Optional[datetime.datetime]:
    """Return a timezone-aware datetime from an RSS entry, or None."""
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


def scrape_article(url: str) -> Dict:
    """
    Fetch the article at *url* and return:
      top_image : str | None
      summary   : str   (NLP summary or first N paragraphs)
      authors   : list[str]
    """
    result: Dict = {"top_image": None, "summary": "", "authors": []}
    try:
        art = Article(url)
        art.download()
        art.parse()

        result["top_image"] = art.top_image or None
        result["authors"]   = art.authors or []

        # Try NLP summary; gracefully degrade if NLTK data is still missing
        try:
            art.nlp()
            if art.summary and len(art.summary) > 80:
                result["summary"] = clean_text(art.summary)
        except Exception:
            pass  # NLP failed — fall through to paragraph fallback

        # Paragraph fallback
        if not result["summary"]:
            paragraphs = [
                p.strip() for p in art.text.split("\n") if len(p.strip()) > 60
            ]
            result["summary"] = clean_text(" ".join(paragraphs[:SUMMARY_SENTENCES]))

    except Exception as e:
        print(f"  [!] Could not scrape {url}: {e}")

    return result


# ── Core fetch ────────────────────────────────────────────────────────────────

def fetch_articles(feeds: List[str], days_back: int) -> List[Dict]:
    """
    Iterate over every feed, filter to the last *days_back* days,
    scrape each article, and return a unified list of article dicts.
    """
    cutoff = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(days=days_back)
    all_articles: List[Dict] = []

    for feed_url in feeds:
        print(f"\n=== Feed: {feed_url} ===")
        feed = feedparser.parse(feed_url)
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
                "source_url": source_url,   # alias expected by Jinja templates
                "date":       pub_date.strftime("%B %d, %Y") if pub_date else "Unknown",
                "authors":    scraped["authors"],
                "image":      scraped["top_image"],
                "paragraphs": [scraped["summary"]] if scraped["summary"] else [],
            })

    print(f"\n✓ Collected {len(all_articles)} articles from {len(feeds)} feed(s).")
    return all_articles


# ── PDF generation ────────────────────────────────────────────────────────────

async def build_pdf(articles: List[Dict]) -> None:
    """Render Jinja2 templates and export a PDF via Playwright."""
    file_loader = FileSystemLoader("templates")
    env = Environment(loader=file_loader)

    with open("./templates/master.css", "r", encoding="utf-8") as f:
        css_styling = f.read()

    master_template = env.get_template("layout.html")
    final_html = master_template.render(
        articles=articles,
        custom_css=css_styling,
        date=datetime.datetime.now(),
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page    = await browser.new_page()
        await page.set_content(final_html)
        await page.wait_for_timeout(3000)   # allow images to load
        await page.pdf(
            path="Tech_Weekly_Pro.pdf",
            format="A4",
            print_background=True,
        )
        await browser.close()

    print("✓ Magazine PDF saved as Tech_Weekly_Pro.pdf")


# ── Entry point ───────────────────────────────────────────────────────────────

async def create_magazine() -> None:
    raw  = input(f"Days back to fetch? [default {DAYS_BACK}]: ").strip()
    days = int(raw) if raw else DAYS_BACK

    articles = fetch_articles(RSS_FEEDS, days_back=days)

    if not articles:
        print("No articles found in the requested window.")
        return

    # Quick stdout preview
    print("\n" + "=" * 70)
    for i, a in enumerate(articles, 1):
        summary_preview = a["paragraphs"][0][:200] if a["paragraphs"] else "N/A"
        print(f"\n[{i}] {a['title']}")
        print(f"    Feed    : {a['feed']}")
        print(f"    Date    : {a['date']}")
        print(f"    Authors : {', '.join(a['authors']) or 'N/A'}")
        print(f"    URL     : {a['url']}")
        print(f"    Summary : {summary_preview}...")

    await build_pdf(articles)


if __name__ == "__main__":
    asyncio.run(create_magazine())