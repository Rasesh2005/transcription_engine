from bs4 import BeautifulSoup
import json
import re
import requests
import os
from datetime import datetime
from loguru import logger

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
LOG_FILE = os.path.abspath(os.path.join(BASE_DIR, "..", "logs", "server_dev.log"))

os.makedirs(OUTPUTS_DIR, exist_ok=True)

logger.remove()
logger.add(LOG_FILE, level="DEBUG", rotation="10 MB", retention="7 days")


if __name__ == "__main__":

    site = 'https://github.com/bitcoinbook/bitcoinbook/blob/develop'
    chapters = ['/ch01.asciidoc', '/ch02.asciidoc', '/ch03.asciidoc', '/ch04.asciidoc',
                '/ch05.asciidoc', '/ch06.asciidoc', '/ch07.asciidoc', '/ch08.asciidoc',
                '/ch09.asciidoc', '/ch10.asciidoc', '/ch11.asciidoc', '/ch12.asciidoc']
    chapter_links = [f"{site}{chapter}" for chapter in chapters]

    documents = []
    for url in chapter_links:
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            title_tag = soup.find('h2', dir='auto')
            body_tag = soup.find('div', id='readme')
            if not title_tag or not body_tag:
                logger.error(f"Missing title or body in {url}")
                continue
            title = title_tag.get_text()
            body = body_tag.get_text()
            body_type = "md"
            author = "Andreas Antonopoulous"
            chapter_number = ''.join(re.findall(r'\d+', url))
            id = "bitcoinbook-chapter-" + chapter_number
            tags = ""
            domain = "https://github.com/bitcoinbook/bitcoinbook"
            created_at = "2022-11-15"  # date of most recent commit

            document = {
                "title": title,
                "body": body,
                "body_type": body_type,
                "author": author,
                "id": id,
                "tags": tags,
                "domain": domain,
                "url": url,
                "created_at": created_at,
                "indexed_at": datetime.utcnow().isoformat()
            }

            doc_id = document.get("id", "unknown_id")
            doc_dir = os.path.join(OUTPUTS_DIR, "bitcoinbook", doc_id)
            os.makedirs(doc_dir, exist_ok=True)
            
            json_path = os.path.join(doc_dir, "data.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(document, f, ensure_ascii=False, default=str, indent=2)
                
            md_path = os.path.join(doc_dir, "content.md")
            with open(md_path, "w", encoding="utf-8") as f:
                title = document.get("title", "No Title")
                body = document.get("body", "")
                f.write(f"# {title}\n\n{body}")
                
            logger.info(f"Saved: {doc_id} — {document.get('title', '')}")
            documents.append(document)
        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            
    logger.info("Number of documents processed: " + str(len(documents)))
