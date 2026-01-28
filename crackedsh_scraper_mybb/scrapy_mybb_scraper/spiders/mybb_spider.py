import scrapy
import re
from urllib.parse import urljoin
from scrapy_mybb_scraper.items import ThreadItem


class MyBBScraperUtils:
    """Utility class for MyBB forum scraping operations"""

    @staticmethod
    def normalize_size_string(size_str):
        """Normalize size string to integer"""
        if not size_str:
            return 0

        # Look for patterns like "502.7k", "14.6k", "11.2M", "910K", etc.
        # These are numbers followed IMMEDIATELY by multipliers (no space allowed)
        multiplier_pattern = r'(\d+(?:\.\d+)?)([kmgtbpKMGTBP])(?!\w)'
        matches = re.findall(multiplier_pattern, str(size_str))

        if matches:
            # Get the match with the largest number
            best_match = max(matches, key=lambda x: float(x[0]))
            num_part = float(best_match[0])
            mult_part = best_match[1].lower()

            multipliers = {
                'k': 1000,
                'm': 1000000,
                'g': 1000000000,
                't': 1000000000000,
                'b': 1000000000000,  # Note: 'b' usually means billion, not byte
                'p': 1000000000000000,
            }

            return int(num_part * multipliers.get(mult_part, 1))

        # If no multiplier patterns found, just extract the largest standalone number
        # Use a pattern that captures numbers but excludes those followed by letters that could be multipliers
        numbers = re.findall(r'\b\d+(?:\.\d+)?\b', str(size_str))
        if not numbers:
            try:
                return int(float(size_str))
            except ValueError:
                return 0

        # Find the largest number that makes sense as a quantity
        # Skip numbers with multiple decimal points (like IP addresses: 1.256.800)
        valid_numbers = []
        for num_str in numbers:
            if num_str.count('.') <= 1:
                try:
                    num_val = float(num_str)
                    valid_numbers.append(num_val)
                except ValueError:
                    continue

        if not valid_numbers:
            return 0

        # Get the largest valid number
        return int(max(valid_numbers))

    @staticmethod
    def extract_numbers_from_title(title):
        """Extract the largest number from the title"""
        numbers = re.findall(r'\d+(?:\.\d+)?', title)
        if numbers:
            return max(float(n) for n in numbers)
        return 0

    @staticmethod
    def is_from_today(date_str):
        """Check if thread is from today (strict)"""
        if not date_str:
            return False  # If no date info, don't assume it's from today

        date_str = date_str.lower().strip()

        # Check for "today" explicitly
        if "today" in date_str:
            return True

        # Check for relative time expressions with "ago"
        if "ago" in date_str:
            # Patterns that indicate today: "X seconds/minutes/hours ago", "an hour ago", etc.
            # Use regex to match time expressions
            # Match patterns like: "2 hours ago", "an hour ago", "15 minutes ago", etc.

            # First, check for numeric time expressions (e.g., "2 hours ago", "1 minute ago")
            time_match = re.search(r'(\d+)\s*(second|minute|hour|day|week|month|year)s?\s+ago', date_str)
            if time_match:
                time_num = int(time_match.group(1))
                time_unit = time_match.group(2)

                # Only seconds, minutes, and hours ago are considered today
                if time_unit in ["second", "minute", "hour"]:
                    return True
                elif time_unit == "day":
                    # Only if it's 0 days ago or less than 1 day (meaning today)
                    return time_num < 1
                else:
                    # Days, weeks, months, years ago are not today
                    return False

            # Check for non-numeric expressions like "an hour ago", "a day ago", etc.
            # "an hour ago", "a minute ago", "a few seconds ago" - these are today
            if any(pattern in date_str for pattern in [
                "an hour ago", "a minute ago", "a second ago", "a few seconds ago",
                "less than a minute ago", "under a minute ago"
            ]):
                return True

            # "a day ago", "a week ago", etc. are not today
            if any(pattern in date_str for pattern in [
                "a day ago", "an day ago", "a week ago", "an week ago",
                "a month ago", "an month ago", "a year ago", "an year ago"
            ]):
                return False

        # If we have a date string but it doesn't match our "today" criteria, assume not today
        return False


class MybbSpider(scrapy.Spider):
    name = 'mybb'
    allowed_domains = ['cracked.sh']
    # Use the URL sorted by thread creation date (newest first) to find most recent threads
    start_urls = ['https://cracked.sh/Forum-Combolists--297?sortby=started&order=desc']

    custom_settings = {
        'FEEDS': {
            'top_combolists_today.json': {
                'format': 'json',
                'overwrite': True,
            }
        }
    }

    def __init__(self, max_pages=30, top_n=10, *args, **kwargs):
        super(MybbSpider, self).__init__(*args, **kwargs)
        self.max_pages = int(max_pages)
        self.top_n = int(top_n)
        self.page_count = 1
        self.all_threads = []
        self.utils = MyBBScraperUtils()

    def parse(self, response):
        """Parse the forum page and extract thread information"""

        self.logger.info(f"Scraping page {self.page_count}...")

        # Find thread rows in MyBB structure based on actual HTML
        thread_rows = response.css('tr.inline_row')

        self.logger.debug(f"Found {len(thread_rows)} thread rows")

        # Track if this page has any recent threads (from today)
        has_recent_threads_on_page = False

        for row_idx, row in enumerate(thread_rows):
            # Find thread title links using the actual HTML structure observed from cracked.sh
            # Each thread row has a d-flex container with the link inside
            flex_containers = row.css('div.d-flex.align-items-center')

            for container in flex_containers:
                # Look for links within the subject_old spans - these are the actual thread links
                # Based on the HTML, the links are in <a> tags inside <span class="subject_old">
                subject_links = container.css('span.subject_old a')

                for link in subject_links:
                    title = link.css('::text').get('').strip()
                    href = link.css('::attr(href)').get('')

                    # Skip if this looks like a pagination number or empty
                    if not title or len(title) <= 2 and title.isdigit():
                        continue

                    # Extract number from title - enhanced to handle formats like [1.256.800], 328.646, 502.7k, etc.
                    # Use the normalize_size_string function which handles multipliers and complex formats
                    final_number = self.utils.normalize_size_string(title)

                    if final_number > 0:
                        # Find thread creation date (not last post date) in the same row
                        date_text = ""

                        # Look in the parent row for date information in author smalltext divs
                        # Based on the HTML, dates are in <span class="thread-date">
                        author_divs = row.css('div.author.smalltext')
                        for div in author_divs:
                            date_spans = div.css('span.thread-date::text')
                            for span_text in date_spans.getall():
                                span_text = span_text.strip()
                                if span_text and ('ago' in span_text.lower() or 'today' in span_text.lower() or 'yesterday' in span_text.lower()):
                                    date_text = span_text
                                    break
                            if date_text:
                                break

                        # If we still don't have date text, try a broader search in the row
                        if not date_text:
                            all_spans_with_dates = row.css('span.thread-date::text').getall()
                            for span_text in all_spans_with_dates:
                                span_text = span_text.strip()
                                if span_text and ('ago' in span_text.lower() or 'today' in span_text.lower() or 'yesterday' in span_text.lower()):
                                    date_text = span_text
                                    break

                        # Check if thread is from today
                        is_today = self.utils.is_from_today(date_text)

                        if is_today:
                            has_recent_threads_on_page = True  # Mark that we found a recent thread
                            # Create the item
                            item = ThreadItem()
                            item['title'] = title
                            item['url'] = urljoin('https://cracked.sh/', href)
                            item['number'] = final_number
                            item['normalized_size'] = final_number
                            item['date_text'] = date_text

                            yield item
                        else:
                            self.logger.debug(f"Thread is not from today: '{title}', date: '{date_text}'")
                    else:
                        self.logger.debug(f"No number found in title: '{title}'")

        # Look for next page link - based on actual HTML structure
        next_link = None

        # Based on the HTML, pagination links are in the form:
        # <a href="forumdisplay.php?fid=297&amp;page=2&amp;sortby=started" class="pagination_page">2</a>
        # Look for next page number (current page + 1)
        next_page_num = self.page_count + 1
        next_link = response.css(f'a[href*="page={next_page_num}"]::attr(href)').get()

        # If not found, try with more general selectors for pagination links
        if not next_link:
            # Look for links with page parameter that's greater than current page
            for link in response.css('a'):
                href = link.css('::attr(href)').get('')
                if href and 'page=' in href and 'fid=297' in href:
                    # Extract page number from href
                    import re
                    page_match = re.search(r'page=(\d+)', href)
                    if page_match:
                        page_num = int(page_match.group(1))
                        if page_num > self.page_count:
                            next_link = href
                            break

        # If still not found, try the general pagination structure
        if not next_link:
            pagination_links = response.css('a.pagination_page::attr(href)').getall()
            for href in pagination_links:
                if 'page=' in href and 'fid=297' in href:
                    import re
                    page_match = re.search(r'page=(\d+)', href)
                    if page_match:
                        page_num = int(page_match.group(1))
                        if page_num > self.page_count:
                            next_link = href
                            break

        # Continue to next page if available and within max_pages limit
        # Continue to next page regardless of whether recent threads were found
        # since we want to scan all pages up to max_pages to find all threads from today
        if next_link and self.page_count < self.max_pages:
            self.page_count += 1
            # Convert URL-encoded ampersands if needed
            next_link = next_link.replace('&amp;', '&')
            next_url = urljoin(response.url, next_link)
            self.logger.debug(f"Following to next page: {next_url}")
            yield response.follow(next_url, callback=self.parse)
        elif not next_link:
            self.logger.debug("No more pages found")
        else:
            self.logger.debug("Max pages reached")