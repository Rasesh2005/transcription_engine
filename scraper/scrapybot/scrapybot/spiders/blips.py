from datetime import datetime
from bs4 import BeautifulSoup
import json

from .utils import get_details, strip_tags, strip_attributes, convert_to_iso_datetime
import uuid
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class BlipsSpider(CrawlSpider):
    name = "blips"
    allowed_domains = ["github.com"]
    start_urls = ["https://github.com/lightning/blips"]

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
            try:
                details_text = BeautifulSoup(article, "html.parser").find("code").text
            except Exception:
                details_text = ""
        else:
            raw_lines = payload.get("codeViewBlobLayoutRoute.StyledBlob", {}).get("rawLines", [])
            article = "\n".join(raw_lines)
            # Find metadata block (often fenced by ``` or --- at start)
            details_text = "\n".join(raw_lines[:25])
            
        details = details_text.split("\n")
        blip_info = get_details(details)
        item["id"] = "blips-" + str(uuid.uuid4())
        
        # Robustly handle missing metadata fields
        title = blip_info.get("Title")
        item["title"] = title if title else "Untitled"

        if not item["title"] or item["title"] == "Untitled":
            item["title"] = response.url.split("/")[-1].replace(".md", "")

        item["body_formatted"] = strip_attributes(article) if "<" in article else article
        item["body"] = strip_tags(article) if "<" in article else article
        item["body_type"] = "html"
        author = blip_info.get("Author")
        item["authors"] = [author] if author else []
        item["domain"] = self.start_urls[0]
        item["url"] = response.url
        created = blip_info.get("Created")
        item["created_at"] = convert_to_iso_datetime(created) if created else datetime.utcnow().isoformat()
        item["indexed_at"] = datetime.utcnow().isoformat()

        return item
