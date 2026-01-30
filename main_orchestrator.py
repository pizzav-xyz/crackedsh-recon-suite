"""Main orchestrator for cracked.sh forum scraping workflow.

This module orchestrates the scraping of combolists from cracked.sh MyBB forum.
It uses a Scrapy spider to identify top combolist threads and then employs
Camoufox to reveal hidden content and extract links from these threads.
"""

import json
import os
import sys
from pathlib import Path

# Add relevant project directories to the Python path for module imports
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT / "crackedsh_scraper_mybb" / "scrapy_mybb_scraper"))
sys.path.insert(0, str(PROJECT_ROOT / "crackedsh_scraper_mybb"))
sys.path.insert(0, str(PROJECT_ROOT / "scrapers"))
# Add project root last, but still with highest priority due to insert(0)
sys.path.insert(0, str(PROJECT_ROOT))

# Third-party imports
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

# Local imports
from scrapers.forum_scraper import reveal_hidden_content_and_extract_links
from scrapy_mybb_scraper.spiders.mybb_spider import MybbSpider


def run_mybb_scraper(output_json_path):
    """Run the MybbSpider to get top combolist threads and save them to a JSON file.

    Args:
        output_json_path (str): Path where the JSON output should be saved.
    """
    print("Running MyBB Scraper...")

    # Define the Scrapy project path and settings module
    scrapy_project_path = (
        Path(__file__).parent / "crackedsh_scraper_mybb" / "scrapy_mybb_scraper"
    )
    scrapy_settings_module = "scrapy_mybb_scraper.settings"

    # Store original working directory and Scrapy settings module
    original_cwd = os.getcwd()
    original_scrapy_settings = os.environ.get("SCRAPY_SETTINGS_MODULE")

    try:
        # Change working directory to the Scrapy project root
        os.chdir(scrapy_project_path)
        # Set the Scrapy settings module environment variable
        os.environ["SCRAPY_SETTINGS_MODULE"] = scrapy_settings_module

        # Load project settings
        settings = get_project_settings()
        # Use FEEDS instead of deprecated FEED_FORMAT/FEED_URI to avoid conflicts
        settings.set(
            "FEEDS", {str(output_json_path): {"format": "json", "overwrite": True}}
        )
        # Reduce log verbosity
        settings.set("LOG_LEVEL", "INFO")

        process = CrawlerProcess(settings)
        process.crawl(MybbSpider)
        process.start()
        print(f"MyBB Scraper finished. Results saved to {output_json_path}")
    finally:
        # Restore original working directory and Scrapy settings module
        os.chdir(original_cwd)
        if original_scrapy_settings is not None:
            os.environ["SCRAPY_SETTINGS_MODULE"] = original_scrapy_settings
        elif "SCRAPY_SETTINGS_MODULE" in os.environ:
            del os.environ["SCRAPY_SETTINGS_MODULE"]


def main():
    """Main orchestration function that coordinates the scraping workflow."""
    # Define paths
    output_top_posts_json = PROJECT_ROOT / "top_combolists_today.json"
    output_extracted_links_txt = PROJECT_ROOT / "crackedsh_extracted_links.txt"

    # Step 1: Run the MyBB Scraper to get top posts
    run_mybb_scraper(str(output_top_posts_json))

    # Step 2: Read the JSON data from the top posts (contains URLs and numbers)
    thread_data = []
    if output_top_posts_json.exists():
        with open(output_top_posts_json, "r", encoding="utf-8") as f:
            thread_data = json.load(f)
    else:
        print(
            f"Error: {output_top_posts_json} not found. Cannot proceed with hidden revealer."
        )
        return

    if not thread_data:
        print("No thread data found from top posts. Exiting.")
        return

    print(
        f"Found {len(thread_data)} threads from top posts. "
        "Proceeding to reveal hidden content (sorted by number descending)."
    )

    # Step 3: Use the hidden revealer to extract links
    # Note: Camoufox requires a display environment. Ensure this script is run
    # where it can launch a browser.
    extracted_all_links = reveal_hidden_content_and_extract_links(thread_data)

    # Step 4: Write all extracted links to a single file for CyberDropDownloader
    if extracted_all_links:
        with open(output_extracted_links_txt, "w", encoding="utf-8") as f:
            for link in extracted_all_links:
                f.write(f"{link}\n")
        print(f"All extracted links saved to {output_extracted_links_txt}")
    else:
        print("No hidden content links were extracted.")

    print("Orchestration complete.")


if __name__ == "__main__":
    main()
