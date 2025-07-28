"""Main application entry point."""

import argparse
import json
from config.logging_config import setup_logging, get_logger
from services.processor_service import process_files_batch
from utils.file_utils import read_file
from config.settings import (
    DEFAULT_MAX_WORKERS, 
    DEFAULT_OUTPUT_FILE, 
    DEFAULT_PROMPT_FILE
)

logger = setup_logging()


def create_argument_parser():
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description='Clean HTML files and process with LLM (with parallel processing)'
    )
    parser.add_argument('--directory', '-d', type=str, required=True,
                       help='Directory containing HTML files (e.g., amazon.com_cleaned)')
    parser.add_argument('--num-files', '-n', type=int, required=True,
                       help='Number of random files to process')
    parser.add_argument('--prompt-file', '-p', type=str, default=DEFAULT_PROMPT_FILE,
                       help=f'Path to prompt file (default: {DEFAULT_PROMPT_FILE})')
    parser.add_argument('--output', '-o', type=str, default=DEFAULT_OUTPUT_FILE,
                       help=f'Output JSON file (default: {DEFAULT_OUTPUT_FILE})')
    parser.add_argument('--max-workers', '-w', type=int, default=DEFAULT_MAX_WORKERS,
                       help=f'Maximum number of worker threads (default: {DEFAULT_MAX_WORKERS})')
    
    return parser


def print_summary(results, output_file):
    """Print processing summary to console."""
    summary = results["summary"]
    logger.info("=" * 50)
    logger.info("PROCESSING SUMMARY:")
    logger.info(f"Total requested: {summary['total_requested']}")
    logger.info(f"Total processed: {summary['total_processed']}")
    logger.info(f"Successful: {summary['successful']}")
    logger.info(f"Failed: {summary['failed']}")
    logger.info(f"Max workers used: {summary['max_workers']}")
    logger.info(f"Results saved to: {output_file}")
    logger.info("=" * 50)


def print_sample_results(results):
    """Print sample results to console."""
    if not results["processed_files"]:
        return
        
    print("\nSample Results:")
    for i, file_result in enumerate(results["processed_files"][:2]):  # Show first 2
        print(f"\nFile {i+1}: {file_result['filename']}")
        print(f"URL: {file_result['url']}")
        print(f"Status: {file_result['status']}")
        print(f"Thread ID: {file_result.get('thread_id', 'N/A')}")
        if file_result['llm_response']:
            print(f"LLM Response (first 200 chars): {file_result['llm_response'][:200]}...")


def main():
    """Main application function."""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    logger.info("=" * 50)
    logger.info("HTML Cleaner Batch Processing Started (Parallel)")
    logger.info(f"Directory: {args.directory}")
    logger.info(f"Number of files: {args.num_files}")
    logger.info(f"Max workers: {args.max_workers}")
    logger.info("=" * 50)
    
    try:
        # Read prompt
        prompt = read_file(args.prompt_file).strip()
        
        # Process files in parallel
        results = process_files_batch(
            directory=args.directory,
            num_files=args.num_files,
            prompt=prompt,
            max_workers=args.max_workers
        )
        
        # Save results
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Print summary and samples
        print_summary(results, args.output)
        print_sample_results(results)
        
    except FileNotFoundError as e:
        logger.error(f"Required file not found: {e}")
    except Exception as e:
        logger.error(f"Script failed with error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()