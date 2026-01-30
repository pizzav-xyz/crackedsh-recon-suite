"""Scrapy pipelines for processing MyBB forum items.

Don't forget to add your pipeline to the ITEM_PIPELINES setting
See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
"""

# Third-party imports
import scrapy


class MybbPipeline:
    """Pipeline for processing and sorting MyBB forum thread items."""

    def __init__(self):
        """Initialize the pipeline."""
        self.items = []

    @classmethod
    def from_crawler(cls, crawler):
        """Create pipeline from crawler and connect signals."""
        pipeline = cls()
        crawler.signals.connect(
            pipeline.spider_opened, signal=scrapy.signals.spider_opened
        )
        crawler.signals.connect(
            pipeline.spider_closed, signal=scrapy.signals.spider_closed
        )
        return pipeline

    def spider_opened(self, spider):
        """Called when spider is opened."""
        self.items = []
        self.spider = spider  # Store spider reference

    def spider_closed(self, spider):
        """Called when spider is closed.

        Sorts all collected items by number (highest first) and saves top N to file.
        """
        # Sort all collected items by number (highest first) and take top N
        top_items = sorted(self.items, key=lambda x: x.get("number", 0), reverse=True)[
            : self.spider.top_n
        ]

        # Save top items to a file
        with open("top_combolists_today.txt", "w", encoding="utf-8") as f:
            f.write(f"# Top {self.spider.top_n} Combolists from Today\n\n")
            for i, item in enumerate(top_items, 1):
                f.write(f"{i}. {item['title']}\n")
                f.write(f"   Link: {item['url']}\n\n")

        print(
            f"\nFound {len(self.items)} threads from today with numbers across "
            f"{self.spider.page_count} pages"
        )
        print(f"Returning top {len(top_items)} combolists")

    def process_item(self, item, spider):
        """Process each item and add to collection."""
        self.items.append(dict(item))
        return item
