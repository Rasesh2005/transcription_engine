import asyncio
import json
import os
import sys
import zipfile
from datetime import datetime

import requests
import yaml
from loguru import logger

# ---------------------------------------------------------------------------
# Paths — everything relative to this file so it works from any CWD
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
LOG_FILE = os.path.abspath(os.path.join(BASE_DIR, "..", "logs", "server_dev.log"))

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)

logger.remove()
logger.add(LOG_FILE, level="DEBUG", rotation="10 MB", retention="7 days")

REPO_URL = "https://github.com/bitcoinops/bitcoinops.github.io/archive/refs/heads/master.zip"
FOLDER_NAME = "raw_data"
DIR_PATH = os.path.join(DATA_DIR, "bitcoinops_dir")
GLOBAL_URL_VARIABLE = os.path.join(DIR_PATH, FOLDER_NAME)
POST_DIR = "bitcoinops.github.io-master/_posts/en"
TOPIC_DIR = "bitcoinops.github.io-master/_topics/en"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_markdown(content: str):
    """Split a Jekyll markdown file into (front_matter, body)."""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[1], parts[2]
    return "", content


async def download_repo():
    os.makedirs(DIR_PATH, exist_ok=True)

    if os.path.exists(GLOBAL_URL_VARIABLE):
        logger.info(f"Repo already downloaded at path: {DIR_PATH}")
        return

    logger.info(f"Downloading repo at path: {DIR_PATH}")
    file_path = os.path.join(DIR_PATH, "raw_data.zip")

    try:
        response = requests.get(REPO_URL, timeout=120)
        response.raise_for_status()

        with open(file_path, "wb") as file:
            file.write(response.content)
        logger.info(f"Downloaded {REPO_URL} to {file_path}")

        with zipfile.ZipFile(file_path, "r") as zip_ref:
            zip_ref.extractall(DIR_PATH)
        logger.info(f"Unzipped {file_path} to {DIR_PATH}")

    except requests.RequestException as e:
        logger.error(f"Failed to download the repo: {e}")
    except zipfile.BadZipFile as e:
        logger.error(f"Failed to unzip the file: {e}")


def parse_post(post_file: str, typeof: str):
    try:
        with open(post_file, "r", encoding="utf-8") as file:
            content = file.read()
        front_matter, body = parse_markdown(content)
        try:
            metadata = yaml.safe_load(front_matter) or {}
        except yaml.YAMLError as e:
            logger.warning(f"YAML parsing error in {post_file}: {e}")
            metadata = {}
        custom_id = (
            os.path.basename(post_file).replace(".md", "")
            if typeof == "topic"
            else metadata.get("slug", os.path.basename(post_file).replace(".md", ""))
        )
        date_val = metadata.get("date")
        if isinstance(date_val, datetime):
            created_at = date_val.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        elif date_val:
            created_at = str(date_val)
        else:
            created_at = None

        document = {
            "id": f"bitcoinops-{custom_id}",
            "title": metadata.get("title", custom_id),
            "body_formatted": body,
            "body": body,
            "body_type": "markdown",
            "created_at": created_at,
            "domain": "https://bitcoinops.org/en/",
            "url": (
                f"https://bitcoinops.org/en/topics/{custom_id}"
                if typeof == "topic"
                else f"https://bitcoinops.org{metadata.get('permalink', '')}"
            ),
            "type": "topic" if typeof == "topic" else metadata.get("type", "newsletter"),
            "language": metadata.get("lang", "en"),
            "authors": ["Bitcoin Optech"],
            "indexed_at": datetime.now().isoformat(),
        }
        return document
    except IOError as e:
        logger.warning(f"Issue while parsing the file, {post_file}: {e}")
        return None


def dir_walk(extracted_dir: str, typeof: str):
    if os.path.exists(extracted_dir):
        documents = []
        for root, dirs, files in os.walk(extracted_dir):
            for post_file in files:
                if not post_file.endswith(".md"):
                    continue
                full_path = os.path.join(root, post_file)
                logger.info(f"Parsing {full_path}")
                document = parse_post(full_path, typeof)
                if document:
                    documents.append(document)
        return documents
    else:
        logger.critical("Data Directory not available.")
        return []


# ---------------------------------------------------------------------------
# Main — writes output line-by-line to a .jsonl file
# ---------------------------------------------------------------------------

async def main():
    await download_repo()
    all_posts = dir_walk(os.path.join(DIR_PATH, POST_DIR), "posts")
    all_topics = dir_walk(os.path.join(DIR_PATH, TOPIC_DIR), "topic")
    all_docs = all_posts + all_topics

    for doc in all_docs:
        doc_id = doc.get("id", "unknown_id")
        doc_dir = os.path.join(OUTPUTS_DIR, "bitcoinops", doc_id)
        os.makedirs(doc_dir, exist_ok=True)
        
        json_path = os.path.join(doc_dir, "data.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, default=str, indent=2)
            
        md_path = os.path.join(doc_dir, "content.md")
        with open(md_path, "w", encoding="utf-8") as f:
            title = doc.get("title", "No Title")
            body = doc.get("body", "")
            f.write(f"# {title}\n\n{body}")
            
        logger.info(f"Saved: {doc_id} — {doc.get('title', '')}")

    logger.info(f"Done. {len(all_docs)} documents written to {OUTPUTS_DIR}/bitcoinops/")


if __name__ == "__main__":
    asyncio.run(main())
