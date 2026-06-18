import os
import configparser
import yaml
from dotenv import load_dotenv
from typing import Dict, List, Optional

from scraper.models import SourceConfig


def get_project_root():
    """
    Find the project root by searching for a specific file.

    This function traverses up the directory tree from the current file's location
    until it finds a directory containing 'cli.py', which is assumed to be
    the project root.

    Returns:
        str: The absolute path to the project root directory.

    Raises:
        Exception: If the project root cannot be found.
    """
    # The sources.yaml file is located in the parent directory (scraper/)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


class Settings:
    def __init__(self):
        # Reload environment variables from .env file
        load_dotenv(override=False)

    def load_sources(self) -> Dict[str, List[SourceConfig]]:
        sources_path = os.path.join(get_project_root(), "sources.yaml")
        try:
            with open(sources_path, "r") as file:
                data = yaml.safe_load(file) or {}
        except FileNotFoundError:
            print(f"Warning: {sources_path} not found. Using empty sources.")
            return {}

        sources = {}
        for source_type, source_list in data.items():
            sources[source_type] = [SourceConfig(**source) for source in source_list]

        return sources

    def get_source_config(self, source_name: str) -> Optional[SourceConfig]:
        sources = self.load_sources()
        for source_list in sources.values():
            for src in source_list:
                if src.name.lower() == source_name.lower():
                    return src
        return None

    def get_config_overview(self) -> str:
        overview = ["Configuration Overview:", "-" * 20]
        overview.append(f"Project Root: {get_project_root()}")
        
        sources = self.load_sources()
        total_sources = sum(len(src_list) for src_list in sources.values())
        overview.append(f"Total Sources Configured: {total_sources}")
        
        for source_type, src_list in sources.items():
            overview.append(f"  {source_type.upper()}: {len(src_list)} sources")
            
        return "\n".join(overview)
# Initialize the Settings class and expose an instance
settings = Settings()

__all__ = ["settings"]
