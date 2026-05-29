import json
import os
from loguru import logger

class TextFilePipeline:
    def open_spider(self, spider):
        spider_name = spider.name if hasattr(spider, "name") else "unknown"
        self.output_dir = os.path.join("outputs", spider_name)
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info(f"TextFilePipeline: writing to directory {self.output_dir}")

    def close_spider(self, spider):
        logger.info(f"TextFilePipeline: finished writing for {spider.name}")

    def process_item(self, item, spider):
        doc_id = item.get("id", "unknown_id")
        
        # Create a specific folder for this document
        doc_dir = os.path.join(self.output_dir, doc_id)
        os.makedirs(doc_dir, exist_ok=True)
        
        # Write metadata to JSON
        json_path = os.path.join(doc_dir, "data.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(dict(item), f, ensure_ascii=False, default=str, indent=2)
            
        # Write content to Markdown file
        md_path = os.path.join(doc_dir, "content.md")
        with open(md_path, "w", encoding="utf-8") as f:
            title = item.get("title", "No Title")
            body = item.get("body", "")
            f.write(f"# {title}\n\n{body}")
            
        logger.info(f"Saved item to {doc_dir}")
        return item
