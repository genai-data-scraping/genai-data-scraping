from utils.html_utils import (
    parse_html, remove_unwanted_tags, remove_comments,
    clean_attributes, is_empty_element
)
from utils.text_utils import convert_html_to_markdown, clean_markdown_text
from utils.file_utils import extract_url_from_html
from cleaners.content_analyzer import calculate_content_score
from cleaners.boilerplate_detector import is_likely_boilerplate
from cleaners.structured_data import extract_structured_data
from config.settings import (
    MIN_CONTENT_SCORE,
    MAX_CONTENT_CHARS,
    REUTERS_MAX_CONTENT_CHARS,
    REUTERS_MIN_CONTENT_SCORE,
)
from config.logging_config import get_logger

logger = get_logger(__name__)


def _is_reuters_source(filename):
    if "reuters" in str(filename).lower():
        return True
    url = extract_url_from_html(filename)
    return "reuters" in (url or "").lower()


def _reuters_tail_tags(soup):
    article = soup.find(attrs={"data-testid": "ArticleBody"})
    if not article:
        return set()
    return set(article.find_all_next(True))


def clean_html_for_llm(filename, preserve_classes=None, preserve_ids=None,
                      min_content_score=MIN_CONTENT_SCORE):

    preserve_classes = preserve_classes or set()
    preserve_ids = preserve_ids or set()

    logger.info(f"Starting HTML cleaning for file: {filename}")

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            html_content = f.read()
        logger.info(f"Successfully read HTML file. Content length: {len(html_content)} characters")
    except Exception as e:
        logger.error(f"Error reading file {filename}: {e}")
        raise

    soup = parse_html(html_content)
    is_reuters = _is_reuters_source(filename)
    reuters_tail = _reuters_tail_tags(soup) if is_reuters else set()
    score_threshold = REUTERS_MIN_CONTENT_SCORE if is_reuters else min_content_score

    structured_data = extract_structured_data(soup)

    remove_unwanted_tags(soup)
    remove_comments(soup)

    elements_to_remove = []

    for tag in soup.find_all(True):
        if tag in elements_to_remove:
            continue

        tag_classes = set(tag.get('class', []))
        tag_id = tag.get('id', '')

        if tag_classes.intersection(preserve_classes) or tag_id in preserve_ids:
            continue

        if is_reuters and tag in reuters_tail:
            continue

        is_boilerplate, _ = is_likely_boilerplate(tag)

        if is_boilerplate:
            score, _ = calculate_content_score(tag)
            if score < score_threshold:
                elements_to_remove.append(tag)
        elif is_empty_element(tag):
            elements_to_remove.append(tag)

    for tag in elements_to_remove:
        if tag.parent:
            tag.decompose()

    clean_attributes(soup)

    clean_html = str(soup.body) if soup.body else str(soup)
    markdown_output = convert_html_to_markdown(clean_html)
    final_output = clean_markdown_text(markdown_output)

    if structured_data:
        final_output = f"{structured_data}\n\n{final_output}"

    max_chars = REUTERS_MAX_CONTENT_CHARS if is_reuters else MAX_CONTENT_CHARS
    if max_chars and len(final_output) > max_chars:
        logger.info(f"Truncating cleaned content from {len(final_output)} "
                    f"to {max_chars} characters")
        final_output = final_output[:max_chars] + "\n\n[content truncated]"

    logger.info(f"HTML cleaning completed for {filename}")
    return final_output
