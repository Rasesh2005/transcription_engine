from .utils import strip_tags, strip_attributes
from bs4 import BeautifulSoup
import json
from datetime import datetime
import uuid
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class LndocsSpider(CrawlSpider):
    name = "lndocs"
    allowed_domains = ["github.com"]
    start_urls = ["https://github.com/t-bast/lightning-docs"]

    rules = (
        Rule(
            LinkExtractor(allow=r"blob/master/.*\.md$"),
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

        item["id"] = "lndocs-" + str(uuid.uuid4())

        if "<h" in article.lower():
            title_node = BeautifulSoup(article, "html.parser").find(["h1", "h2", "h3", "h4", "h5", "h6"])
            item["title"] = "[Lightning-docs ] " + title_node.text.strip() if title_node else "[Lightning-docs ] Untitled"
        else:
            import re
            match = re.search(r'^(?:#+|=+)\s*(.+?)\s*(?:=+)?$', article, re.MULTILINE)
            item["title"] = "[Lightning-docs ] " + match.group(1).strip() if match else "[Lightning-docs ] " + response.url.split("/")[-1]

        if not item["title"]:
            return None

        item["body_formatted"] = strip_attributes(article) if "<" in article else article
        item["body"] = strip_tags(article) if "<" in article else article
        item["body_type"] = "html"
        item["authors"] = ["Bastien Teinturier"]
        item["domain"] = self.start_urls[0]
        item["url"] = response.url
        item["created_at"] = datetime.utcnow().isoformat()
        item["indexed_at"] = datetime.utcnow().isoformat()

        return item
