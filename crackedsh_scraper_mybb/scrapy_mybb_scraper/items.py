# -*- coding: utf-8 -*-
"""Scrapy items for MyBB forum scraper."""

# Third-party imports
import scrapy


class ThreadItem(scrapy.Item):
    """Scrapy Item representing a forum thread."""

    title = scrapy.Field()
    url = scrapy.Field()
    number = scrapy.Field()
    normalized_size = scrapy.Field()
    date_text = scrapy.Field()
