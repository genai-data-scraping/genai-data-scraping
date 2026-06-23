import re
import logging
from config.settings import URL_SEARCH_LINES

logger = logging.getLogger(__name__)

def extract_url_from_html(file_path: str) -> str:

    try:
        with open(file_path, 'r', encoding='utf-8') as f:

            for _ in range(URL_SEARCH_LINES):
                line = f.readline()
                if not line:
                    break


                if 'saved from url=' in line:
                    url = _extract_url_from_line(line)
                    if url:
                        return url

        logger.warning(f"No URL found in {file_path}")
        return ""
    except Exception as e:
        logger.error(f"Error extracting URL from {file_path}: {e}")
        return ""

def _extract_url_from_line(line: str) -> str:


    pattern = r'url=\(\d+\)(https?://[^)\s]+)'
    match = re.search(pattern, line)
    if match:
        url = match.group(1)
        return _clean_url(url)


    pattern2 = r'(https?://[^\s>-]+)'
    match2 = re.search(pattern2, line)
    if match2:
        url = match2.group(1)
        return _clean_url(url)

    return ""

def _clean_url(url: str) -> str:


    return url.rstrip(' ->')

def validate_url(url: str) -> bool:

    if not url:
        return False


    url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return bool(re.match(url_pattern, url))

def extract_domain_from_url(url: str) -> str:

    try:
        pattern = r'https?://(?:www\.)?([^/]+)'
        match = re.search(pattern, url)
        if match:
            return match.group(1)
        return ""
    except Exception as e:
        logger.error(f"Error extracting domain from {url}: {e}")
        return ""
