import re
import html2text


def convert_html_to_markdown(html_content):
    """Convert HTML content to markdown format."""
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.body_width = 0
    h.protect_links = True
    h.unicode_snob = True
    h.single_line_break = True
    
    return h.handle(html_content)


def clean_markdown_text(markdown_content):
    """Clean up markdown content by removing excessive whitespace and empty lines."""
    # Remove excessive newlines
    markdown_content = re.sub(r'\n{4,}', '\n\n\n', markdown_content)
    
    # Clean up lines
    lines = markdown_content.split('\n')
    cleaned_lines = []
    
    for line in lines:
        stripped = line.strip()
        if stripped and not all(c in '*-_=~' for c in stripped):
            cleaned_lines.append(line)
        elif not stripped:
            cleaned_lines.append('')
    
    return '\n'.join(cleaned_lines).strip()


def calculate_text_metrics(text):
    """Calculate various text metrics."""
    return {
        'length': len(text),
        'word_count': len(text.split()) if text else 0,
        'line_count': len(text.split('\n')) if text else 0
    }