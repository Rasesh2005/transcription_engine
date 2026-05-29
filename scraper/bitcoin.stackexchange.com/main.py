import json
import os
import sys
import time
from datetime import datetime
from loguru import logger
from tqdm import tqdm

from utils import download_dump, extract_dump, parse_posts, parse_users, strip_tags
import traceback

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Removed Elasticsearch imports, using local paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
LOG_FILE = os.path.abspath(os.path.join(BASE_DIR, "..", "logs", "server_dev.log"))

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)

logger.remove()
logger.add(LOG_FILE, level="DEBUG", rotation="10 MB", retention="7 days")

if __name__ == "__main__":
    DOWNLOAD_PATH = os.path.join(DATA_DIR, "bitcoin.stackexchange.com.7z")
    EXTRACT_PATH = os.path.join(DATA_DIR, "bitcoin.stackexchange.com")

    # download archive data
    if not os.path.exists(DOWNLOAD_PATH):
        download_dump(DOWNLOAD_PATH)
    else:
        logger.info(f'File already exists at path: {os.path.abspath(DOWNLOAD_PATH)}')

    # extract the data if necessary
    if not os.path.exists(EXTRACT_PATH):
        os.makedirs(EXTRACT_PATH)
        should_extract = True
    else:
        if not os.listdir(EXTRACT_PATH):
            should_extract = True
        else:
            file_count = len(os.listdir(EXTRACT_PATH))
            logger.info(f'{file_count} files already exist at path: {os.path.abspath(EXTRACT_PATH)}')
            should_extract = False

    if should_extract:
        extract_dump(DOWNLOAD_PATH, EXTRACT_PATH)

    # parse the data
    USERS_FILE_PATH = f"{EXTRACT_PATH}/Users.xml"
    users = parse_users(USERS_FILE_PATH)

    POSTS_FILE_PATH = f"{EXTRACT_PATH}/Posts.xml"
    docs = parse_posts(POSTS_FILE_PATH)

    for post in tqdm(docs):
        try:
            if post.attrib.get("PostTypeId") != "1" and post.attrib.get("PostTypeId") != "2":
                continue

            user = users.get(post.attrib.get("OwnerUserId")) or post.attrib.get("OwnerDisplayName") or "Anonymous"

            # prepare the document based on type: 'question' or 'answer'
            if post.attrib.get("ParentId") is None:
                tags = post.attrib.get("Tags", "")
                if len(tags) > 2:
                    tags = tags[1:-1].split("><")
                else:
                    tags = []
                    
                document = {
                    "title": post.attrib.get("Title"),
                    "body": strip_tags(post.attrib.get("Body", "")),
                    "body_type": "raw",
                    "authors": [user],
                    "id": "stackexchange-" + post.attrib.get("Id"),
                    "tags": tags,
                    "domain": "https://bitcoin.stackexchange.com",
                    "url": "https://bitcoin.stackexchange.com/questions/" + post.attrib.get("Id"),
                    "thread_url": "https://bitcoin.stackexchange.com/questions/" + post.attrib.get("Id"),
                    "created_at": post.attrib.get("CreationDate"),
                    "accepted_answer_id": post.attrib.get("AcceptedAnswerId"),
                    "type": "question",
                    "indexed_at": datetime.utcnow().isoformat()
                }
            else:
                posts = {}
                question = posts.get(post.attrib.get("ParentId"))
                if question is None:
                    question = docs.find("./row[@Id='" + post.attrib.get("ParentId") + "']")
                    if question is not None:
                        posts[post.attrib.get("ParentId")] = question

                title = question.attrib.get("Title") + " (Answer)" if question is not None else "Answer"
                
                document = {
                    "title": title,
                    "body": strip_tags(post.attrib.get("Body", "")),
                    "body_type": "raw",
                    "authors": [user],
                    "id": "stackexchange-" + post.attrib.get("Id"),
                    "domain": "https://bitcoin.stackexchange.com",
                    "url": "https://bitcoin.stackexchange.com/questions/" + post.attrib.get("ParentId") + "#" + post.attrib.get("Id"),
                    "thread_url": "https://bitcoin.stackexchange.com/questions/" + post.attrib.get("ParentId") + "#" + post.attrib.get("Id"),
                    "created_at": post.attrib.get("CreationDate"),
                    "type": "answer",
                    "indexed_at": datetime.utcnow().isoformat()
                }

            # Save to individual files
            doc_id = document.get("id", "unknown_id")
            doc_dir = os.path.join(OUTPUTS_DIR, "bitcoin.stackexchange.com", doc_id)
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

        except Exception as ex:
            logger.error(f"Error occurred: {ex} \n{traceback.format_exc()}")

    logger.info(f"All Documents updated successfully!")
