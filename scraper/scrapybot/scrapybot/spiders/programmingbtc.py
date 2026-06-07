import uuid
import json
from bs4 import BeautifulSoup
from .utils import strip_tags, strip_attributes
from datetime import datetime
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class ProgrammingbtcSpider(CrawlSpider):
    name = "programmingbtc"
    allowed_domains = ["github.com"]
    start_urls = ["https://github.com/jimmysong/programmingbitcoin"]

    rules = (
        Rule(
            LinkExtractor(allow=r"blob/master/.*\.asciidoc$"),
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

        item["id"] = "programmingbtc-" + str(uuid.uuid4())
        
        if "<h" in article.lower():
            title_node = BeautifulSoup(article, "html.parser").find(["h1", "h2", "h3", "h4", "h5", "h6"])
            item["title"] = "[Programming Bitcoin] " + title_node.text.strip() if title_node else "[Programming Bitcoin] Untitled"
        else:
            import re
            match = re.search(r'^(?:#+|=+)\s*(.+?)\s*(?:=+)?$', article, re.MULTILINE)
            item["title"] = "[Programming Bitcoin] " + match.group(1).strip() if match else "[Programming Bitcoin] " + response.url.split("/")[-1]

        if not item["title"]:
            return None

        item["body_formatted"] = strip_attributes(article) if "<" in article else article
        item["body"] = strip_tags(article) if "<" in article else article
        item["body_type"] = "html"
        item["authors"] = ["Jimmy Song"]
        item["domain"] = self.start_urls[0]
        item["url"] = response.url
        item["created_at"] = datetime.utcnow().isoformat()
        item["indexed_at"] = datetime.utcnow().isoformat()

        return item
