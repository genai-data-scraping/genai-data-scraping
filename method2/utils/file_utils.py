import re
import random
from pathlib import Path
from config.logging_config import get_logger

logger = get_logger(__name__)


def extract_url_from_html(file_path):

    try:
        with open(file_path, 'r', encoding='utf-8') as f:

            for _ in range(10):
                line = f.readline()
                if not line:
                    break


                if 'saved from url=' in line:


                    pattern = r'url=\(\d+\)(https?://[^)]+?)(?:\s*-->)'
                    match = re.search(pattern, line)
                    if match:
                        return match.group(1)


                    pattern2 = r'(https?://[^\s>]+?)(?:\s*-->)'
                    match2 = re.search(pattern2, line)
                    if match2:
                        return match2.group(1)

        logger.warning(f"No URL found in {file_path}")
        return ""
    except Exception as e:
        logger.error(f"Error extracting URL from {file_path}: {e}")
        return ""


def get_random_html_files(directory, num_files):

    dir_path = Path(directory)

    if not dir_path.exists():
        raise FileNotFoundError(f"Directory {directory} not found")


    html_files = list(dir_path.glob("*.html"))

    if not html_files:
        raise FileNotFoundError(f"No HTML files found in {directory}")

    if len(html_files) < num_files:
        logger.warning(f"Only {len(html_files)} HTML files found, but {num_files} requested")
        num_files = len(html_files)


    selected_files = random.sample(html_files, num_files)
    return [str(f) for f in selected_files]


def read_file(file_path, encoding='utf-8'):

    try:
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"File {file_path} not found")
        raise
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        raise


def write_file(file_path, content, encoding='utf-8'):

    try:
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)
    except Exception as e:
        logger.error(f"Error writing to file {file_path}: {e}")
        raise
