from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from models.schemas import create_batch_summary, create_file_result_from_path
from services.file_service import process_single_file
from utils.file_utils import get_random_html_files
from config.settings import PRESERVE_CLASSES, PRESERVE_IDS
from config.logging_config import get_logger

logger = get_logger(__name__)


def process_files_batch(directory, num_files, prompt, max_workers=10):
    """Process multiple HTML files in parallel and return results."""
    
    # Get random HTML files
    selected_files = get_random_html_files(directory, num_files)
    
    # Initialize results structure
    summary = create_batch_summary(
        total_requested=num_files,
        directory=directory,
        max_workers=max_workers
    )
    
    processed_files = []
    
    logger.info(f"Starting parallel processing with {max_workers} workers")
    
    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks to the executor
        future_to_file = {
            executor.submit(
                process_single_file, 
                file_path, 
                prompt, 
                PRESERVE_CLASSES, 
                PRESERVE_IDS
            ): file_path
            for file_path in selected_files
        }
        
        # Process completed tasks as they finish
        for future in as_completed(future_to_file):
            file_path = future_to_file[future]
            try:
                file_result = future.result()
                
                if file_result['status'] == "success":
                    summary['successful'] += 1
                else:
                    summary['failed'] += 1
                
                processed_files.append(file_result)
                summary['total_processed'] += 1
                
                logger.info(f"Completed processing: {file_path} (Status: {file_result['status']})")
                
            except Exception as exc:
                logger.error(f"Task generated an exception for {file_path}: {exc}")
                
                error_result = create_file_result_from_path(file_path)
                error_result.update({
                    'status': 'failed',
                    'error': f"Task exception: {str(exc)}"
                })
                
                processed_files.append(error_result)
                summary['failed'] += 1
                summary['total_processed'] += 1
    
    logger.info(f"Parallel processing completed. Processed {summary['total_processed']} files")
    
    # Return as dictionary for JSON serialization
    return {
        "processed_files": processed_files,
        "summary": summary
    }
