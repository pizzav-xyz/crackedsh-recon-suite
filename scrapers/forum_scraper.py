"""Forum scraper for revealing hidden content using Camoufox browser automation."""

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

# Third-party imports
from camoufox import Camoufox

# Constants for rate limiting and configuration
RATE_LIMIT_FILE = "post_state.json"
REPLIED_POSTS_FILE = "replied_posts.json"
MAX_POSTS_PER_DAY = 25
PROFILE_DIR = "profile"


def reveal_hidden_content_and_extract_links(
    threads_data, output_dir: str = "extracted_content"
):
    """Reveal hidden content and extract links from forum threads.

    Args:
        threads_data: Either a list of URLs or JSON data with thread information including 'url' and 'number' fields.
        output_dir (str): Directory to save extracted content. Defaults to "extracted_content".

    Returns:
        list[str]: List of extracted links.
    """
    extracted_links = []

    import json

    # If threads_data is a list of dictionaries (JSON data from Scrapy), sort by 'number' field
    if (
        isinstance(threads_data, list)
        and len(threads_data) > 0
        and isinstance(threads_data[0], dict)
    ):
        # Sort by the 'number' field in descending order (highest first)
        sorted_threads_data = sorted(
            threads_data, key=lambda x: x.get("number", 0), reverse=True
        )
        sorted_threads = [thread["url"] for thread in sorted_threads_data]
    elif isinstance(threads_data, list):
        # If it's already a list of URLs, use as is
        sorted_threads = threads_data
    else:
        # Default to empty list if format is unexpected
        sorted_threads = []

    # Rate limiting logic from reference
    post_state = {"last_post_date": None, "post_count": 0}

    if Path(RATE_LIMIT_FILE).exists():
        with open(RATE_LIMIT_FILE, "r", encoding="utf-8") as f:
            try:
                post_state = json.load(f)
            except json.JSONDecodeError:
                print(
                    f"Warning: Could not decode {RATE_LIMIT_FILE}. "
                    "Starting with fresh state."
                )
                post_state = {"last_post_date": None, "post_count": 0}

    # Load replied posts tracking
    replied_posts = {}
    if Path(REPLIED_POSTS_FILE).exists():
        with open(REPLIED_POSTS_FILE, "r", encoding="utf-8") as f:
            try:
                replied_posts = json.load(f)
            except json.JSONDecodeError:
                print(
                    f"Warning: Could not decode {REPLIED_POSTS_FILE}. "
                    "Starting with fresh tracking."
                )
                replied_posts = {}

    today_str = datetime.now().strftime("%Y-%m-%d")

    if post_state["last_post_date"] != today_str:
        print("New day detected. Resetting post count.")
        post_state["last_post_date"] = today_str
        post_state["post_count"] = 0

    # Ensure output directory exists
    Path(output_dir).mkdir(exist_ok=True)

    # Initialize Camoufox (which uses Playwright under hood)
    # Only use one tab at a time
    with Camoufox(
        persistent_context=True, user_data_dir=PROFILE_DIR, headless=False
    ) as browser:
        page = browser.new_page()

        for url in sorted_threads:
            if not url:
                continue

            print(f"Processing URL: {url}")

            # Skip if already replied to this post
            if url in replied_posts:
                print(f"Already replied to {url}. Skipping.")
                continue

            if post_state["post_count"] >= MAX_POSTS_PER_DAY:
                print(
                    f"Daily post limit ({MAX_POSTS_PER_DAY}) reached. Skipping further posts for today."
                )
                break

            try:
                page.goto(url, wait_until="domcontentloaded")

                # Scroll to the bottom of the page to ensure all content is loaded
                page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                # Wait a bit for any dynamic content to load after scrolling
                page.wait_for_timeout(2000)

                # Use the working approach from the proven implementation
                # Find the iframe and interact with its content frame
                iframe = page.locator("iframe")
                if iframe.count() > 0:
                    # Click on the iframe's content frame and fill the body with "thx"
                    iframe.content_frame.locator("html").click()
                    iframe.content_frame.locator("body").fill("thx")
                    # Click the "Post Reply" button
                    page.get_by_role("button", name="Post Reply").click()
                else:
                    print(f"Warning: No iframe found for {url}. Skipping post.")
                    continue  # Skip to next URL if no iframe found

                post_state["post_count"] += 1
                print(
                    f"Post count for today: {post_state['post_count']}/{MAX_POSTS_PER_DAY}"
                )

                # Mark this post as replied to
                replied_posts[url] = {
                    "replied_at": datetime.now().isoformat(),
                    "title": "Processing",
                }

                with open(RATE_LIMIT_FILE, "w") as f:
                    json.dump(post_state, f)

                with open(REPLIED_POSTS_FILE, "w") as f:
                    json.dump(replied_posts, f, indent=2)

                # Wait for the page to update after posting
                time.sleep(10)

                # Navigate back to the page to ensure the hidden content is loaded after the post
                page.goto(url, wait_until="domcontentloaded")

                # Wait a bit more for the hidden content to load after navigating back
                time.sleep(2)

                title = page.locator("div.hidden-content-title").inner_text()

                if url in replied_posts:
                    replied_posts[url]["title"] = title
                    with open(REPLIED_POSTS_FILE, "w") as f:
                        json.dump(replied_posts, f, indent=2)

                hidden_content = page.locator("div.hidden-content-body")
                link_elements = hidden_content.locator("a.mycode_url")
                if link_elements.count() > 0:
                    link_url = link_elements.first.get_attribute("href")
                    link_text = link_elements.first.inner_text()
                    # Append extracted link
                    extracted_links.append(link_url)
                else:
                    link_url = "No link found"
                    link_text = "No link found"
            except Exception as e:
                print(f"Error during posting or content extraction for {url}: {e}")
                title = "Error"
                link_url = "Error"
                link_text = "Error"
                with open(RATE_LIMIT_FILE, "w") as f:
                    json.dump(post_state, f)

            filename = f"{url.replace('https://', '').replace('/', '_')}.txt"
            with open(f"{output_dir}/{filename}", "w") as f:
                f.write(f"URL: {url}\n")
                f.write(f"Title: {title}\n")
                f.write(f"Link Text: {link_text}\n")
                f.write(f"Link URL: {link_url}\n")

            print(f"Saved: {output_dir}/{filename}")
            print(f"Found link: {link_text} -> {link_url}")

    return extracted_links
