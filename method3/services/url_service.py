import re
import random
from pathlib import Path
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

def extract_url_from_html(file_path: str) -> str:

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

def get_html_files_from_directory(directory: str, num_files: int = None) -> List[str]:

    dir_path = Path(directory)

    if not dir_path.exists():
        raise FileNotFoundError(f"Directory {directory} not found")


    html_files = list(dir_path.glob("*.html"))

    if not html_files:
        raise FileNotFoundError(f"No HTML files found in {directory}")

    if num_files is None:
        return [str(f) for f in html_files]

    if len(html_files) < num_files:
        logger.warning(f"Only {len(html_files)} HTML files found, but {num_files} requested")
        num_files = len(html_files)


    selected_files = random.sample(html_files, num_files)
    return [str(f) for f in selected_files]

def extract_urls_from_data_directory(data_dir: str = "../sample_data", num_files_per_site: int = 5) -> List[Dict[str, str]]:

    data_path = Path(data_dir)

    if not data_path.exists():
        raise FileNotFoundError(f"Directory {data_dir} not found")

    url_list = []


    html_files = list(data_path.glob("*.html"))

    if html_files:

        site_name = data_path.name
        logger.info(f"Processing single site directory: {site_name}")


        selected_files = get_html_files_from_directory(str(data_path), num_files_per_site)

        for html_file in selected_files:
            url = extract_url_from_html(html_file)
            url_list.append({
                'url': url,
                'source_file': html_file,
                'site': site_name
            })
            logger.info(f"Extracted URL from {site_name}: {url}")

    else:

        logger.info("Processing multi-site directory structure")

        for site_dir in data_path.iterdir():
            if site_dir.is_dir() and not site_dir.name.startswith('.'):
                logger.info(f"Processing site directory: {site_dir.name}")

                try:
                    html_files = get_html_files_from_directory(str(site_dir), num_files_per_site)

                    for html_file in html_files:
                        url = extract_url_from_html(html_file)
                        if url:
                            url_list.append({
                                'url': url,
                                'source_file': html_file,
                                'site': site_dir.name
                            })
                            logger.info(f"Extracted URL from {site_dir.name}: {url}")
                        else:
                            logger.warning(f"No URL found in {html_file}")

                except Exception as e:
                    logger.error(f"Error processing {site_dir.name}: {e}")
                    continue

    logger.info(f"Total URLs extracted: {len(url_list)}")
    return url_list

def validate_url(url: str) -> bool:

    url_pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None
