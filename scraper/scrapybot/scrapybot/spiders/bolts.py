import uuid
import json
import re
from bs4 import BeautifulSoup
from .utils import strip_tags, strip_attributes, convert_to_iso_datetime
from datetime import datetime
from .utils import strip_tags
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class BoltsSpider(CrawlSpider):
    name = "bolts"
    allowed_domains = ["github.com"]
    start_urls = ["https://github.com/lightning/bolts"]

    rules = (
        Rule(
            LinkExtractor(allow=r"blob/master/.*\.md$"),
            callback="parse_item",
        ),
    )

    def parse_item(self, response):
        item = {}
        # Regular expression pattern to match URLs containing numbers
        pattern = r"\d"
        if not re.search(pattern, response.url):
            return None

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
            body_to_be_parsed = payload["blob"]["richText"]
        else:
            raw_lines = payload.get("codeViewBlobLayoutRoute.StyledBlob", {}).get("rawLines", [])
            body_to_be_parsed = "\n".join(raw_lines)

        item["id"] = "bolts-" + str(uuid.uuid4())
        
        if "<h1" in body_to_be_parsed.lower():
            title_node = BeautifulSoup(body_to_be_parsed, "html.parser").find("h1")
            item["title"] = title_node.text.strip() if title_node else "Untitled"
        else:
            match = re.search(r'^#\s+(.+)$', body_to_be_parsed, re.MULTILINE)
            item["title"] = match.group(1).strip() if match else "Untitled"

        if not item["title"] or item["title"] == "Untitled":
            # Some bolts don't have an h1, fallback to filename or skip
            item["title"] = response.url.split("/")[-1].replace(".md", "")

        item["body_formatted"] = strip_attributes(body_to_be_parsed) if "<" in body_to_be_parsed else body_to_be_parsed
        item["body"] = strip_tags(body_to_be_parsed) if "<" in body_to_be_parsed else body_to_be_parsed
        item["body_type"] = "html"
        item["authors"] = ["Spec"]
        item["domain"] = "https://github.com/lightning/bolts"
        item["created_at"] = convert_to_iso_datetime("2023-05-11")
        item["url"] = response.url
        item["indexed_at"] = datetime.utcnow().isoformat()

        return item
