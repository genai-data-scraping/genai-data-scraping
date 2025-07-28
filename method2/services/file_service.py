import threading
from models.schemas import create_file_result_from_path
from utils.file_utils import extract_url_from_html
from cleaners.html_cleaner import clean_html_for_llm
from services.llm_service import extract_with_llm
from config.logging_config import get_logger

logger = get_logger(__name__)


def process_single_file(file_path, prompt, preserve_classes, preserve_ids):
    """Process a single HTML file."""
    file_result = create_file_result_from_path(file_path)
    
    try:
        logger.info(f"[Thread {threading.current_thread().ident}] Processing file: {file_path}")
        
        # Extract URL
        file_result['url'] = extract_url_from_html(file_path)
        
        # Clean HTML
        cleaned_content = clean_html_for_llm(
            filename=file_path,
            preserve_classes=preserve_classes,
            preserve_ids=preserve_ids
        )
        
        # Process with LLM
        llm_response = extract_with_llm(cleaned_content, prompt)
        
        file_result['llm_response'] = llm_response
        file_result['status'] = "success"
        
        logger.info(f"[Thread {threading.current_thread().ident}] Successfully processed: {file_path}")
        
    except Exception as e:
        file_result['error'] = str(e)
        logger.error(f"[Thread {threading.current_thread().ident}] Failed to process {file_path}: {e}")
    
    return file_result