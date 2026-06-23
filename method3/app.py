#!/usr/bin/env python3


import sys
import logging
from pathlib import Path


project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv


load_dotenv()

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

    if verbose:

        logging.getLogger().setLevel(logging.DEBUG)
        logger = get_logger(__name__)
        logger.info("Verbose logging enabled")

def handle_directory_processing(args) -> bool:


    logger = get_logger(__name__)

    try:
        logger.info(f"Processing HTML files from directory: {args.directory}")


        prompt = ""
        if not args.screenshots_only:
            prompt = load_prompt_from_file(args.prompt_file)


        dir_path = Path(args.directory)
        html_files = list(dir_path.glob("*.html"))

        if html_files:

            logger.info(f"Processing single site directory: {dir_path.name}")
            results = run_data_scraping_pipeline(
                data_dir=args.directory,
                screenshot_dir=args.screenshot_dir,
                prompt=prompt,
                num_files_per_site=args.num_files,
                headless=not args.no_headless,
                disable_javascript=True
            )
        else:

            logger.info("Processing multiple site directories")
            results = run_data_scraping_pipeline(
                data_dir=args.directory,
                screenshot_dir=args.screenshot_dir,
                prompt=prompt,
                num_files_per_site=args.num_files,
                headless=not args.no_headless,
                disable_javascript=True
            )


        if results["success"]:
            if args.screenshots_only:
                logger.info(f"Screenshots generated successfully: {results['screenshots_captured']} images")
                logger.info(f"Screenshots saved to: {results['screenshot_directory']}")


                print_folder_stats(results['screenshot_directory'])
                return True
            else:
                logger.info("Full pipeline completed successfully")


                if args.backup:
                    create_backup_if_exists(args.output)

                save_results_to_json(results["vision_processing"], args.output)


                log_processing_summary(results["vision_processing"])


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


    logger = get_logger(__name__)

    try:

        log_processing_start(args.folder, args.output, args.prompt_file)


        image_stats = get_image_stats(args.folder)
        log_image_stats(image_stats)


        logger.info("Validating processing inputs...")
        prompt = load_prompt_from_file(args.prompt_file)
        validate_processing_inputs(args.folder, prompt)


        validate_output_path(args.output)
        if args.backup:
            create_backup_if_exists(args.output)

        logger.info("Starting image processing...")


        results = process_images_from_folder(args.folder, prompt)


        logger.info("Saving results to JSON...")
        save_results_to_json(results, args.output)


        log_processing_summary(results)


        if args.preview:
            log_processing_result_preview(results)


        return results.get("success", False)

    except Exception as e:
        logger.error(f"Error in folder processing: {e}")
        log_error_details(e, "Folder processing error")
        return False

def main():


    setup_logging()
    logger = get_logger(__name__)

    try:

        args = parse_arguments()


        setup_verbose_logging(args.verbose)


        if args.stats_only:
            if args.directory:
                print_directory_stats(args.directory)
            else:
                print_folder_stats(args.folder)
            return


        success = False

        if args.directory:

            success = handle_directory_processing(args)
        else:

            success = handle_folder_processing(args)


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
