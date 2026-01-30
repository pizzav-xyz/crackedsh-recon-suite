#!/usr/bin/env python3
"""Unified MyBB Forum Scraper for cracked.sh using Scrapy.

Reimplementation of the original unified scraper using Scrapy framework.
"""

import argparse
import os
import sys

# Third-party imports
from scrapy.crawler import CrawlerProcess


def run_scraper(max_pages=30, top_n=10):
    """Run the MyBB scraper using Scrapy.

    Args:
        max_pages (int): Maximum number of pages to scrape. Defaults to 30.
        top_n (int): Number of top combolists to return. Defaults to 10.
    """
    print("Starting MyBB Forum Scraper for cracked.sh using Scrapy...")
    print(
        f"Finding top {top_n} combolists from today with highest numbers in titles..."
    )

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
    process.crawl(MybbSpider, max_pages=max_pages, top_n=top_n)
    # The script will block here until the crawling is finished
    process.start()

    print(
        f"\nScraping completed! Check 'top_combolists_today.txt' and 'top_combolists_today.json' for results."
    )


def print_results():
    """Print the results to console."""
    try:
        with open("top_combolists_today.txt", "r", encoding="utf-8") as f:
            content = f.read()
            print(content)
    except FileNotFoundError:
        print(
            "No results file found. The scraper may not have found any threads from today."
        )


def main():
    """Main entry point for the scraper."""
    parser = argparse.ArgumentParser(
        description="Scrapy-based MyBB Forum Scraper for cracked.sh"
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=30,
        help="Maximum number of pages to scrape (default: 30)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="Number of top combolists to return (default: 10)",
    )
    parser.add_argument(
        "--print-results",
        action="store_true",
        help="Print results to console after scraping",
    )

    args = parser.parse_args()

    # Run the scraper
    run_scraper(args.max_pages, args.top_n)

    # Optionally print results
    if args.print_results:
        print_results()


if __name__ == "__main__":
    main()
