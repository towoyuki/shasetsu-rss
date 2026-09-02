import sys
import re
import json
import logging
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

def fetch_html(url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=8)
        res.raise_for_status()
        res.encoding = res.apparent_encoding or "utf-8"
        return BeautifulSoup(res.text, "html.parser")
    except Exception as e:
        print(f"[ERROR] Fetching {url}: {e}")
        return None

def test_asahi():
    print("\n=================== 朝日新聞 テスト (本日: 9/2) ===================")
    url = "https://www.asahi.com/rensai/list.html?id=16"
    soup = fetch_html(url)
    if not soup:
        return
    count = 0
    for a in soup.find_all("a", href=True):
        href = a["href"]
        title = a.get_text(strip=True)
        if "/articles/" in href and len(title) > 8:
            full_url = href if href.startswith("http") else "https://www.asahi.com" + href
            cleaned_title = re.sub(r"^（社説）\s*", "", title).split("･･･[続きを読む]")[0].strip()
            print(f"[{count+1}] タイトル: {cleaned_title}")
            print(f"    URL: {full_url}")
            count += 1
            if count >= 3:
                break

def test_yomiuri():
    print("\n=================== 読売新聞 テスト (本日: 9/2) ===================")
    url = "https://www.yomiuri.co.jp/editorial/"
    soup = fetch_html(url)
    if not soup:
        return
    count = 0
    for a in soup.find_all("a", href=True):
        href = a["href"]
        title = a.get_text(strip=True)
        if "/editorial/" in href and len(title) > 8 and "読売新聞" not in title and href != "/editorial/":
            full_url = href if href.startswith("http") else "https://www.yomiuri.co.jp" + href
            cleaned_title = re.sub(r"^社説：\s*", "", title)
            print(f"[{count+1}] タイトル: {cleaned_title}")
            print(f"    URL: {full_url}")
            count += 1
            if count >= 3:
                break

def test_mainichi():
    print("\n=================== 毎日新聞 テスト (本日: 9/2) ===================")
    url = "https://mainichi.jp/editorial/"
    soup = fetch_html(url)
    if not soup:
        return
    count = 0
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "{}")
            has_part = data.get("hasPart", [])
            for article in has_part:
                if article.get("@type") == "NewsArticle":
                    full_url = article.get("url")
                    title = article.get("headline", "").replace(" - 毎日新聞", "")
                    pub_date = article.get("datePublished", "不明")
                    cleaned_title = re.sub(r"^社説：?\s*", "", title)
                    print(f"[{count+1}] タイトル: {cleaned_title}")
                    print(f"    URL: {full_url}")
                    print(f"    発行日時: {pub_date}")
                    count += 1
                    if count >= 3:
                        break
        except Exception as e:
            pass

def test_nikkei():
    print("\n=================== 日本経済新聞 テスト (本日: 9/2) ===================")
    url = "https://www.nikkei.com/news/editorial/"
    soup = fetch_html(url)
    if not soup:
        return
    count = 0
    for a in soup.find_all("a", href=True):
        href = a["href"]
        title = a.get_text(strip=True)
        if "/article/DG" in href and len(title) > 8:
            full_url = href if href.startswith("http") else "https://www.nikkei.com" + href
            cleaned_title = re.sub(r"^【社説】\s*", "", title)
            print(f"[{count+1}] タイトル: {cleaned_title}")
            print(f"    URL: {full_url}")
            count += 1
            if count >= 3:
                break

if __name__ == "__main__":
    print(f"テスト実行日時: {datetime.now(timezone.utc)}")
    test_asahi()
    test_yomiuri()
    test_mainichi()
    test_nikkei()
