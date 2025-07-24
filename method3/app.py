#!/usr/bin/env python3
"""
Vision Processing Application

A modular application for processing images using vision API to extract 
structured data from screenshots and images.
"""

import sys
import logging
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import get_logging_config
from utils.logger import (
    setup_logging,
    get_logger,
    log_processing_start,
    log_processing_summary,
    log_image_stats,
    log_processing_result_preview,
    log_error_details
)
from utils.cli import parse_arguments, print_folder_stats
from services.file_service import (
    load_prompt_from_file,
    save_results_to_json,
    validate_output_path,
    create_backup_if_exists
)
from services.processing_service import process_images_from_folder, validate_processing_inputs
from services.image_service import get_image_stats

def setup_verbose_logging(verbose: bool) -> None:
    """Setup logging with verbose mode if requested."""
    if verbose:
        # Override log level for verbose mode
        logging.getLogger().setLevel(logging.DEBUG)
        logger = get_logger(__name__)
        logger.info("Verbose logging enabled")

def main():
    """Main execution function."""
    # Setup logging first
    setup_logging()
    logger = get_logger(__name__)
    
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Setup verbose logging if requested
        setup_verbose_logging(args.verbose)
        
        # Handle stats-only mode
        if args.stats_only:
            print_folder_stats(args.folder)
            return
        
        # Log processing start
        log_processing_start(args.folder, args.output, args.prompt_file)
        
        # Get and log image statistics
        image_stats = get_image_stats(args.folder)
        log_image_stats(image_stats)
        
        # Validate processing inputs
        logger.info("Validating processing inputs...")
        prompt = load_prompt_from_file(args.prompt_file)
        validate_processing_inputs(args.folder, prompt)
        
        # Validate output path and create backup if requested
        validate_output_path(args.output)
        if args.backup:
            create_backup_if_exists(args.output)
        
        logger.info("Starting image processing...")
        
        # Process images
        results = process_images_from_folder(args.folder, prompt)
        
        # Save results
        logger.info("Saving results to JSON...")
        save_results_to_json(results, args.output)
        
        # Log summary
        log_processing_summary(results)
        
        # Show preview if requested
        if args.preview:
            log_processing_result_preview(results)
        
        # Determine exit code based on success
        if results.get("success"):
            logger.info("Processing completed successfully")
            sys.exit(0)
        else:
            logger.error("Processing failed")
            sys.exit(1)
        
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        sys.exit(1)
    
    except FileNotFoundError as e:
        log_error_details(e, "File not found")
        logger.error(f"Required file not found: {e}")
        sys.exit(1)
    
    except ValueError as e:
        log_error_details(e, "Invalid input")
        logger.error(f"Invalid input: {e}")
        sys.exit(1)
    
    except Exception as e:
        log_error_details(e, "Unexpected error")
        logger.error(f"Script failed with unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()