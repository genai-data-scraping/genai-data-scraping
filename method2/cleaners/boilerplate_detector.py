from config.settings import HIGH_CONFIDENCE_BOILERPLATE_PATTERNS


def is_likely_boilerplate(tag):
    """Determine if a tag is likely boilerplate content."""
    class_list = tag.get('class', [])
    id_val = tag.get('id', '')
    tag_name = tag.name
    
    class_str = ' '.join(class_list).lower()
    id_str = id_val.lower()
    combined_text = f"{class_str} {id_str} {tag_name}"
    
    # Check high confidence patterns
    for pattern in HIGH_CONFIDENCE_BOILERPLATE_PATTERNS:
        if pattern in combined_text:
            return True, f"High confidence pattern: {pattern}"
    
    # Check for navigation-like structures with high link density
    if tag_name in ['ul', 'ol', 'div']:
        links = tag.find_all('a')
        if links and len(links) > 5:
            text = tag.get_text(strip=True)
            if text:
                link_density = sum(len(link.get_text(strip=True)) for link in links) / len(text)
                if link_density > 0.8:
                    return True, "High link density"
    
    # Check ARIA labels
    aria_label = tag.get('aria-label', '').lower()
    boilerplate_aria_terms = ['navigation', 'menu', 'advertisement', 'banner', 'complementary']
    if any(term in aria_label for term in boilerplate_aria_terms):
        return True, f"ARIA label indicates boilerplate: {aria_label}"
    
    return False, ""


def detect_navigation_elements(tag):
    """Detect if tag is likely a navigation element."""
    nav_indicators = ['nav', 'navigation', 'menu', 'breadcrumb', 'sidebar']
    
    # Check tag attributes
    attrs_text = ' '.join([
        ' '.join(tag.get('class', [])),
        tag.get('id', ''),
        tag.get('role', ''),
        tag.name
    ]).lower()
    
    return any(indicator in attrs_text for indicator in nav_indicators)


def detect_advertisement_content(tag):
    """Detect if tag contains advertisement content."""
    ad_indicators = ['ad', 'advertisement', 'banner', 'sponsor', 'promo']
    
    attrs_text = ' '.join([
        ' '.join(tag.get('class', [])),
        tag.get('id', ''),
        tag.name
    ]).lower()
    
    return any(indicator in attrs_text for indicator in ad_indicators)