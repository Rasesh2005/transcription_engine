from .utils import strip_tags, strip_attributes
from datetime import datetime
import uuid
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class BitcoinOpsSpider(CrawlSpider):
    """
    Scrapes Bitcoin Optech newsletter articles.

    Index page:  https://bitcoinops.org/en/newsletters/
    Structure:   <ul class="post-list">
                   <li>
                     <span class="post-meta">DATE</span>
                     <h3><a class="post-link" href="/en/newsletters/YYYY/MM/DD/">TITLE</a></h3>
                     <p>SUMMARY</p>
                   </li>
                 </ul>

    Individual newsletter pages have the full content inside:
      <div class="post-content"> ... <div class="language-plaintext"> sections etc.

    Framework: Scrapy CrawlSpider — follows links from the newsletter index to
               each newsletter's individual page, then parses the article body.
    Output dict keys: id, title, body_formatted, body, body_type,
                      authors, domain, url, created_at, indexed_at
    """
    name = "bitcoinops"
    allowed_domains = ["bitcoinops.org"]
    start_urls = ["https://bitcoinops.org/en/newsletters/"]

    rules = (
        Rule(
            LinkExtractor(allow=r"/en/newsletters/\d{4}/\d{2}/\d{2}/"),
            callback="parse_item",
            follow=False,
        ),
    )

    def parse_item(self, response):
        item = {}

        # Full article body is inside <div class="post-content">
        post_content = response.xpath('//div[@class="post-content"]')
        paragraphs = post_content.xpath(".//p").getall()
        body_to_be_parsed = "".join(paragraphs)

        if not body_to_be_parsed:
            return None

        title = response.xpath('//h1[@class="post-title"]/text()').get()
        if not title:
            # Fallback: grab from <title> tag
            title = response.xpath("//title/text()").get()

        if not title:
            return None

        # Date is in <time class="dt-published" datetime="YYYY-MM-DD">
        date_str = response.xpath('//time[@class="dt-published"]/@datetime').get()
        if not date_str:
            # Try <span class="post-meta"> format from index page context
            date_str = response.xpath('//span[@class="post-meta"]/text()').get()

        try:
            created_at = datetime.fromisoformat(date_str).isoformat() if date_str else datetime.utcnow().isoformat()
        except (ValueError, TypeError):
            created_at = datetime.utcnow().isoformat()

        item["id"] = "bitcoinops-" + str(uuid.uuid4())
        item["title"] = title.strip()
        item["body_formatted"] = strip_attributes(body_to_be_parsed)
        item["body"] = strip_tags(body_to_be_parsed)
        item["body_type"] = "html"
        item["authors"] = ["Bitcoin Optech"]
        item["domain"] = "https://bitcoinops.org"
        item["url"] = response.url
        item["created_at"] = created_at
        item["indexed_at"] = datetime.utcnow().isoformat()

        return item
