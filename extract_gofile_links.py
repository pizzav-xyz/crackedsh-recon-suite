import re
from camoufox.sync_api import Camoufox
import os
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


def extract_gofile_urls_from_paste(paste_url: str) -> list[str]:
    """
    Navigates to a pasted.pw URL using Camoufox, extracts the content from the
    CodeMirror editor, and finds all GoFile.io URLs within it.

    Args:
        paste_url (str): The URL of the pasted.pw page.

    Returns:
        list[str]: A list of GoFile.io URLs found in the paste content.
    """
    gofile_urls = []
    try:
        print(f"  [Camoufox] Navigating to {paste_url}...")
        with Camoufox(headless=False) as browser:
            page = browser.new_page()
            page.goto(
                paste_url, wait_until="domcontentloaded", timeout=30000
            )  # Increased timeout

            # Wait for the CodeMirror editor to be initialized and content loaded
            # The actual content is usually within a div with class 'CodeMirror-code' or the original textarea
            paste_content = None
            try:
                # Attempt to get content from the visible CodeMirror element
                # The text is broken into lines within 'div.CodeMirror-line' elements
                code_mirror_lines = page.locator(
                    ".CodeMirror-code .CodeMirror-line"
                ).all_text_contents()
                if code_mirror_lines:
                    paste_content = "\n".join(code_mirror_lines)
                else:
                    # Fallback to the original textarea if CodeMirror structure is not found or is empty
                    paste_content = page.locator("textarea#code-editor").input_value(
                        timeout=5000
                    )
            except PlaywrightTimeoutError:
                print(
                    f"    [Camoufox] CodeMirror or textarea#code-editor not found/loaded on {paste_url} within timeout."
                )
            except Exception as e:
                print(
                    f"    [Camoufox] Error extracting paste content from {paste_url}: {e}"
                )

            if paste_content:
                gofile_pattern = re.compile(
                    r"https?://(?:www\.)?gofile\.io/(?:d|id)/[a-zA-Z0-9]+"
                )
                found_urls_in_text = gofile_pattern.findall(paste_content)
                gofile_urls.extend(found_urls_in_text)

            try:
                gofile_locators = page.locator('a[href*="gofile.io"]')
                for i in range(gofile_locators.count()):
                    href = gofile_locators.nth(i).get_attribute("href")
                    if href and re.match(
                        r"https?://(?:www\.)?gofile\.io/(?:d|id)/[a-zA-Z0-9]+", href
                    ):
                        gofile_urls.append(href)
            except Exception as e:
                print(f"    [Camoufox] Error searching for GoFile links in HTML: {e}")

            gofile_urls = list(dict.fromkeys(gofile_urls))

            if gofile_urls:
                print(f"    [Camoufox] Found {len(gofile_urls)} GoFile URLs.")
            else:
                print(f"    [Camoufox] No GoFile URLs found in paste.")

    except PlaywrightTimeoutError:
        print(f"  [Camoufox] Navigation to {paste_url} timed out.")
    except Exception as e:
        print(f"  [Camoufox] An error occurred during processing {paste_url}: {e}")
    return gofile_urls


def process_links_file(file_path: str):
    """
    Reads a file containing URLs, processes pasted.pw links to extract GoFile URLs,
    and updates the file with the new GoFile URLs.

    Args:
        file_path (str): The path to the file containing URLs.
    """
    updated_lines = []
    original_lines = []

    print(f"Processing {file_path}...")

    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        original_lines = [line.strip() for line in f if line.strip()]

    for line in original_lines:
        if "pasted.pw" in line:
            print(f"[*] Processing pasted.pw link: {line}")
            gofile_links = extract_gofile_urls_from_paste(line)
            if gofile_links:
                for gofile_link in gofile_links:
                    updated_lines.append(gofile_link)
            else:
                updated_lines.append(line)  # Keep original if no gofile links found
        else:
            updated_lines.append(line)

    print(f"Writing updated links back to {file_path}...")
    with open(file_path, "w", encoding="utf-8") as f:
        for u_line in updated_lines:
            f.write(u_line + "\n")
    print("Processing complete.")


if __name__ == "__main__":
    links_file = "crackedsh_extracted_links.txt"
    process_links_file(links_file)
