#!/usr/bin/env python3
"""
Energy Pulse — feed fetcher.

Reads config/feeds.yaml, pulls each source (RSS/Atom via feedparser, or a
lightweight HTML link-scrape fallback), normalizes items, merges with the
existing docs/data/articles.json (so history isn't lost between runs), drops
anything older than retention_days, and writes the result back out.

Run manually:  python scripts/fetch_feeds.py
Run in CI:     see .github/workflows/update.yml
"""
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import requests
import yaml
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "feeds.yaml"
OUTPUT_PATH = ROOT / "docs" / "data" / "articles.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; EnergyPulseBot/1.0; +https://github.com/)"}
REQUEST_TIMEOUT = 20


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def make_id(link, title):
    return hashlib.sha256(f"{link}|{title}".encode("utf-8")).hexdigest()[:16]


def safe_date(entry):
    for key in ("published", "updated", "pubDate"):
        val = entry.get(key)
        if val:
            try:
                dt = dateparser.parse(val)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except Exception:
                continue
    return datetime.now(timezone.utc)


def fetch_rss(source):
    items = []
    try:
        parsed = feedparser.parse(source["url"], request_headers=HEADERS)
        for entry in parsed.entries[:30]:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            if not title or not link:
                continue
            summary = BeautifulSoup(entry.get("summary", ""), "html.parser").get_text().strip()
            items.append({
                "id": make_id(link, title),
                "title": title,
                "link": link,
                "summary": summary[:400],
                "source": source["name"],
                "category": source["category"],
                "published": safe_date(entry).isoformat(),
            })
    except Exception as e:
        print(f"  [!] RSS parse failed for {source['name']}: {e}", file=sys.stderr)
    return items


def fetch_html_fallback(source):
    """Best-effort: grab anchor tags that look like headlines from a news/press page.
    This is intentionally conservative — it's meant to surface links, not full articles.
    Expect to hand-tune per site if a source's markup changes."""
    items = []
    try:
        resp = requests.get(source["url"], headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        seen = set()
        for a in soup.find_all("a", href=True):
            text = a.get_text().strip()
            href = a["href"]
            if len(text) < 25 or len(text) > 200:
                continue
            if href.startswith("/"):
                base = "/".join(source["url"].split("/")[:3])
                href = base + href
            if not href.startswith("http"):
                continue
            key = (text, href)
            if key in seen:
                continue
            seen.add(key)
            items.append({
                "id": make_id(href, text),
                "title": text,
                "link": href,
                "summary": "",
                "source": source["name"],
                "category": source["category"],
                "published": datetime.now(timezone.utc).isoformat(),
            })
            if len(items) >= 15:
                break
    except Exception as e:
        print(f"  [!] HTML fallback failed for {source['name']}: {e}", file=sys.stderr)
    return items


def main():
    config = load_config()
    retention_days = config.get("retention_days", 21)
    all_items = {}

    # Load existing data so history persists across runs
    if OUTPUT_PATH.exists():
        try:
            existing = json.loads(OUTPUT_PATH.read_text())
            for item in existing.get("articles", []):
                all_items[item["id"]] = item
        except Exception:
            pass

    for source in config["sources"]:
        print(f"Fetching: {source['name']}")
        new_items = fetch_html_fallback(source) if source.get("html") else fetch_rss(source)
        print(f"  -> {len(new_items)} items")
        for item in new_items:
            all_items[item["id"]] = item

    # Drop stale items
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    fresh = []
    for item in all_items.values():
        try:
            pub = dateparser.parse(item["published"])
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=timezone.utc)
        except Exception:
            pub = datetime.now(timezone.utc)
        if pub >= cutoff:
            fresh.append(item)

    fresh.sort(key=lambda x: x["published"], reverse=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(fresh),
        "articles": fresh,
    }, indent=2))

    print(f"\nWrote {len(fresh)} articles to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
