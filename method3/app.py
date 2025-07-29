#!/usr/bin/env python3
"""
Vision Processing Application

A modular application for processing images using vision API to extract 
structured data from screenshots and images. Supports both HTML file 
screenshot generation and existing image processing.
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
from utils.cli import parse_arguments, print_folder_stats, print_directory_stats
from services.file_service import (
    load_prompt_from_file,
    save_results_to_json,
    validate_output_path,
    create_backup_if_exists
)
from services.processing_service import process_images_from_folder, validate_processing_inputs
from services.image_service import get_image_stats
from services.data_scraping_service import run_data_scraping_pipeline

def setup_verbose_logging(verbose: bool) -> None:
    """Setup logging with verbose mode if requested."""
    if verbose:
        # Override log level for verbose mode
        logging.getLogger().setLevel(logging.DEBUG)
        logger = get_logger(__name__)
        logger.info("Verbose logging enabled")

def handle_directory_processing(args) -> bool:
    """
    Handle processing HTML files from a directory.
    
    Returns:
        bool: True if processing was successful, False otherwise
    """
    logger = get_logger(__name__)
    
    try:
        logger.info(f"Processing HTML files from directory: {args.directory}")
        
        # Load prompt if doing full pipeline
        prompt = ""
        if not args.screenshots_only:
            prompt = load_prompt_from_file(args.prompt_file)
        
        # Determine if processing single site or multiple sites
        dir_path = Path(args.directory)
        html_files = list(dir_path.glob("*.html"))
        
        if html_files:
            # Single site directory - process specified number of files
            logger.info(f"Processing single site directory: {dir_path.name}")
            results = run_data_scraping_pipeline(
                data_dir=args.directory,
                screenshot_dir=args.screenshot_dir,
                prompt=prompt,
                num_files_per_site=args.num_files,
                headless=not args.no_headless,
                disable_javascript=True  # Always disabled
            )
        else:
            # Multiple site directories - process num_files from each site
            logger.info("Processing multiple site directories")
            results = run_data_scraping_pipeline(
                data_dir=args.directory,
                screenshot_dir=args.screenshot_dir,
                prompt=prompt,
                num_files_per_site=args.num_files,
                headless=not args.no_headless,
                disable_javascript=True  # Always disabled
            )
        
        # Handle results
        if results["success"]:
            if args.screenshots_only:
                logger.info(f"Screenshots generated successfully: {results['screenshots_captured']} images")
                logger.info(f"Screenshots saved to: {results['screenshot_directory']}")
                
                # Show screenshot statistics
                print_folder_stats(results['screenshot_directory'])
                return True
            else:
                logger.info("Full pipeline completed successfully")
                
                # Save vision processing results
                if args.backup:
                    create_backup_if_exists(args.output)
                
                save_results_to_json(results["vision_processing"], args.output)
                
                # Log summary
                log_processing_summary(results["vision_processing"])
                
                # Show preview if requested
                if args.preview:
                    log_processing_result_preview(results["vision_processing"])
                
                return True
        else:
            logger.error(f"Processing failed: {results.get('error', 'Unknown error')}")
            logger.error(f"Failed at stage: {results.get('stage', 'Unknown')}")
            return False
            
    except Exception as e:
        logger.error(f"Error in directory processing: {e}")
        log_error_details(e, "Directory processing error")
        return False

def handle_folder_processing(args) -> bool:
    """
    Handle processing existing image files from a folder.
    
    Returns:
        bool: True if processing was successful, False otherwise
    """
    logger = get_logger(__name__)
    
    try:
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
        
        # Determine success
        return results.get("success", False)
        
    except Exception as e:
        logger.error(f"Error in folder processing: {e}")
        log_error_details(e, "Folder processing error")
        return False

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
            if args.directory:
                print_directory_stats(args.directory)
            else:
                print_folder_stats(args.folder)
            return
        
        # Determine processing mode
        success = False
        
        if args.directory:
            # Directory mode: process HTML files
            success = handle_directory_processing(args)
        else:
            # Folder mode: process existing images
            success = handle_folder_processing(args)
        
        # Exit with appropriate code
        if success:
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