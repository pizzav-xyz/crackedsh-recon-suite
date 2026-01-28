#!/usr/bin/env python3

import sys
import os
import time
import json
import re  # Added import for regex
from datetime import datetime

# sys.path.insert(0, "/home/pizzav/Documents/crackedshscraper/camoufox_repo/pythonlib")

from camoufox import Camoufox
from pathlib import Path


def reveal_hidden_content_and_extract_links(urls: list) -> list:
    extracted_links = []

    RATE_LIMIT_FILE = str(Path(__file__).parent.parent / "post_state.json")
    MAX_POSTS_PER_DAY = 25
    post_state = {"last_post_date": None, "post_count": 0}

    if Path(RATE_LIMIT_FILE).exists():
        with open(RATE_LIMIT_FILE, "r") as f:
            try:
                post_state = json.load(f)
            except json.JSONDecodeError:
                print(
                    f"Warning: Could not decode {RATE_LIMIT_FILE}. Starting with fresh state."
                )
                post_state = {"last_post_date": None, "post_count": 0}

    today_str = datetime.now().strftime("%Y-%m-%d")

    if post_state["last_post_date"] != today_str:
        print("New day detected. Resetting post count.")
        post_state["last_post_date"] = today_str
        post_state["post_count"] = 0

    profile_path = str(Path(__file__).parent.parent / "profile")

    with Camoufox(persistent_context=True, user_data_dir=profile_path) as browser:
        page = browser.new_page()

        for url in urls:
            print(f"Processing: {url}")

            if post_state["post_count"] >= MAX_POSTS_PER_DAY:
                print(
                    f"Daily post limit ({MAX_POSTS_PER_DAY}) reached. Skipping further posts for today."
                )
                break

            try:
                page.goto(url)
                iframe = page.locator("iframe")
                iframe.content_frame.locator("html").click()
                iframe.content_frame.locator("body").fill("thx")
                page.get_by_role("button", name="Post Reply").click()

                post_state["post_count"] += 1
                print(
                    f"Post count for today: {post_state['post_count']}/{MAX_POSTS_PER_DAY}"
                )

                with open(RATE_LIMIT_FILE, "w") as f:
                    json.dump(post_state, f)

                time.sleep(5)

                title = page.locator("div.hidden-content-title").inner_text()

                hidden_content = page.locator("div.hidden-content-body")
                found_links_on_page = []

                # Extract all possible URLs directly from the text content of hidden_content_body
                text_content = hidden_content.inner_text()
                # Generic URL pattern to catch all http(s):// links
                generic_url_pattern = r"https?://[^\s<]+"
                direct_links_from_text = re.findall(generic_url_pattern, text_content)
                found_links_on_page.extend(direct_links_from_text)

                # Then, check for links within all <a> tags (not just .mycode_url)
                # We assume any <a> tag in hidden content is relevant
                all_link_elements = hidden_content.locator(
                    "a"
                )  # Change from a.mycode_url
                for i in range(all_link_elements.count()):
                    link_element = all_link_elements.nth(i)
                    link_href = link_element.get_attribute("href")
                    if link_href:  # Ensure href attribute exists
                        found_links_on_page.append(link_href)

                # Add unique links found on this page to the main extracted_links list
                extracted_links.extend(list(set(found_links_on_page)))
            except Exception as e:
                print(f"Error during posting or content extraction for {url}: {e}")
                title = "Error"
                link_url = "Error"
                link_text = "Error"
                with open(RATE_LIMIT_FILE, "w") as f:
                    json.dump(post_state, f)

    return extracted_links
