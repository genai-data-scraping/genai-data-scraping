import logging
from config.settings import get_logging_config

def setup_logging() -> None:
    """Setup logging configuration."""
    config = get_logging_config()
    
    logging.basicConfig(
        level=getattr(logging, config["log_level"]),
        format=config["log_format"],
        handlers=[
            logging.FileHandler(config["log_file"]),
            logging.StreamHandler()
        ]
    )

def get_logger(name: str) -> logging.Logger:
    """Get logger instance with specified name."""
    return logging.getLogger(name)

def log_processing_start(directory: str, num_files: int, max_workers: int, output_file: str) -> None:
    """Log processing start information."""
    logger = get_logger(__name__)
    logger.info("=" * 60)
    logger.info("Web Search Batch Processing Started")
    logger.info(f"Directory: {directory}")
    logger.info(f"Number of files: {num_files}")
    logger.info(f"Max workers: {max_workers}")
    logger.info(f"Output file: {output_file}")
    logger.info("=" * 60)

def log_processing_summary(results: dict) -> None:
    """Log processing summary."""
    logger = get_logger(__name__)
    summary = results["summary"]
    
    logger.info("=" * 60)
    logger.info("PROCESSING SUMMARY:")
    logger.info(f"Total requested: {summary['total_requested']}")
    logger.info(f"Total processed: {summary['total_processed']}")
    logger.info(f"Successful: {summary['successful']}")
    logger.info(f"Failed: {summary['failed']}")
    
    if summary['total_processed'] > 0:
        success_rate = (summary['successful'] / summary['total_processed'] * 100)
        logger.info(f"Success rate: {success_rate:.1f}%")
    else:
        logger.info("Success rate: N/A")
    
    logger.info(f"Max workers used: {summary['max_workers']}")
    logger.info("=" * 60)

def log_sample_results(results: dict) -> None:
    """Log sample results to console."""
    logger = get_logger(__name__)
    
    if not results["processed_files"]:
        return
    
    print("\nSample Results:")
    for i, file_result in enumerate(results["processed_files"][:2]):  # Show first 2
        print(f"\nFile {i+1}: {file_result['filename']}")
        print(f"URL: {file_result['url']}")
        print(f"Status: {file_result['status']}")
        print(f"Thread ID: {file_result.get('thread_id', 'N/A')}")
        
        if file_result['llm_response']:
            response_preview = file_result['llm_response'][:200]
            print(f"LLM Response (first 200 chars): {response_preview}...")
        elif file_result['error']:
            print(f"Error: {file_result['error']}")