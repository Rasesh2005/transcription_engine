import uuid
from bs4 import BeautifulSoup
import json
from .utils import strip_tags, strip_attributes, convert_to_iso_datetime
from datetime import datetime
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule


class AndreasbooksSpider(CrawlSpider):
    name = "andreasbooks"
    allowed_domains = ["github.com"]
    start_urls = [
        "https://github.com/bitcoinbook/bitcoinbook",
        "https://github.com/lnbook/lnbook",
    ]

    rules = (
        Rule(
            LinkExtractor(
                allow=[r"blob/develop/.*\d+.*"], deny=[r"part"]
            ),
            callback="parse_item",
            follow=True,
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

        item["id"] = (
            "masteringbitcoin-" + str(uuid.uuid4())
            if "bitcoinbook" in response.url
            else "masteringln-" + str(uuid.uuid4())
        )

        prefix = "[Mastering Bitcoin] " if "bitcoinbook" in response.url else "[Mastering Lightning] "
        
        # Try finding h2 if HTML
        if "<h2" in article.lower():
            title_node = BeautifulSoup(article, "html.parser").find("h2")
            item["title"] = prefix + title_node.text.strip() if title_node else prefix + "Untitled"
        else:
            # Try finding asciidoc or markdown h2/h1 (e.g., == Title == or ## Title or = Title)
            import re
            match = re.search(r'^(?:#+|=+)\s*(.+?)\s*(?:=+)?$', article, re.MULTILINE)
            item["title"] = prefix + match.group(1).strip() if match else prefix + response.url.split("/")[-1]

        if not item["title"]:
            return None

        item["body_formatted"] = strip_attributes(article) if "<" in article else article
        item["body"] = strip_tags(article) if "<" in article else article
        item["body_type"] = "html"
        item["url"] = response.url
        item["authors"] = (
            ["Andreas Antonopoulos"]
            if "bitcoinbook" in response.url
            else ["Andreas Antonopoulos", "Olaoluwa Osuntokun", "Rene Pickhardt"]
        )
        item["domain"] = (
            self.start_urls[0] if "bitcoinbook" in response.url else self.start_urls[1]
        )
        item["created_at"] = convert_to_iso_datetime(
            "2022-11-15" if "bitcoinbook" in response.url else "2023-04-22"
        )  # date of most recent commit
        item["indexed_at"] = datetime.utcnow().isoformat()
        return item
