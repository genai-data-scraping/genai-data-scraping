import threading
import logging
from pathlib import Path
from typing import Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

from models.data_models import (
    create_file_result, 
    create_batch_results, 
    update_batch_summary,
    create_error_result
)
from services.api_service import make_api_request
from services.file_service import get_random_html_files
from utils.url_extractor import extract_url_from_html

logger = logging.getLogger(__name__)

def process_single_file(file_path: str, prompt: str) -> Dict:
    """Process a single HTML file. This function will be called by each worker thread."""
    thread_id = threading.current_thread().ident
    filename = Path(file_path).name
    
    file_result = create_file_result(
        filename=filename,
        full_path=file_path
    )
    
    try:
        logger.info(f"[Thread {thread_id}] Processing file: {file_path}")
        
        # Extract URL from HTML file
        extracted_url = extract_url_from_html(file_path)
        if not extracted_url:
            raise Exception("No URL found in HTML file")
        
        file_result["url"] = extracted_url
        logger.info(f"[Thread {thread_id}] Extracted URL: {extracted_url[:100]}...")
        
        # Process with web search API
        llm_response = make_api_request(extracted_url, prompt)
        
        file_result["llm_response"] = llm_response
        file_result["status"] = "success"
        
        logger.info(f"[Thread {thread_id}] Successfully processed: {file_path}")
        
    except Exception as e:
        file_result["error"] = str(e)
        logger.error(f"[Thread {thread_id}] Failed to process {file_path}: {e}")
    
    return file_result

def process_files_batch(directory: str, num_files: int, prompt: str, max_workers: int = 5) -> Dict:
    """Process multiple HTML files in parallel using web search API and return results as JSON."""
    
    # Get random HTML files
    selected_files = get_random_html_files(directory, num_files)
    
    results = create_batch_results(directory, num_files, max_workers)
    
    logger.info(f"Starting parallel processing with {max_workers} workers")
    logger.info(f"Selected files: {[Path(f).name for f in selected_files]}")
    
    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks to the executor
        future_to_file = {
            executor.submit(process_single_file, file_path, prompt): file_path
            for file_path in selected_files
        }
        
        # Process completed tasks as they finish
        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                file_result = future.result()
                update_batch_summary(results, file_result)
                
                logger.info(f"Completed processing: {Path(file_path).name} (Status: {file_result['status']})")
                
            except Exception as exc:
                # This should rarely happen since we handle exceptions in process_single_file
                logger.error(f"Task generated an exception for {file_path}: {exc}")
                
                error_result = create_error_result(file_path, f"Task exception: {str(exc)}")
                update_batch_summary(results, error_result)
    
    logger.info(f"Parallel processing completed. Processed {results['summary']['total_processed']} files")
    return results