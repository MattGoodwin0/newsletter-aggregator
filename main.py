import feedparser
import asyncio
import datetime
import requests
from bs4 import BeautifulSoup
from newspaper import Article
from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright
import unicodedata


def clean_text(text):
    if not text:
        return ""
    # Normalize unicode to remove "Smart Quotes" and replace with standard ones
    # or just clean up the byte-order-mark issues.
    text = unicodedata.normalize("NFKC", text)
    # Manual fix for common tech-scraper artifacts
    replacements = {
        "\u2013": "-",  # en dash
        "\u2014": "-",  # em dash
        "\u2018": "'",  # left single quote
        "\u2019": "'",  # right single quote
        "\u201c": '"',  # left double quote
        "\u201d": '"',  # right double quote
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.strip()


def get_source_content(url):
    """Visits the actual news source to get the lead image and body text."""
    try:
        scraper = Article(url)
        scraper.download()
        scraper.parse()
        # Split text into paragraphs and take top 3
        paragraphs = [
            p.strip() for p in scraper.text.split("\n") if len(p.strip()) > 50
        ]
        return scraper.top_image, paragraphs[:3]
    except Exception as e:
        print(f"Error scraping source {url}: {e}")
        return None, []


def fetch_digest_data(feed_url, limit=3):
    print(f"--- Fetching {limit} digest pages from RSS ---")
    feed = feedparser.parse(feed_url)
    all_articles = []

    for entry in feed.entries[:limit]:
        print(f"\nProcessing Digest: {entry.title}")
        res = requests.get(entry.link)
        res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, "html.parser")

        # Techpresso uses <h2> for article titles in the digest
        for h2 in soup.find_all("h2"):

            title_text = clean_text(
                h2.get_text().replace("[LINK]", "")
            )  # Find the [LINK] anchor tag
            link_tag = h2.find("a", href=True)
            if not link_tag:
                # Sometimes the link is the next sibling
                link_tag = h2.find_next("a", href=True)

            if (
                not link_tag
                or "dupple.com" in link_tag["href"]
                and "archives" in link_tag["href"]
            ):
                continue

            source_url = link_tag["href"]

            # --- ATTEMPT 1: Scrape Bullets from Digest ---
            bullets = []
            next_node = h2.find_next_sibling()
            # Search for list items or text blocks until the next heading
            while next_node and next_node.name != "h2":
                if next_node.name in ["ul", "ol"]:
                    bullets = [li.get_text().strip() for li in next_node.find_all("li")]
                    break
                # Handle cases where bullets are just paragraphs starting with dots/dashes
                if next_node.name == "p" and (
                    next_node.text.strip().startswith("•")
                    or next_node.text.strip().startswith("*")
                ):
                    bullets.append(next_node.text.strip().lstrip("•* "))
                next_node = next_node.find_next_sibling()

            # --- ATTEMPT 2: Fall back to Source Scrape ---
            image, content = get_source_content(source_url)

            # Use digest bullets if found, otherwise use source paragraphs
            final_paragraphs = bullets if bullets else content

            if final_paragraphs:
                print(f"  [+] Added: {title_text[:50]}...")
                all_articles.append(
                    {
                        "title": title_text,
                        "image": image,
                        "paragraphs": final_paragraphs,
                        "source_url": source_url,
                        "date": datetime.datetime.now().strftime("%B %d, %Y"),
                    }
                )

    return all_articles


async def create_magazine():
    limit = int(input("How many archive days to check? "))
    articles = fetch_digest_data("https://www.dupple.com/techpresso-archives/rss.xml", limit=limit)
    
    if not articles:
        print("No articles found. Check if the RSS feed structure has changed.")
        return
    
    # 1. Set up the Template Environment
    file_loader = FileSystemLoader('templates')
    env = Environment(loader=file_loader)
    
    # 2. Load the CSS
    with open("./templates/master.css", "r", encoding="utf-8") as f:
        css_styling = f.read()

    # 3. Render the Master Layout
    # This automatically finds cover.html, article.html etc. via the {% include %} tags
    master_template = env.get_template('layout.html')
    final_html = master_template.render(
        articles=articles,
        custom_css=css_styling,
        date=datetime.datetime.now()
    )

    # 4. PDF Generation
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(final_html)
        await page.wait_for_timeout(3000) # Wait for images
        await page.pdf(path="Tech_Weekly_Pro.pdf", format="A4", print_background=True)
        await browser.close()

    print("Magazine generated successfully.")

if __name__ == "__main__":
    asyncio.run(create_magazine())
