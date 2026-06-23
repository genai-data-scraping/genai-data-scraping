#!/usr/bin/env python3


import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv()

from utils.logger import (
    setup_logging,
    get_logger,
    log_processing_start,
    log_processing_summary,
    log_sample_results,
)
from utils.cli import parse_arguments
from services.file_service import (
    load_prompt_from_file,
    save_results_to_json,
    validate_directory,
    create_output_directory,
)
from services.processing_service import process_files_batch


def main():

    setup_logging()
    logger = get_logger(__name__)

    try:
        args = parse_arguments()

        log_processing_start(
            args.directory,
            args.num_files,
            args.max_workers,
            args.output,
        )

        validate_directory(args.directory)
        create_output_directory(args.output)

        prompt = load_prompt_from_file(args.prompt_file)

        results = process_files_batch(
            directory=args.directory,
            num_files=args.num_files,
            prompt=prompt,
            max_workers=args.max_workers,
        )

        save_results_to_json(results, args.output)

        log_processing_summary(results)
        log_sample_results(results)

        logger.info("Processing completed successfully")

    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        sys.exit(1)
    except FileNotFoundError as e:
        logger.error(f"Required file not found: {e}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Invalid argument: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Script failed with error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
