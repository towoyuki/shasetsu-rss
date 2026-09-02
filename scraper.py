import os
import re
import json
import logging
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
from feedparser import parse as parse_feed
from dateutil.parser import parse as parse_date

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

FEED_FILE = "feed.xml"
TEST_FEED_FILE = "feed-test.xml"
MAX_ITEMS = 200

def fetch_html(url):
    try:
        logging.info(f"Fetching HTML: {url}")
        res = requests.get(url, headers=HEADERS, timeout=8)
        res.raise_for_status()
        res.encoding = res.apparent_encoding or "utf-8"
        return BeautifulSoup(res.text, "html.parser")
    except Exception as e:
        logging.error(f"Error fetching {url}: {e}")
        return None

def fetch_article_detail(url):
    soup = fetch_html(url)
    if not soup:
        return "", None
    
    img_url = None
    og_img = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
    if og_img and og_img.get("content"):
        img_url = og_img["content"]

    paragraphs = []
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if text and len(text) > 20 and not re.search(r"PR|広告|利用規約|著作権|無断転載", text):
            paragraphs.append(text)
    
    body_text = "\n\n".join(paragraphs[:5]) if paragraphs else ""
    return body_text, img_url

def parse_asahi():
    logging.info("Parsing Asahi...")
    items = []
    url = "https://www.asahi.com/rensai/list.html?id=16"
    soup = fetch_html(url)
    if not soup:
        return items

    for a in soup.find_all("a", href=True):
        href = a["href"]
        title = a.get_text(strip=True)
        if "/articles/" in href and len(title) > 8:
            full_url = href if href.startswith("http") else "https://www.asahi.com" + href
            if not any(item["link"] == full_url for item in items):
                cleaned_title = re.sub(r"^（社説）\s*", "", title)
                cleaned_title = cleaned_title.split("･･･[続きを読む]")[0].strip()
                body_text, img_url = fetch_article_detail(full_url)
                items.append({
                    "title": f"[朝日] {cleaned_title}",
                    "link": full_url,
                    "description": body_text or cleaned_title,
                    "image": img_url,
                    "pub_date": datetime.now(timezone.utc)
                })
                if len(items) >= 2:
                    break
    return items

def parse_yomiuri():
    logging.info("Parsing Yomiuri...")
    items = []
    url = "https://www.yomiuri.co.jp/editorial/"
    soup = fetch_html(url)
    if not soup:
        return items

    for a in soup.find_all("a", href=True):
        href = a["href"]
        title = a.get_text(strip=True)
        if "/editorial/" in href and len(title) > 8 and "読売新聞" not in title and href != "/editorial/":
            full_url = href if href.startswith("http") else "https://www.yomiuri.co.jp" + href
            if not any(item["link"] == full_url for item in items):
                cleaned_title = re.sub(r"^社説：\s*", "", title)
                body_text, img_url = fetch_article_detail(full_url)
                items.append({
                    "title": f"[読売] {cleaned_title}",
                    "link": full_url,
                    "description": body_text or cleaned_title,
                    "image": img_url,
                    "pub_date": datetime.now(timezone.utc)
                })
                if len(items) >= 2:
                    break
    return items

def parse_mainichi():
    logging.info("Parsing Mainichi...")
    items = []
    url = "https://mainichi.jp/editorial/"
    soup = fetch_html(url)
    if not soup:
        return items

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "{}")
            has_part = data.get("hasPart", [])
            for article in has_part:
                if article.get("@type") == "NewsArticle":
                    full_url = article.get("url")
                    title = article.get("headline", "").replace(" - 毎日新聞", "")
                    cleaned_title = re.sub(r"^社説：?\s*", "", title)
                    if full_url and cleaned_title and not any(item["link"] == full_url for item in items):
                        body_text = article.get("description", "")
                        img_url = None
                        img_data = article.get("image")
                        if isinstance(img_data, dict):
                            img_url = img_data.get("url")
                        elif isinstance(img_data, str):
                            img_url = img_data

                        items.append({
                            "title": f"[毎日] {cleaned_title}",
                            "link": full_url,
                            "description": body_text or cleaned_title,
                            "image": img_url,
                            "pub_date": datetime.now(timezone.utc)
                        })
                        if len(items) >= 2:
                            break
        except Exception as e:
            logging.warning(f"Error parsing Mainichi JSON-LD: {e}")

    if not items:
        for a in soup.find_all("a", href=True):
            href = a["href"]
            title = a.get_text(strip=True)
            if "/articles/" in href and ("ddm/005/070" in href or "社説" in title) and len(title) > 8:
                full_url = href if href.startswith("http") else "https://mainichi.jp" + href
                if not any(item["link"] == full_url for item in items):
                    cleaned_title = re.sub(r"^社説：?\s*", "", title)
                    body_text, img_url = fetch_article_detail(full_url)
                    items.append({
                        "title": f"[毎日] {cleaned_title}",
                        "link": full_url,
                        "description": body_text or cleaned_title,
                        "image": img_url,
                        "pub_date": datetime.now(timezone.utc)
                    })
                    if len(items) >= 2:
                        break
    return items

def parse_nikkei():
    logging.info("Parsing Nikkei...")
    items = []
    url = "https://www.nikkei.com/news/editorial/"
    soup = fetch_html(url)
    if not soup:
        return items

    for a in soup.find_all("a", href=True):
        href = a["href"]
        title = a.get_text(strip=True)
        if "/article/DG" in href and len(title) > 8:
            full_url = href if href.startswith("http") else "https://www.nikkei.com" + href
            if not any(item["link"] == full_url for item in items):
                cleaned_title = re.sub(r"^【社説】\s*", "", title)
                body_text, img_url = fetch_article_detail(full_url)
                items.append({
                    "title": f"[日経] {cleaned_title}",
                    "link": full_url,
                    "description": body_text or cleaned_title,
                    "image": img_url,
                    "pub_date": datetime.now(timezone.utc)
                })
                if len(items) >= 2:
                    break
    return items

def main():
    logging.info("Starting Editorial RSS Generator...")
    
    new_items = []
    new_items.extend(parse_asahi())
    new_items.extend(parse_yomiuri())
    new_items.extend(parse_mainichi())
    new_items.extend(parse_nikkei())
    
    logging.info(f"Fetched {len(new_items)} new articles across 4 newspapers.")

    existing_items = []
    if os.path.exists(FEED_FILE):
        try:
            parsed = parse_feed(FEED_FILE)
            for entry in parsed.entries:
                dt = None
                if entry.get("published"):
                    try:
                        dt = parse_date(entry.published)
                    except Exception:
                        dt = datetime.now(timezone.utc)
                else:
                    dt = datetime.now(timezone.utc)

                existing_items.append({
                    "title": entry.title,
                    "link": entry.link,
                    "description": entry.get("summary", ""),
                    "pub_date": dt
                })
        except Exception as e:
            logging.warning(f"Failed to parse existing RSS file: {e}")

    combined_items = []
    seen_links = set()

    for item in new_items:
        if item["link"] not in seen_links:
            seen_links.add(item["link"])
            combined_items.append(item)

    for item in existing_items:
        if item["link"] not in seen_links:
            seen_links.add(item["link"])
            combined_items.append(item)

    combined_items = combined_items[:MAX_ITEMS]

    fg = FeedGenerator()
    fg.title("全国4紙 社説統合RSS")
    fg.link(href="https://github.com/towoyuki/shasetsu-rss", rel="alternate")
    fg.description("朝日新聞・読売新聞・毎日新聞・日本経済新聞の社説見出しフィード")
    fg.language("ja")

    for item in combined_items:
        fe = fg.add_entry()
        fe.title(item["title"])
        fe.link(href=item["link"])
        fe.id(item["link"])

        
        pub_dt = item.get("pub_date")
        if isinstance(pub_dt, datetime):
            if pub_dt.tzinfo is None:
                pub_dt = pub_dt.replace(tzinfo=timezone.utc)
            fe.pubDate(pub_dt)
        else:
            fe.pubDate(datetime.now(timezone.utc))

        desc = item["description"]
        if item.get("image") and item["image"] not in desc:
            desc = f'<img src="{item["image"]}" style="max-width:100%;"><br><br>' + desc
        fe.description(desc)

    for feed_file in (FEED_FILE, TEST_FEED_FILE):
        fg.rss_file(feed_file, pretty=True)
        logging.info(f"Successfully updated {feed_file} with {len(combined_items)} total entries.")

if __name__ == "__main__":
    main()
