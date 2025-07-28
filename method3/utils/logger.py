import logging
from config.settings import get_logging_config

def setup_logging() -> None:
    """Setup logging configuration for vision processing."""
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

def log_processing_start(folder_path: str, output_file: str, prompt_file: str) -> None:
    """Log processing start information."""
    logger = get_logger(__name__)
    logger.info("=" * 60)
    logger.info("Vision Processing Started")
    logger.info(f"Image folder: {folder_path}")
    logger.info(f"Prompt file: {prompt_file}")
    logger.info(f"Output file: {output_file}")
    logger.info("=" * 60)

def log_processing_summary(results: dict) -> None:
    """Log processing summary."""
    logger = get_logger(__name__)
    
    logger.info("=" * 60)
    logger.info("PROCESSING SUMMARY:")
    
    if results.get("success"):
        logger.info(f"Status: SUCCESS")
        logger.info(f"Images processed: {results.get('image_count', 0)}")
        logger.info(f"Folder: {results.get('folder_path', 'N/A')}")
        
        # Log summary stats if available
        summary = results.get("summary", {})
        if summary:
            logger.info(f"Total images found: {summary.get('total_images_found', 0)}")
            logger.info(f"Successfully processed: {summary.get('successfully_processed', 0)}")
            logger.info(f"Failed to process: {summary.get('failed_to_process', 0)}")
            logger.info(f"Success rate: {summary.get('success_rate', 0):.1f}%")
    else:
        logger.info(f"Status: FAILED")
        logger.info(f"Error: {results.get('error', 'Unknown error')}")
        logger.info(f"Folder: {results.get('folder_path', 'N/A')}")
    
    logger.info("=" * 60)

def log_image_stats(image_stats: dict) -> None:
    """Log image statistics."""
    logger = get_logger(__name__)
    
    if "error" in image_stats:
        logger.error(f"Failed to get image stats: {image_stats['error']}")
        return
    
    logger.info("Image Statistics:")
    logger.info(f"  Total files: {image_stats.get('total_files', 0)}")
    logger.info(f"  Total size: {image_stats.get('total_size_bytes', 0):,} bytes")
    
    breakdown = image_stats.get('file_breakdown', {})
    if breakdown:
        logger.info("  File types:")
        for ext, count in breakdown.items():
            logger.info(f"    {ext}: {count} files")

def log_api_request_info(image_count: int, prompt_length: int) -> None:
    """Log API request information."""
    logger = get_logger(__name__)
    logger.info(f"Preparing API request:")
    logger.info(f"  Images to process: {image_count}")
    logger.info(f"  Prompt length: {prompt_length} characters")

def log_processing_result_preview(results: dict) -> None:
    """Log a preview of processing results."""
    logger = get_logger(__name__)
    
    if not results.get("success"):
        logger.warning("Processing failed, no results to preview")
        return
    
    data = results.get("data")
    if not data:
        logger.warning("No data in results")
        return
    
    print("\n" + "=" * 50)
    print("PROCESSING RESULTS PREVIEW:")
    print("=" * 50)
    
    # Show raw response if it exists
    if isinstance(data, dict) and "raw_response" in data:
        response = data["raw_response"]
        preview_length = min(500, len(response))
        print(f"Raw Response (first {preview_length} chars):")
        print(response[:preview_length])
        if len(response) > preview_length:
            print("... (truncated)")
    
    # Show structured data if it exists
    elif isinstance(data, dict) and "raw_response" not in data:
        print("Structured Data:")
        import json
        try:
            preview = json.dumps(data, indent=2)[:1000]
            print(preview)
            if len(json.dumps(data)) > 1000:
                print("... (truncated)")
        except Exception as e:
            print(f"Could not format data for preview: {e}")
    
    print("=" * 50)

def log_error_details(error: Exception, context: str = "") -> None:
    """Log detailed error information."""
    logger = get_logger(__name__)
    
    if context:
        logger.error(f"Error in {context}: {str(error)}")
    else:
        logger.error(f"Error: {str(error)}")
    
    # Log stack trace for debugging
    logger.debug("Error details:", exc_info=True)