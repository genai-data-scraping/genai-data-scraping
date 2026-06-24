import os
from urllib.parse import urlparse


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL_NAME = "meta-llama/llama-3.1-8b-instruct"
API_TIMEOUT = 120
API_TEMPERATURE = 0.1
API_URL = "https://openrouter.ai/api/v1/chat/completions"

OPENROUTER_REFERER = "https://github.com/genai-data-scraping"
OPENROUTER_METHOD = "html"


def site_name_from_url(url: str) -> str:
    host = urlparse(url).netloc.replace("www.", "")
    return ".".join(host.split(".")[-2:]) or host or "unknown"


def openrouter_app_title(url: str = "", site: str = "") -> str:
    name = site or (site_name_from_url(url) if url else "unknown")
    return f"{OPENROUTER_METHOD} - {name}"


MIN_CONTENT_SCORE = 0.3
DEFAULT_MAX_WORKERS = 10
DEFAULT_OUTPUT_FILE = "results.json"
DEFAULT_PROMPT_FILE = "prompt.txt"


MAX_CONTENT_CHARS = 80000
MAX_OUTPUT_TOKENS = 8192

REUTERS_MAX_CONTENT_CHARS = 80000
REUTERS_MIN_CONTENT_SCORE = 0.2


PRESERVE_CLASSES = {
    'product', 'item', 'listing', 'content', 'price', 'reviews', 'title', 'description',
    'a-section', 'a-spacing-base', 'a-text-bold', 'job-details', 'profile-overview',
    'listing-details', 'specs-section',


    'dock-item', 'dock-module', 'ticker-item-wrapper',
}

PRESERVE_IDS = {
    'main', 'products', 'results', 'productTitle', 'priceblock_ourprice',
    'featurebullets_feature_div', 'productDescription', 'customerReviews',
    'detailBullets_feature_div', 'buybox', 'main-content', 'job-post-content',
    'vehicle-overview', 'details-pane',
    'quote-title', 'quote-price', 'quote-statistics',
}


UNWANTED_TAGS = ['script', 'style', 'noscript', 'iframe', 'svg', 'form', 'link']
PRESERVED_ATTRS = {'href', 'src', 'alt', 'title', 'datetime', 'cite'}


SCORING_WEIGHTS = {
    'text_length': 0.3,
    'paragraph_density': 0.25,
    'link_ratio': 0.2,
    'semantic_content': 0.15,
    'list_quality': 0.1
}


HIGH_CONFIDENCE_BOILERPLATE_PATTERNS = {
    'advertisement', 'cookie-banner', 'popup-modal', 'social-share',
    'newsletter-signup', 'gdpr', 'privacy-banner', 'sticky-nav',
    'share-buttons', 'related-posts', 'comment-section'
}
