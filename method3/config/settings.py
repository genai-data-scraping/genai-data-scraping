import os
from urllib.parse import urlparse


API_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
API_MODEL = "mistralai/mistral-small-3.2-24b-instruct"
API_TIMEOUT = 120
API_TEMPERATURE = 0.1

OPENROUTER_REFERER = "https://github.com/genai-data-scraping"
OPENROUTER_METHOD = "screenshot"


def site_name_from_url(url: str) -> str:
    host = urlparse(url).netloc.replace("www.", "")
    return ".".join(host.split(".")[-2:]) or host or "unknown"


def site_name_from_group(group_name: str) -> str:

    parts = group_name.split("_")
    if len(parts) >= 2 and parts[1].isdigit():
        return parts[0]
    return parts[0] if parts else "unknown"


def openrouter_app_title(url: str = "", site: str = "", group_name: str = "") -> str:
    if site:
        name = site
    elif url:
        name = site_name_from_url(url)
    elif group_name:
        name = site_name_from_group(group_name)
    else:
        name = "unknown"
    return f"{OPENROUTER_METHOD} - {name}"


SUPPORTED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
DEFAULT_IMAGE_FORMAT = "image/png"
DEFAULT_FOLDER_PATH = "scraped_photos"
DEFAULT_PROMPT_FILE = "prompt.txt"
DEFAULT_OUTPUT_FILE = "vision_results.json"


DEFAULT_DATA_DIR = "../sample_data"
DEFAULT_NUM_FILES_PER_SITE = 5
SCREENSHOT_WINDOW_WIDTH = 1920
SCREENSHOT_WINDOW_HEIGHT = 1080
SCREENSHOT_WAIT_TIME = 3
SCREENSHOT_PAGE_LOAD_TIMEOUT = 15
DEFAULT_HEADLESS_MODE = True


SCREENSHOTS_PER_PAGE = 4
SCREENSHOT_SCROLL_OVERLAP = 270


LOG_FILE = "vision_processing.log"
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

def get_api_key():

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable not set")
    return api_key

def get_api_config():

    return {
        "base_url": API_BASE_URL,
        "model": API_MODEL,
        "timeout": API_TIMEOUT,
        "temperature": API_TEMPERATURE,
        "api_key": get_api_key()
    }

def get_image_config():

    return {
        "supported_extensions": SUPPORTED_IMAGE_EXTENSIONS,
        "default_format": DEFAULT_IMAGE_FORMAT,
        "default_folder": DEFAULT_FOLDER_PATH
    }

def get_processing_config():

    return {
        "prompt_file": DEFAULT_PROMPT_FILE,
        "output_file": DEFAULT_OUTPUT_FILE,
        "folder_path": DEFAULT_FOLDER_PATH
    }

def get_screenshot_config():

    return {
        "data_dir": DEFAULT_DATA_DIR,
        "num_files_per_site": DEFAULT_NUM_FILES_PER_SITE,
        "window_width": SCREENSHOT_WINDOW_WIDTH,
        "window_height": SCREENSHOT_WINDOW_HEIGHT,
        "wait_time": SCREENSHOT_WAIT_TIME,
        "page_load_timeout": SCREENSHOT_PAGE_LOAD_TIMEOUT,
        "headless": DEFAULT_HEADLESS_MODE,
        "screenshots_per_page": SCREENSHOTS_PER_PAGE,
        "scroll_overlap": SCREENSHOT_SCROLL_OVERLAP,
    }

def get_logging_config():

    return {
        "log_file": LOG_FILE,
        "log_level": LOG_LEVEL,
        "log_format": LOG_FORMAT
    }
