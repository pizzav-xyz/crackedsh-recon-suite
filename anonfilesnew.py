#!/usr/bin/env python3
# import time  # Commented out since no longer used
from datetime import datetime
from pathlib import Path

from camoufox.sync_api import Camoufox
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

PROFILE_DIR = "/tmp/camoufox_profile"
URLS_FILE = "/tmp/urls.txt"


def click_and_extract_download_link(page, url, timeout=20000):
    print(f"\n➡️ Processing: {url}")

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout)  # Changed from networkidle to domcontentloaded for faster loading
        print(f"✅ Page loaded successfully: {url}")
    except Exception as e:
        print(f"🚨 Navigation error: {e}")
        return {"original_url": url, "download_url": None, "success": False}

    # Combine all selectors into a single CSS selector for efficiency
    combined_selector = 'button:has-text("Download"), a:has-text("Download"), button:has-text("DOWNLOAD"), a:has-text("DOWNLOAD"), a[href*="download"]'
    
    btn = page.query_selector(combined_selector)

    if not btn:
        print("❌ No download button found")
        return {"original_url": url, "download_url": None, "success": False}

    print("🖱️ Clicking download button...")

    # Try to click the button and capture download with retries
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            with page.expect_download(timeout=5000) as dl_info:
                btn.click(timeout=5000)
            # Wait briefly for the download to initiate
            page.wait_for_timeout(500)
            download = dl_info.value
            print(f"⬇️ Download captured (attempt {attempt + 1}): {download.url}")
            return {
                "original_url": url,
                "download_url": download.url,
                "success": True,
            }
        except PlaywrightTimeoutError:
            print(f"⚠️ Attempt {attempt + 1} failed - no download detected")
            if attempt < max_retries - 1:  # If not the last attempt
                print(f"🔄 Retrying... ({attempt + 2}/{max_retries})")
                page.wait_for_timeout(1000)  # Wait before retry
            else:
                print("❌ All retry attempts failed")
                return {"original_url": url, "download_url": None, "success": False}
        except Exception as e:
            print(f"❌ Unexpected error during attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:  # If not the last attempt
                print(f"🔄 Retrying... ({attempt + 2}/{max_retries})")
                page.wait_for_timeout(1000)  # Wait before retry
            else:
                print("❌ All retry attempts failed with unexpected error")
                return {"original_url": url, "download_url": None, "success": False}


def process_all_urls():
    with open(URLS_FILE) as f:
        urls = [u.strip() for u in f if u.strip()]

    print(f"📝 URLs to process: {len(urls)}")

    Path(PROFILE_DIR).mkdir(parents=True, exist_ok=True)

    results = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"download_results_{timestamp}.txt"

    with Camoufox(
        headless=False,
        humanize=True,
        persistent_context=True,
        user_data_dir=PROFILE_DIR,
    ) as browser:
        # Reuse existing open pages if any (avoid opening a second blank)
        pages = browser.pages
        if pages:
            page = pages[0]
        else:
            page = browser.new_page()

        for i, url in enumerate(urls, start=1):
            print(f"\n[{i}/{len(urls)}]")
            result = click_and_extract_download_link(page, url)
            results.append(result)
            # Remove fixed sleep - rely on page actions for timing
            pass  # No delay between URLs - each page.goto() will handle its own timing

        page.close()

    with open(output_file, "w", encoding="utf-8") as out:
        out.write(f"Download Extraction Report - {datetime.now()}\n\n")
        for r in results:
            out.write(f"{r}\n")

    print(f"\n📁 Results saved: {output_file}")


if __name__ == "__main__":
    process_all_urls()
