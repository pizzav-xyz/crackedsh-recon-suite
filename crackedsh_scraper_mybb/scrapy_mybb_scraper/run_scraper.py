#!/usr/bin/env python3
"""Scrapy-based MyBB Forum Scraper for cracked.sh.

Reimplementation of the original unified scraper using Scrapy framework.
"""

import os
import sys

# Third-party imports
from scrapy.crawler import CrawlerProcess

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_scraper():
    """Run the MyBB scraper using Scrapy."""
    print("Starting MyBB Forum Scraper for cracked.sh using Scrapy...")
    print("Finding top 10 combolists from today with highest numbers in titles...")

    # Create a CrawlerProcess with custom settings
    process = CrawlerProcess(
        {
            "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "ROBOTSTXT_OBEY": False,
            "DOWNLOAD_DELAY": 1,
            "RANDOMIZE_DOWNLOAD_DELAY": 0.5,
            "CONCURRENT_REQUESTS_PER_DOMAIN": 8,
            "AUTOTHROTTLE_ENABLED": True,
            "AUTOTHROTTLE_START_DELAY": 1,
            "AUTOTHROTTLE_MAX_DELAY": 10,
            "AUTOTHROTTLE_TARGET_CONCURRENCY": 4.0,
            "FEEDS": {
                "top_combolists_today.json": {
                    "format": "json",
                    "overwrite": True,
                }
            },
            "ITEM_PIPELINES": {
                "scrapy_mybb_scraper.pipelines.MybbPipeline": 300,
            },
        }
    )

    # Import the spider after setting up the process
    from scrapy_mybb_scraper.spiders.mybb_spider import MybbSpider

    # Start the crawling process with custom arguments
    process.crawl(MybbSpider, max_pages=30, top_n=10)
    # The script will block here until the crawling is finished
    process.start()

    print(
        "\nScraping completed! Check 'top_combolists_today.txt' and 'top_combolists_today.json' for results."
    )


if __name__ == "__main__":
    run_scraper()
