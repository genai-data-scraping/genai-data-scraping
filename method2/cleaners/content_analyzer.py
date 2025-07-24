from models.schemas import create_content_score
from config.settings import SCORING_WEIGHTS


def calculate_content_score(tag):
    """Calculate content quality score for an HTML tag."""
    scores = {}
    
    text = tag.get_text(strip=True)
    text_length = len(text)
    scores['text_length'] = min(text_length / 100, 1.0)
    
    paragraphs = tag.find_all(['p', 'article', 'section'])
    scores['paragraph_density'] = min(len(paragraphs) / 10, 1.0)
    
    links = tag.find_all('a')
    if text_length > 0:
        link_text_length = sum(len(link.get_text(strip=True)) for link in links)
        scores['link_ratio'] = 1.0 - min(link_text_length / text_length, 1.0)
    else:
        scores['link_ratio'] = 0.0
    
    content_tags = tag.find_all(['article', 'main', 'h1', 'h2', 'h3'])
    scores['semantic_content'] = min(len(content_tags) / 5, 1.0)
    
    lists = tag.find_all(['ul', 'ol'])
    list_items = tag.find_all('li')
    if lists:
        avg_items_per_list = len(list_items) / len(lists)
        scores['list_quality'] = 1.0 - min(avg_items_per_list / 20, 1.0)
    else:
        scores['list_quality'] = 0.5
    
    total_score = sum(scores[key] * SCORING_WEIGHTS[key] for key in SCORING_WEIGHTS)
    
    content_score = create_content_score(
        total_score=total_score,
        text_length=scores['text_length'],
        paragraph_density=scores['paragraph_density'],
        link_ratio=scores['link_ratio'],
        semantic_content=scores['semantic_content'],
        list_quality=scores['list_quality']
    )
    
    return total_score, content_score


def analyze_link_density(tag):
    """Analyze link density in a tag."""
    links = tag.find_all('a')
    if not links:
        return 0.0
    
    text = tag.get_text(strip=True)
    if not text:
        return 1.0
    
    link_text_length = sum(len(link.get_text(strip=True)) for link in links)
    return link_text_length / len(text)


def has_semantic_content(tag):
    """Check if tag contains semantic content indicators."""
    semantic_tags = tag.find_all(['article', 'main', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    return len(semantic_tags) > 0