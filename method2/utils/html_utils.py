from bs4 import BeautifulSoup, Comment
from config.settings import UNWANTED_TAGS, PRESERVED_ATTRS
from config.logging_config import get_logger

logger = get_logger(__name__)


def parse_html(html_content):
    """Parse HTML content using BeautifulSoup."""
    return BeautifulSoup(html_content, 'html.parser')


def remove_unwanted_tags(soup):
    """Remove unwanted tags from HTML soup."""
    removed_count = 0
    for tag_name in UNWANTED_TAGS:
        tags = soup.find_all(tag_name)
        removed_count += len(tags)
        for tag in tags:
            tag.decompose()
    return removed_count


def remove_comments(soup):
    """Remove HTML comments from soup."""
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    removed_count = len(comments)
    for comment in comments:
        comment.extract()
    return removed_count


def clean_attributes(soup):
    """Clean attributes, keeping only essential ones."""
    for tag in soup.find_all(True):
        if tag.attrs:
            new_attrs = {k: v for k, v in tag.attrs.items() 
                        if k in PRESERVED_ATTRS or k.startswith('data-')}
            tag.attrs = new_attrs


def is_empty_element(tag):
    """Check if an element is empty (no text or media content)."""
    return not tag.get_text(strip=True) and not tag.find_all(['img', 'video', 'audio'])