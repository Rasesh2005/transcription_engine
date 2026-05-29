import json
import os
from typing import List, Optional

from loguru import logger

from scraper.models import ScrapedDocument, ScraperRunDocument
from scraper.outputs import AbstractOutput
from scraper.registry import output_registry


@output_registry.register("text")
class TextOutput(AbstractOutput):
    def __init__(self, source_name: str = "output", **kwargs):
        kwargs.pop("batch_size", None)
        super().__init__(batch_size=1, **kwargs)
        self.source_name = source_name
        
        # Create output directory if it doesn't exist
        self.output_dir = os.path.join("outputs", source_name)
        os.makedirs(self.output_dir, exist_ok=True)

    async def _initialize(self):
        logger.info(f"TextOutput: writing to directory {self.output_dir}")

    async def _cleanup(self):
        logger.info(f"TextOutput: finished writing for {self.source_name}")

    async def _index_batch(self, documents: List[ScrapedDocument]):
        for doc in documents:
            doc_dict = doc.model_dump(exclude_none=True)
            doc_id = doc_dict.get("id", "unknown_id")
            
            doc_dir = os.path.join(self.output_dir, doc_id)
            os.makedirs(doc_dir, exist_ok=True)
            
            # JSON file
            json_path = os.path.join(doc_dir, "data.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(doc_dict, f, ensure_ascii=False, default=str, indent=2)
                
            # MD file
            md_path = os.path.join(doc_dir, "content.md")
            with open(md_path, "w", encoding="utf-8") as f:
                title = doc_dict.get("title", "No Title")
                body = doc_dict.get("body", "")
                f.write(f"# {title}\n\n{body}")
                
            logger.debug(f"TextOutput: saved doc to {doc_dir}")

    async def get_last_successful_run(self, source: str) -> Optional[ScraperRunDocument]:
        return None

    async def record_run(self, run_document: ScraperRunDocument) -> None:
        pass
