"""Curl-cffi based scraper for MyBB forum listing pages.

Replaces the Scrapy-based scraper with an async curl-cffi approach.
Fetches forum listing pages in parallel, parses thread rows,
outputs all entries where number < 100,000 (or no number) to filtered_under_100k.json.
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

from curl_cffi.requests import AsyncSession
from parsel import Selector

from scrapy_mybb_scraper import config

DOMAIN = config.DOMAIN
FORUM_ID = config.FORUM_ID
PREFIX_ID = config.PREFIX_ID
SORT_BY = config.SORT_BY
ORDER = config.ORDER


def normalize_size_string(size_str):
    """Normalize size string to integer.

    Handles patterns like "502.7k", "14.6k", "11.2M", "910K", etc.
    These are numbers followed immediately by multipliers (no space allowed).
    Copied from MyBBScraperUtils in mybb_spider.py.
    """
    if not size_str:
        return 0

    multiplier_pattern = r"(\d+(?:\.\d+)?)\s*([kmgtbpKMGTBP])(?!\w)"
    matches = re.findall(multiplier_pattern, str(size_str))

    if matches:
        best_match = max(matches, key=lambda x: float(x[0]))
        num_part = float(best_match[0])
        mult_part = best_match[1].lower()

        multipliers = {
            "k": 1000,
            "m": 1000000,
            "g": 1000000000,
            "t": 1000000000000,
            "b": 1000000000000,
            "p": 1000000000000000,
        }

        return int(num_part * multipliers.get(mult_part, 1))

    european_pattern = r"\b(\d{1,3}(?:\.\d{3})+)\b"
    european_matches = re.findall(european_pattern, str(size_str))
    if european_matches:
        valid_numbers = []
        for num_str in european_matches:
            try:
                num_val = float(num_str.replace(".", ""))
                valid_numbers.append(num_val)
            except ValueError:
                continue
        if valid_numbers:
            return int(max(valid_numbers))

    numbers = re.findall(r"\b\d+(?:\.\d+)?\b", str(size_str))
    if not numbers:
        try:
            return int(float(size_str))
        except ValueError:
            return 0

    valid_numbers = []
    for num_str in numbers:
        if num_str.count(".") <= 1:
            try:
                num_val = float(num_str)
                valid_numbers.append(num_val)
            except ValueError:
                continue

    if not valid_numbers:
        return 0

    return int(max(valid_numbers))


PROCESSED_URLS_FILE = Path(__file__).parent / "processed_urls.json"


def load_processed_urls() -> set:
    if PROCESSED_URLS_FILE.exists():
        try:
            return set(json.loads(PROCESSED_URLS_FILE.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            return set()
    return set()


def save_processed_urls(urls: set) -> None:
    try:
        PROCESSED_URLS_FILE.write_text(
            json.dumps(sorted(urls), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as e:
        print(f"  [warn] could not save processed URLs: {e}")


def is_from_today(date_str: str) -> bool:
    if not date_str:
        return False
    date_str = date_str.lower().strip()
    if "today" in date_str:
        return True
    if "ago" in date_str:
        time_match = re.search(r"(\d+)\s*(second|minute|hour|day)s?\s+ago", date_str)
        if time_match:
            num = int(time_match.group(1))
            unit = time_match.group(2)
            if unit in ("second", "minute", "hour"):
                return True
            if unit == "day":
                return num <= 1
        if any(p in date_str for p in ("an hour ago", "a minute ago", "a second ago",
                                        "a few seconds ago", "less than a minute ago",
                                        "under a minute ago")):
            return True
        if any(p in date_str for p in ("a day ago", "an day ago", "a week ago",
                                        "an week ago", "a month ago", "a year ago")):
            return False
    return False


def is_older_than_1_day(date_str: str) -> bool:
    if not date_str:
        return True
    date_str = date_str.lower().strip()
    if "ago" not in date_str:
        return True
    time_match = re.search(r"(\d+)\s*(second|minute|hour|day)s?\s+ago", date_str)
    if not time_match:
        if any(p in date_str for p in ("a day ago", "an day ago", "a week ago",
                                        "an week ago", "a month ago", "a year ago",
                                        "yesterday")):
            return True
        return False
    num = int(time_match.group(1))
    unit = time_match.group(2)
    if unit in ("second", "minute", "hour"):
        return False
    if unit == "day":
        return num > 1
    return True


def build_url(page: int) -> str:
    return (
        f"https://{DOMAIN}/Forum-Combolists--{FORUM_ID}"
        f"?sortby={SORT_BY}&order={ORDER}&prefix={PREFIX_ID}&page={page}"
    )


async def fetch_page(session, page: int) -> list:
    try:
        r = await session.get(build_url(page), impersonate="chrome120", timeout=30)
        if r.status_code != 200:
            print(f"  [page {page}] non-200 status: {r.status_code}")
            return []
    except Exception as e:
        print(f"  [page {page}] fetch error: {e}")
        return []

    sel = Selector(text=r.text)
    return parse_page(sel)


def parse_page(sel: Selector) -> list:
    results = []
    for row in sel.css("tr.inline_row"):
        date_text = ""
        for span_text in row.css("div.author.smalltext span.thread-date::text").getall():
            span_text = span_text.strip()
            if span_text and ("ago" in span_text.lower() or "today" in span_text.lower() or "yesterday" in span_text.lower()):
                date_text = span_text
                break
        if not date_text:
            for span_text in row.css("span.thread-date::text").getall():
                span_text = span_text.strip()
                if span_text and ("ago" in span_text.lower() or "today" in span_text.lower() or "yesterday" in span_text.lower()):
                    date_text = span_text
                    break
        for link in row.css("span.subject_old a"):
            title = "".join(link.css("*::text").getall()).strip()
            if not title or (len(title) <= 2 and title.isdigit()):
                continue

            href = link.css("::attr(href)").get("") or ""
            full_url = urljoin(f"https://{DOMAIN}/", href)

            number = normalize_size_string(title)

            results.append({
                "title": title,
                "url": full_url,
                "number": number,
                "date_text": date_text,
            })
    return results


async def scrape() -> list:
    async with AsyncSession(impersonate="chrome120") as session:
        page = 1
        all_entries = []
        while True:
            entries = await fetch_page(session, page)
            for e in entries:
                if is_older_than_1_day(e["date_text"]):
                    print(f"  page {page}: thread older than 1 day ('{e['date_text']}') — stopping")
                    print(f"  Scraped {len(all_entries)} total entries from {page - 1} pages")
                    processed = load_processed_urls()
                    new_entries = []
                    for e2 in all_entries:
                        if e2["url"] not in processed:
                            if is_from_today(e2["date_text"]):
                                new_entries.append(e2)
                            processed.add(e2["url"])
                    save_processed_urls(processed)
                    filtered = [e2 for e2 in new_entries if e2["number"] is None or e2["number"] < 100_000]
                    return filtered
                all_entries.append(e)
            page += 1


def save(filtered: list, date_str: str, cwd: Path) -> Path:
    path = cwd / "filtered_under_100k.json"
    path.write_text(
        json.dumps(filtered, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


if __name__ == "__main__":
    filtered = asyncio.run(scrape())
    date_str = datetime.now().strftime("%Y-%m-%d")
    path = save(filtered, date_str, Path(__file__).parent)
    print(f"Written {len(filtered)} entries to {path}")