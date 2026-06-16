#!/usr/bin/env python3
"""
Simple entrypoint to run scrapers with text file output.
Usage: python run_scraper.py [source_name]
"""
import sys
import asyncio
from loguru import logger
import os

log_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs", "server_dev.log"))
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
logger.remove()
logger.add(log_file_path, level="DEBUG", rotation="10 MB", retention="7 days")

async def main():
    from scraper.config import settings
    from scraper.scraper_factory import ScraperFactory

    source_name = sys.argv[1] if len(sys.argv) > 1 else None
    sources = settings.load_sources()
    all_sources = [src for sl in sources.values() for src in sl]

    if source_name:
        targets = [s for s in all_sources if s.name.lower() == source_name.lower()]
        if not targets:
            logger.error(f"Source '{source_name}' not found")
            sys.exit(1)
    else:
        targets = all_sources

    for src in targets:
        logger.info(f"Starting scrape: {src.name}")
        try:
            scraper = ScraperFactory.create_scraper(src, "text")
            await scraper.run()
        except Exception as e:
            logger.exception(f"Error scraping {src.name}: {e}")
        logger.info(f"Finished scrape: {src.name}")

if __name__ == "__main__":
    asyncio.run(main())
