from .utils import strip_tags, strip_attributes
from datetime import datetime
import uuid
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


# Bitcoin-relevant categories and keywords to filter wiki pages
BITCOIN_KEYWORDS = [
    "bitcoin", "lightning", "segwit", "taproot", "script", "wallet",
    "transaction", "block", "mining", "hash", "node", "peer", "bip",
    "signature", "multisig", "channel", "payment", "mempool", "utxo",
    "coinbase", "fork", "proof", "cryptography", "secp256k1",
]


class BitcoinWikiSpider(CrawlSpider):
    """
    Scrapes the Bitcoin Wiki (en.bitcoin.it/wiki/).

    Start URL: https://en.bitcoin.it/wiki/Main_Page
    Follows:   Only /wiki/ internal links (excludes Special:, User:, Talk:,
               File:, etc. which are MediaWiki meta-pages).

    Article page structure (MediaWiki):
      <h1 id="firstHeading">TITLE</h1>
      <div id="mw-content-text">
        <div class="mw-parser-output">
          <p>Content paragraphs...</p>
        </div>
      </div>

    Filtering: Only keeps pages whose title or body contains a bitcoin-related
               keyword to avoid scraping irrelevant wiki pages.

    Framework: Scrapy CrawlSpider
    Output dict keys: id, title, body_formatted, body, body_type,
                      authors, domain, url, created_at, indexed_at
    """
    name = "bitcoinwiki"
    allowed_domains = ["en.bitcoin.it"]
    start_urls = ["https://en.bitcoin.it/wiki/Main_Page"]

    # Only follow /wiki/ links; skip MediaWiki system pages
    rules = (
        Rule(
            LinkExtractor(
                allow=r"/wiki/[^:]+$",
                deny=[
                    r"/wiki/Special:",
                    r"/wiki/User:",
                    r"/wiki/Talk:",
                    r"/wiki/File:",
                    r"/wiki/Template:",
                    r"/wiki/Category:",
                    r"/wiki/Help:",
                    r"/wiki/Bitcoin_Wiki:",
                    r"\?action=",
                    r"\?oldid=",
                ],
            ),
            callback="parse_item",
            follow=True,
        ),
    )

    def parse_item(self, response):
        item = {}

        title = response.xpath('//h1[@id="firstHeading"]/text()').get()
        if not title:
            return None
        title = title.strip()

        # Get the main article content
        content_div = response.xpath('//div[@class="mw-parser-output"]')
        paragraphs = content_div.xpath(".//p").getall()
        body_to_be_parsed = "".join(paragraphs)

        if not body_to_be_parsed or len(strip_tags(body_to_be_parsed).strip()) < 100:
            return None  # Skip stubs and empty pages

        body_text = strip_tags(body_to_be_parsed).lower()
        title_lower = title.lower()

        # Filter: only keep pages relevant to Bitcoin
        if not any(kw in title_lower or kw in body_text for kw in BITCOIN_KEYWORDS):
            return None

        item["id"] = "bitcoinwiki-" + str(uuid.uuid4())
        item["title"] = title
        item["body_formatted"] = strip_attributes(body_to_be_parsed)
        item["body"] = strip_tags(body_to_be_parsed)
        item["body_type"] = "html"
        item["authors"] = ["Bitcoin Wiki Contributors"]
        item["domain"] = "https://en.bitcoin.it"
        item["url"] = response.url
        item["created_at"] = datetime.utcnow().isoformat()
        item["indexed_at"] = datetime.utcnow().isoformat()

        return item
