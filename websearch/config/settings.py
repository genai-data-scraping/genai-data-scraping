import os
from urllib.parse import urlparse


API_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
API_MODEL = "openai/gpt-4o-search-preview-2025-03-11"
API_TEMPERATURE = 0.1
API_TIMEOUT = 120

OPENROUTER_REFERER = "https://github.com/genai-data-scraping"
OPENROUTER_METHOD = "websearch"


def site_name_from_url(url: str) -> str:
    host = urlparse(url).netloc.replace("www.", "")
    return ".".join(host.split(".")[-2:]) or host or "unknown"


def openrouter_app_title(url: str = "", site: str = "") -> str:
    name = site or (site_name_from_url(url) if url else "unknown")
    return f"{OPENROUTER_METHOD} - {name}"


DEFAULT_MAX_WORKERS = 5
DEFAULT_PROMPT_FILE = "prompt.txt"
DEFAULT_OUTPUT_FILE = "web_search_results.json"
URL_SEARCH_LINES = 10


LOG_FILE = "web_search_batch.log"
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
        "temperature": API_TEMPERATURE,
        "timeout": API_TIMEOUT,
        "api_key": get_api_key()
    }

def get_processing_config():

    return {
        "max_workers": DEFAULT_MAX_WORKERS,
        "prompt_file": DEFAULT_PROMPT_FILE,
        "output_file": DEFAULT_OUTPUT_FILE,
        "url_search_lines": URL_SEARCH_LINES
    }

def get_logging_config():

    return {
        "log_file": LOG_FILE,
        "log_level": LOG_LEVEL,
        "log_format": LOG_FORMAT
    }
