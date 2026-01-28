import json
import os
import sys
from pathlib import Path

# Add relevant project directories to the Python path for module imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "crackedsh_scraper_mybb" / "scrapy_mybb_scraper"))
sys.path.insert(0, str(project_root / "crackedsh_scraper_mybb"))
sys.path.insert(0, str(project_root / "scrapers"))
sys.path.insert(
    0, str(project_root)
)  # Add project root last, but still with highest priority due to insert(0)

# Import the reveal function
from forum_scraper import reveal_hidden_content_and_extract_links

# Import Scrapy components
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from scrapy_mybb_scraper.spiders.mybb_spider import MybbSpider


def run_mybb_scraper(output_json_path):  # Removed default value as it's always passed
    """
    Runs the MybbSpider to get top combolist threads and saves them to a JSON file.
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
        settings.set("FEED_FORMAT", "json")
        # output_json_path is already an absolute path string from the calling main function
        settings.set("FEED_URI", output_json_path)
        settings.set("LOG_LEVEL", "INFO")  # Reduce log verbosity

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
    # Define paths
    output_top_posts_json = Path(__file__).parent / "top_combolists_today.json"
    output_extracted_links_txt = Path(__file__).parent / "crackedsh_extracted_links.txt"

    # Step 1: Run the MyBB Scraper to get top posts
    run_mybb_scraper(str(output_top_posts_json))

    # Step 2: Read the URLs from the top posts
    thread_urls = []
    if output_top_posts_json.exists():
        with open(output_top_posts_json, "r") as f:
            top_posts = json.load(f)
            for post in top_posts:
                if "url" in post:
                    thread_urls.append(post["url"])
    else:
        print(
            f"Error: {output_top_posts_json} not found. Cannot proceed with hidden revealer."
        )
        return

    if not thread_urls:
        print("No thread URLs found from top posts. Exiting.")
        return

    print(
        f"Found {len(thread_urls)} thread URLs from top posts. Proceeding to reveal hidden content."
    )

    # Step 3: Use the hidden revealer to extract links
    # Note: Camoufox requires a display environment. Ensure this script is run where it can launch a browser.
    extracted_all_links = reveal_hidden_content_and_extract_links(thread_urls)

    # Step 4: Write all extracted links to a single file for CyberDropDownloader
    if extracted_all_links:
        with open(output_extracted_links_txt, "w") as f:
            for link in extracted_all_links:
                f.write(f"{link}\n")
        print(f"All extracted links saved to {output_extracted_links_txt}")
    else:
        print("No hidden content links were extracted.")

    print("Orchestration complete.")


if __name__ == "__main__":
    main()
