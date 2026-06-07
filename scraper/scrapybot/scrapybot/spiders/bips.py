import re
from bs4 import BeautifulSoup
import json
from datetime import datetime
from .utils import strip_tags, strip_attributes, convert_to_iso_datetime
import uuid
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class BipsSpider(CrawlSpider):
    name = "bips"
    allowed_domains = ["github.com"]
    start_urls = ["https://github.com/bitcoin/bips"]

    rules = (
        Rule(
            LinkExtractor(restrict_xpaths="//td/a"),
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
            body_to_be_parsed = payload["blob"]["richText"]
        else:
            raw_lines = payload.get("codeViewBlobLayoutRoute.StyledBlob", {}).get("rawLines", [])
            body_to_be_parsed = "\n".join(raw_lines)
            
        try:
            bip_details = BeautifulSoup(body_to_be_parsed, "html.parser").find("pre").text
        except Exception:
            # Fallback for raw text: just grab the first 25 lines (usually contains metadata)
            bip_details = "\n".join(body_to_be_parsed.split("\n")[:25])
            
        metadata = self.parse_details(bip_details)
        item["id"] = "bips-" + str(uuid.uuid4())
        
        # Robustly handle missing metadata fields
        titles = metadata.get("Title")
        item["title"] = titles[0] if titles else "Untitled"

        if not item["title"]:
            return None

        item["body_formatted"] = strip_attributes(body_to_be_parsed) if "<" in body_to_be_parsed else body_to_be_parsed
        item["body"] = strip_tags(body_to_be_parsed) if "<" in body_to_be_parsed else body_to_be_parsed
        item["body_type"] = "html"
        authors = metadata.get("Author")
        item["authors"] = authors if authors else []
        item["domain"] = self.start_urls[0]
        item["url"] = response.url
        created = metadata.get("Created")
        item["created_at"] = convert_to_iso_datetime(created[0]) if created else datetime.utcnow().isoformat()
        item["indexed_at"] = datetime.utcnow().isoformat()
        return item

    def parse_details(self, details):
        data_lines = details.split("\n")
        data_dict = {}
        current_key = None

        for line in data_lines:
            if line.strip():
                if ":" in line:
                    key, value = line.split(":", 1)
                    current_key = key.strip()
                    if current_key == "Author":
                        # Remove emails from the value
                        value = re.sub(r"<[^>]+>", "", value)
                    data_dict[current_key] = [value.strip()]
                else:
                    print(line)
                    line = re.sub(r"<[^>]+>", "", line)
                    data_dict[current_key].append(line.strip())

        return data_dict
