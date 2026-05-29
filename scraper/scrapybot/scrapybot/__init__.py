import sys
from loguru import logger

import os

log_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "logs", "server_dev.log"))
logger.remove()
logger.add(log_file_path, level="DEBUG", rotation="10 MB", retention="7 days")
