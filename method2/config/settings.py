import os

# API Settings
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL_NAME = "openai/gpt-4o-mini"
API_TIMEOUT = 60
API_TEMPERATURE = 0.1
API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Processing Settings
MIN_CONTENT_SCORE = 0.3
DEFAULT_MAX_WORKERS = 10
DEFAULT_OUTPUT_FILE = "results.json"
DEFAULT_PROMPT_FILE = "prompt.txt"

# Content Preservation
PRESERVE_CLASSES = {
    'product', 'item', 'listing', 'content', 'price', 'reviews', 'title', 'description', 
    'a-section', 'a-spacing-base', 'a-text-bold', 'job-details', 'profile-overview',
    'listing-details', 'specs-section'
}

PRESERVE_IDS = {
    'main', 'products', 'results', 'productTitle', 'priceblock_ourprice', 
    'featurebullets_feature_div', 'productDescription', 'customerReviews', 
    'detailBullets_feature_div', 'buybox', 'main-content', 'job-post-content',
    'vehicle-overview', 'details-pane'
}

# HTML Cleaning
UNWANTED_TAGS = ['script', 'style', 'noscript', 'iframe', 'svg', 'form', 'link']
PRESERVED_ATTRS = {'href', 'src', 'alt', 'title', 'datetime', 'cite'}

# Content Scoring Weights
SCORING_WEIGHTS = {
    'text_length': 0.3,
    'paragraph_density': 0.25,
    'link_ratio': 0.2,
    'semantic_content': 0.15,
    'list_quality': 0.1
}

# Boilerplate Detection
HIGH_CONFIDENCE_BOILERPLATE_PATTERNS = {
    'advertisement', 'cookie-banner', 'popup-modal', 'social-share',
    'newsletter-signup', 'gdpr', 'privacy-banner', 'sticky-nav',
    'share-buttons', 'related-posts', 'comment-section'
}