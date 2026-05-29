from .utils import strip_tags, strip_attributes
from datetime import datetime
import uuid
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class BitcoinDevGuideSpider(CrawlSpider):
    """
    Scrapes the Bitcoin.org Developer Guide (developer.bitcoin.org).

    Start URLs:
      - https://developer.bitcoin.org/devguide/        (Developer Guide)
      - https://developer.bitcoin.org/reference/       (Reference)
      - https://developer.bitcoin.org/examples/        (Examples)

    Article page structure:
      <div class="content-left">
        <h1> or <h2> — section title
        <p> — body paragraphs
      </div>

    Or the more generic:
      <main role="main">
        <div class="container">
          <h1> ... </h1>
          <p> ... </p>
        </div>
      </main>

    Framework: Scrapy CrawlSpider — follows all /devguide/, /reference/,
               and /examples/ links.
    Output dict keys: id, title, body_formatted, body, body_type,
                      authors, domain, url, created_at, indexed_at
    """
    name = "bitcoindevguide"
    allowed_domains = ["developer.bitcoin.org"]
    start_urls = [
        "https://developer.bitcoin.org/devguide/",
        "https://developer.bitcoin.org/reference/",
        "https://developer.bitcoin.org/examples/",
    ]

    rules = (
        Rule(
            LinkExtractor(
                allow=[
                    r"/devguide/",
                    r"/reference/",
                    r"/examples/",
                ],
                deny=[r"#"],  # skip anchor-only links
            ),
            callback="parse_item",
            follow=True,
        ),
    )

    def parse_item(self, response):
        item = {}

        # Try the developer.bitcoin.org-specific content container
        # The site uses Sphinx-generated HTML
        title = (
            response.xpath('//h1/text()').get()
            or response.xpath('//div[@class="section"]//h1/text()').get()
        )
        if not title:
            return None
        title = title.strip()

        # Content lives in .content-left or the main doc body
        content = response.xpath('//div[@class="content-left"]')
        if not content:
            content = response.xpath('//div[@role="main"]')
        if not content:
            content = response.xpath('//main')

        paragraphs = content.xpath(".//p").getall()
        body_to_be_parsed = "".join(paragraphs)

        if not body_to_be_parsed or len(strip_tags(body_to_be_parsed).strip()) < 80:
            return None

        item["id"] = "bitcoindevguide-" + str(uuid.uuid4())
        item["title"] = title
        item["body_formatted"] = strip_attributes(body_to_be_parsed)
        item["body"] = strip_tags(body_to_be_parsed)
        item["body_type"] = "html"
        item["authors"] = ["Bitcoin.org Developers"]
        item["domain"] = "https://developer.bitcoin.org"
        item["url"] = response.url
        item["created_at"] = datetime.utcnow().isoformat()
        item["indexed_at"] = datetime.utcnow().isoformat()

        return item
