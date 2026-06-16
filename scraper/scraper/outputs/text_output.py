import json
import os
import asyncio
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

    def _write_doc(self, doc_dict, doc_dir):
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

    async def _index_batch(self, documents: List[ScrapedDocument]):
        for doc in documents:
            doc_dict = doc.model_dump(exclude_none=True)
            doc_id = doc_dict.get("id", "unknown_id")
            doc_dir = os.path.join(self.output_dir, doc_id)
            await asyncio.to_thread(self._write_doc, doc_dict, doc_dir)
            logger.debug(f"TextOutput: saved doc to {doc_dir}")

    async def get_last_successful_run(self, source: str) -> Optional[ScraperRunDocument]:
        runs_file = os.path.join(self.output_dir, "runs.json")
        if not os.path.exists(runs_file):
            return None
        try:
            with open(runs_file, "r") as f:
                data = json.load(f)
                run_data = data.get(source)
                if run_data:
                    return ScraperRunDocument(**run_data)
        except Exception as e:
            logger.warning(f"Failed to read runs.json: {e}")
        return None

    async def record_run(self, run_document: ScraperRunDocument) -> None:
        runs_file = os.path.join(self.output_dir, "runs.json")
        data = {}
        if os.path.exists(runs_file):
            try:
                with open(runs_file, "r") as f:
                    data = json.load(f)
            except Exception:
                pass
        
        data[run_document.source] = run_document.model_dump(exclude_none=True)
        
        def _write():
            with open(runs_file, "w", encoding="utf-8") as f:
                json.dump(data, f, default=str, indent=2)
                
        await asyncio.to_thread(_write)
