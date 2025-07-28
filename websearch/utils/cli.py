import argparse
from config.settings import get_processing_config

def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description='Process HTML files with web search API (parallel processing)'
    )
    
    config = get_processing_config()
    
    parser.add_argument(
        '--directory', '-d', 
        type=str, 
        required=True,
        help='Directory containing HTML files (e.g., amazon.com_cleaned)'
    )
    
    parser.add_argument(
        '--num-files', '-n', 
        type=int, 
        required=True,
        help='Number of random files to process'
    )
    
    parser.add_argument(
        '--prompt-file', '-p', 
        type=str, 
        default=config["prompt_file"],
        help=f'Path to prompt file (default: {config["prompt_file"]})'
    )
    
    parser.add_argument(
        '--output', '-o', 
        type=str, 
        default=config["output_file"],
        help=f'Output JSON file (default: {config["output_file"]})'
    )
    
    parser.add_argument(
        '--max-workers', '-w', 
        type=int, 
        default=config["max_workers"],
        help=f'Maximum number of worker threads (default: {config["max_workers"]}, lower for API rate limits)'
    )
    
    return parser

def validate_arguments(args) -> None:
    """Validate command line arguments."""
    if args.num_files <= 0:
        raise ValueError("Number of files must be positive")
    
    if args.max_workers <= 0:
        raise ValueError("Max workers must be positive")
    
    if args.max_workers > 20:
        print("Warning: High worker count may hit API rate limits")

def parse_arguments():
    """Parse and validate command line arguments."""
    parser = create_argument_parser()
    args = parser.parse_args()
    validate_arguments(args)
    return args