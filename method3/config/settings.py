import os

# API Configuration
API_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
API_MODEL = "mistralai/mistral-small-3.2-24b-instruct"
API_TIMEOUT = 120

# Image Processing Configuration
SUPPORTED_IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
DEFAULT_IMAGE_FORMAT = "image/jpeg"
DEFAULT_FOLDER_PATH = "scraped_photos"
DEFAULT_PROMPT_FILE = "prompt.txt"
DEFAULT_OUTPUT_FILE = "vision_results.json"

# Screenshot Generation Configuration
DEFAULT_DATA_DIR = "../sample_data"
DEFAULT_NUM_FILES_PER_SITE = 5
SCREENSHOT_WINDOW_WIDTH = 1920
SCREENSHOT_WINDOW_HEIGHT = 1080
SCREENSHOT_WAIT_TIME = 5
SCREENSHOT_PAGE_LOAD_TIMEOUT = 30
DEFAULT_HEADLESS_MODE = True

# Logging Configuration
LOG_FILE = "vision_processing.log"
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
        "timeout": API_TIMEOUT,
        "api_key": get_api_key()
    }

def get_image_config():
    """Return image processing configuration as dictionary."""
    return {
        "supported_extensions": SUPPORTED_IMAGE_EXTENSIONS,
        "default_format": DEFAULT_IMAGE_FORMAT,
        "default_folder": DEFAULT_FOLDER_PATH
    }

def get_processing_config():
    """Return processing configuration as dictionary."""
    return {
        "prompt_file": DEFAULT_PROMPT_FILE,
        "output_file": DEFAULT_OUTPUT_FILE,
        "folder_path": DEFAULT_FOLDER_PATH
    }

def get_screenshot_config():
    """Return screenshot generation configuration as dictionary."""
    return {
        "data_dir": DEFAULT_DATA_DIR,
        "num_files_per_site": DEFAULT_NUM_FILES_PER_SITE,
        "window_width": SCREENSHOT_WINDOW_WIDTH,
        "window_height": SCREENSHOT_WINDOW_HEIGHT,
        "wait_time": SCREENSHOT_WAIT_TIME,
        "page_load_timeout": SCREENSHOT_PAGE_LOAD_TIMEOUT,
        "headless": DEFAULT_HEADLESS_MODE
    }

def get_logging_config():
    """Return logging configuration as dictionary."""
    return {
        "log_file": LOG_FILE,
        "log_level": LOG_LEVEL,
        "log_format": LOG_FORMAT
    }