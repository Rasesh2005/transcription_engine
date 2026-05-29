from .utils import strip_tags, strip_attributes
from datetime import datetime
import uuid
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class BlockstreamSpider(CrawlSpider):
    """
    Scrapes the Blockstream Blog (blog.blockstream.com) — a Ghost CMS blog.

    Index page:  https://blog.blockstream.com
    Pagination:  https://blog.blockstream.com/page/2/  (up to page 29)

    Post listing structure (index):
      <h2 class="post-card__title font-h2 text-white">
        <a href="/post-slug/">POST TITLE</a>
      </h2>
      <time datetime="YYYY-MM-DD" class="post-card__date ...">DATE</time>
      <div class="post-card__author-names ..."><a href="...">AUTHOR</a></div>

    Individual post page structure:
      <h1 class="post-title"> ... </h1>
      <section class="post-content"> ... </section>
      <time class="post-date" datetime="YYYY-MM-DD">

    Framework: Scrapy CrawlSpider — follows post links across paginated listing.
    Output dict keys: id, title, body_formatted, body, body_type,
                      authors, domain, url, created_at, indexed_at
    """
    name = "blockstream"
    allowed_domains = ["blog.blockstream.com"]
    start_urls = ["https://blog.blockstream.com"]

    rules = (
        # Follow pagination links like /page/2/
        Rule(
            LinkExtractor(allow=r"/page/\d+/"),
            follow=True,
        ),
        # Parse each individual blog post
        Rule(
            LinkExtractor(
                allow=r"blog\.blockstream\.com/[^/]+/$",
                deny=[r"/page/", r"/tag/", r"/author/", r"/blockstream-research/", r"/education/"],
            ),
            callback="parse_item",
            follow=False,
        ),
    )

    def parse_item(self, response):
        item = {}

        # Post content lives in <section class="post-content">
        post_section = response.xpath('//section[contains(@class,"post-content")]')
        if not post_section:
            # Fallback to <div class="post-content">
            post_section = response.xpath('//div[contains(@class,"post-content")]')

        paragraphs = post_section.xpath(".//p").getall()
        body_to_be_parsed = "".join(paragraphs)

        if not body_to_be_parsed:
            return None

        title = response.xpath('//h1[contains(@class,"post-title")]/text()').get()
        if not title:
            title = response.xpath("//h1/text()").get()
        if not title:
            return None

        # Author names from <a href="/author/..."> elements
        authors = response.xpath('//div[contains(@class,"post-author__name")]//a/text()').getall()
        if not authors:
            authors = response.xpath('//div[contains(@class,"post-card__author-names")]//a/text()').getall()
        if not authors:
            authors = ["Blockstream"]

        # Date from <time datetime="YYYY-MM-DD">
        date_str = response.xpath('//time/@datetime').get()
        try:
            created_at = datetime.fromisoformat(date_str).isoformat() if date_str else datetime.utcnow().isoformat()
        except (ValueError, TypeError):
            created_at = datetime.utcnow().isoformat()

        item["id"] = "blockstream-" + str(uuid.uuid4())
        item["title"] = title.strip()
        item["body_formatted"] = strip_attributes(body_to_be_parsed)
        item["body"] = strip_tags(body_to_be_parsed)
        item["body_type"] = "html"
        item["authors"] = [a.strip() for a in authors if a.strip()]
        item["domain"] = "https://blog.blockstream.com"
        item["url"] = response.url
        item["created_at"] = created_at
        item["indexed_at"] = datetime.utcnow().isoformat()

        return item
