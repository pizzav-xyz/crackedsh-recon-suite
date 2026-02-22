import re
from camoufox.sync_api import Camoufox
import os

# Combined regex for multiple file hosting sites
FILE_HOST_REGEX = re.compile(
    r"https?://(?:www\.)?(?:gofile\.io/(?:d|id)/[A-Za-z0-9_-]+|limewire\.com/d/[A-Za-z0-9_-]+|mega\.nz/file/[A-Za-z0-9_#!-]+|upload\.ee/files/[A-Za-z0-9_.-]+|anonfilesnew\.com/(?:s/[A-Za-z0-9_]+|[A-Za-z0-9_]+/[A-Za-z0-9_.-]+))"
)

def extract_filehost_urls(page, url: str) -> list[str]:
    """Extract file-hosting links from a page using a reused Camoufox page."""
    print(f"[Camoufox] Navigating to {url}…")
    page.goto(url, wait_until="domcontentloaded", timeout=20000)

    urls = []

    # Extract all visible text from body
    body_text = page.locator("body").inner_text()
    urls.extend(FILE_HOST_REGEX.findall(body_text))

    # Extract hrefs directly
    links = page.locator('a[href]')
    for i in range(links.count()):
        href = links.nth(i).get_attribute("href")
        if href and FILE_HOST_REGEX.match(href):
            urls.append(href)

    # Return unique links
    return list(dict.fromkeys(urls))


def process_links_file(file_path: str):
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    updated = []

    # Reuse a single browser and page
    with Camoufox(headless=True) as browser:
        page = browser.new_page()
        for line in lines:
            # Only scrape if it's a supported paste or text page
            if any(x in line for x in ["pasted.pw", "upload.ee", "text", "anonfilesnew.com"]):
                print(f"[Camoufox] Processing page: {line}")
                urls = extract_filehost_urls(page, line)
                updated.extend(urls if urls else [line])
            else:
                updated.append(line)

    # Save all extracted URLs
    with open(file_path, "w", encoding="utf-8") as f:
        for u in updated:
            f.write(u + "\n")

    print("Done!")


if __name__ == "__main__":
    process_links_file("anonfiles_urls.txt")
