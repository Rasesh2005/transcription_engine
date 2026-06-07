from datetime import datetime
from bs4 import BeautifulSoup
import json
from .utils import strip_tags, strip_attributes
from scrapy.exceptions import DropItem
import uuid
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class GrokkingbtcSpider(CrawlSpider):
    name = "grokkingbtc"
    allowed_domains = ["github.com"]
    start_urls = ["https://github.com/kallerosenbaum/grokkingbitcoin"]

    rules = (
        Rule(
            LinkExtractor(allow=r"blob/master/.*\.adoc$"),
            callback="parse_item",
        ),
    )

    def parse_item(self, response):
        item = {}
        soup = BeautifulSoup(response.text, "html.parser")
        script_tags = soup.find_all("script")
        json_object = None
        for script in script_tags:
            try:
                if script.string:
                    data = json.loads(script.string)
                    if "payload" in data:
                        json_object = data
                        break
            except Exception:
                continue
        if not json_object:
            return None

        payload = json_object["payload"]
        if "blob" in payload and "richText" in payload["blob"]:
            article = payload["blob"]["richText"]
        else:
            raw_lines = payload.get("codeViewBlobLayoutRoute.StyledBlob", {}).get("rawLines", [])
            article = "\n".join(raw_lines)
            
        item["id"] = "grokkingbtc-" + str(uuid.uuid4())

        # Try finding h1-h6 if HTML
        if "<h" in article.lower():
            title_node = BeautifulSoup(article, "html.parser").find(["h1", "h2", "h3", "h4", "h5", "h6"])
            item["title"] = "[Grokking Bitcoin] " + title_node.text.strip() if title_node else "[Grokking Bitcoin] Untitled"
        else:
            # Try finding asciidoc or markdown heading
            import re
            match = re.search(r'^(?:#+|=+)\s*(.+?)\s*(?:=+)?$', article, re.MULTILINE)
            item["title"] = "[Grokking Bitcoin] " + match.group(1).strip() if match else "[Grokking Bitcoin] " + response.url.split("/")[-1]

        if not item["title"]:
            return None

        item["body_formatted"] = strip_attributes(article) if "<" in article else article
        item["body"] = strip_tags(article) if "<" in article else article
        item["body_type"] = "html"
        item["authors"] = ["Kalle Rosenbaum"]
        item["domain"] = self.start_urls[0]
        item["url"] = response.url
        item["created_at"] = datetime.utcnow().isoformat()
        item["indexed_at"] = datetime.utcnow().isoformat()

        return item
