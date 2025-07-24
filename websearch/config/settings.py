import os

# API Configuration
API_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
API_MODEL = "openai/gpt-4o-search-preview-2025-03-11"
API_TEMPERATURE = 0.1
API_TIMEOUT = 120

# Processing Configuration
DEFAULT_MAX_WORKERS = 5
DEFAULT_PROMPT_FILE = "prompt.txt"
DEFAULT_OUTPUT_FILE = "web_search_results.json"
URL_SEARCH_LINES = 10  # Number of lines to search for URL in HTML

# Logging Configuration
LOG_FILE = "web_search_batch.log"
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

def get_api_key():
    """Get API key from environment variable."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable not set")
    return api_key

def get_api_config():
    """Return API configuration as dictionary."""
    return {
        "base_url": API_BASE_URL,
        "model": API_MODEL,
        "temperature": API_TEMPERATURE,
        "timeout": API_TIMEOUT,
        "api_key": get_api_key()
    }

def get_processing_config():
    """Return processing configuration as dictionary."""
    return {
        "max_workers": DEFAULT_MAX_WORKERS,
        "prompt_file": DEFAULT_PROMPT_FILE,
        "output_file": DEFAULT_OUTPUT_FILE,
        "url_search_lines": URL_SEARCH_LINES
    }

def get_logging_config():
    """Return logging configuration as dictionary."""
    return {
        "log_file": LOG_FILE,
        "log_level": LOG_LEVEL,
        "log_format": LOG_FORMAT
    }