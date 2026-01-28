# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import scrapy


class MybbPipeline:
    def __init__(self):
        self.items = []

    @classmethod
    def from_crawler(cls, crawler):
        pipeline = cls()
        crawler.signals.connect(pipeline.spider_opened, signal=scrapy.signals.spider_opened)
        crawler.signals.connect(pipeline.spider_closed, signal=scrapy.signals.spider_closed)
        return pipeline

    def spider_opened(self, spider):
        self.items = []
        self.spider = spider  # Store spider reference

    def spider_closed(self, spider):
        # Sort all collected items by number (highest first) and take top N
        top_items = sorted(self.items, key=lambda x: x.get('number', 0), reverse=True)[:self.spider.top_n]

        # Save top items to a file
        with open('top_combolists_today.txt', 'w', encoding='utf-8') as f:
            f.write(f"# Top {self.spider.top_n} Combolists from Today\n\n")
            for i, item in enumerate(top_items, 1):
                f.write(f"{i}. {item['title']}\n")
                f.write(f"   Link: {item['url']}\n\n")

        print(f"\nFound {len(self.items)} threads from today with numbers across {self.spider.page_count} pages")
        print(f"Returning top {len(top_items)} combolists")

    def process_item(self, item, spider):
        self.items.append(dict(item))
        return item