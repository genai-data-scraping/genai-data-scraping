from utils.html_utils import (
    parse_html, remove_unwanted_tags, remove_comments, 
    clean_attributes, is_empty_element
)
from utils.text_utils import convert_html_to_markdown, clean_markdown_text
from cleaners.content_analyzer import calculate_content_score
from cleaners.boilerplate_detector import is_likely_boilerplate
from config.settings import MIN_CONTENT_SCORE
from config.logging_config import get_logger

logger = get_logger(__name__)


def clean_html_for_llm(filename, preserve_classes=None, preserve_ids=None, 
                      min_content_score=MIN_CONTENT_SCORE):
    """Clean HTML file for LLM processing."""
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
    
    # Remove unwanted tags and comments
    removed_count = remove_unwanted_tags(soup)
    comment_count = remove_comments(soup)
    
    # Identify elements to remove
    elements_to_remove = []
    
    for tag in soup.find_all(True):
        if tag in elements_to_remove:
            continue
            
        tag_classes = set(tag.get('class', []))
        tag_id = tag.get('id', '')
        
        # Check if element should be preserved
        if tag_classes.intersection(preserve_classes) or tag_id in preserve_ids:
            continue
        
        # Check for boilerplate
        is_boilerplate, reason = is_likely_boilerplate(tag)
        
        if is_boilerplate:
            score, score_details = calculate_content_score(tag)
            if score < min_content_score:
                elements_to_remove.append(tag)
        
        # Check for empty elements
        elif is_empty_element(tag):
            elements_to_remove.append(tag)
    
    # Remove identified elements
    for tag in elements_to_remove:
        if tag.parent:
            tag.decompose()
    
    # Clean attributes
    clean_attributes(soup)
    
    # Convert to markdown
    clean_html = str(soup.body) if soup.body else str(soup)
    markdown_output = convert_html_to_markdown(clean_html)
    
    # Clean up markdown
    final_output = clean_markdown_text(markdown_output)
    
    logger.info(f"HTML cleaning completed for {filename}")
    return final_output