import threading
from pathlib import Path


def create_processing_result(filename, full_path, url="", status="failed", 
                           error=None, llm_response=None, thread_id=None):
    """Create a processing result dictionary."""
    return {
        'filename': filename,
        'full_path': full_path,
        'url': url,
        'status': status,
        'error': error,
        'llm_response': llm_response,
        'thread_id': thread_id
    }


def create_batch_summary(total_requested, total_processed=0, successful=0, 
                        failed=0, directory="", max_workers=0):
    """Create a batch summary dictionary."""
    return {
        'total_requested': total_requested,
        'total_processed': total_processed,
        'successful': successful,
        'failed': failed,
        'directory': directory,
        'max_workers': max_workers
    }


def create_batch_results(processed_files=None, summary=None):
    """Create a batch results dictionary."""
    return {
        'processed_files': processed_files or [],
        'summary': summary or create_batch_summary(0)
    }


def create_content_score(total_score, text_length, paragraph_density, 
                        link_ratio, semantic_content, list_quality):
    """Create a content score dictionary."""
    return {
        'total_score': total_score,
        'text_length': text_length,
        'paragraph_density': paragraph_density,
        'link_ratio': link_ratio,
        'semantic_content': semantic_content,
        'list_quality': list_quality
    }


def create_file_result_from_path(file_path):
    """Create a basic file result from a file path."""
    return create_processing_result(
        filename=Path(file_path).name,
        full_path=file_path,
        thread_id=threading.current_thread().ident
    )