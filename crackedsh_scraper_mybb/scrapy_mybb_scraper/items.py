# -*- coding: utf-8 -*-
import scrapy


class ThreadItem(scrapy.Item):
    title = scrapy.Field()
    url = scrapy.Field()
    number = scrapy.Field()
    normalized_size = scrapy.Field()
    date_text = scrapy.Field()