import argparse
from pathlib import Path
from config.settings import get_processing_config, get_image_config

def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser for vision processing."""
    parser = argparse.ArgumentParser(
        description='Process images using vision API to extract structured data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python app.py                                    # Use default settings
  python app.py -f screenshots -o results.json    # Custom folder and output
  python app.py -p custom_prompt.txt -f images/   # Custom prompt and folder
        """
    )
    
    processing_config = get_processing_config()
    image_config = get_image_config()
    
    parser.add_argument(
        '--folder', '-f',
        type=str,
        default=processing_config["folder_path"],
        help=f'Folder containing images to process (default: {processing_config["folder_path"]})'
    )
    
    parser.add_argument(
        '--prompt-file', '-p',
        type=str,
        default=processing_config["prompt_file"],
        help=f'Path to prompt file (default: {processing_config["prompt_file"]})'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=processing_config["output_file"],
        help=f'Output JSON file (default: {processing_config["output_file"]})'
    )
    
    parser.add_argument(
        '--preview', 
        action='store_true',
        help='Show preview of results in console'
    )
    
    parser.add_argument(
        '--backup',
        action='store_true',
        help='Create backup of existing output file'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--stats-only',
        action='store_true',
        help='Only show image folder statistics without processing'
    )
    
    return parser

def validate_arguments(args) -> None:
    """Validate command line arguments."""
    # Validate folder path
    folder_path = Path(args.folder)
    if not folder_path.exists():
        raise FileNotFoundError(f"Image folder not found: {args.folder}")
    
    if not folder_path.is_dir():
        raise ValueError(f"Path is not a directory: {args.folder}")
    
    # Validate prompt file (unless only showing stats)
    if not args.stats_only:
        prompt_file = Path(args.prompt_file)
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {args.prompt_file}")
        
        if not prompt_file.is_file():
            raise ValueError(f"Prompt path is not a file: {args.prompt_file}")
    
    # Validate output path parent directory
    output_path = Path(args.output)
    if not output_path.parent.exists():
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ValueError(f"Cannot create output directory {output_path.parent}: {e}")

def validate_image_folder_contents(folder_path: str) -> None:
    """Validate that folder contains supported image files."""
    image_config = get_image_config()
    folder = Path(folder_path)
    
    # Check for supported image files
    image_files = [
        f for f in folder.iterdir() 
        if f.is_file() and f.suffix.lower() in image_config["supported_extensions"]
    ]
    
    if not image_files:
        supported_exts = ', '.join(image_config["supported_extensions"])
        raise ValueError(
            f"No supported image files found in {folder_path}. "
            f"Supported extensions: {supported_exts}"
        )

def parse_arguments():
    """Parse and validate command line arguments."""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    try:
        validate_arguments(args)
        if not args.stats_only:
            validate_image_folder_contents(args.folder)
    except Exception as e:
        parser.error(str(e))
    
    return args

def show_help_info():
    """Show additional help information."""
    image_config = get_image_config()
    processing_config = get_processing_config()
    
    print("\nSupported Image Formats:")
    for ext in sorted(image_config["supported_extensions"]):
        print(f"  {ext}")
    
    print(f"\nDefault Configuration:")
    print(f"  Image folder: {processing_config['folder_path']}")
    print(f"  Prompt file: {processing_config['prompt_file']}")
    print(f"  Output file: {processing_config['output_file']}")
    
    print(f"\nRequired Environment Variables:")
    print(f"  OPENROUTER_API_KEY - Your OpenRouter API key")

def print_folder_stats(folder_path: str) -> None:
    """Print statistics about the image folder."""
    from services.image_service import get_image_stats
    
    stats = get_image_stats(folder_path)
    
    if "error" in stats:
        print(f"Error getting folder stats: {stats['error']}")
        return
    
    print(f"\nImage Folder Statistics:")
    print(f"  Folder: {folder_path}")
    print(f"  Total files: {stats.get('total_files', 0)}")
    print(f"  Total size: {stats.get('total_size_bytes', 0):,} bytes")
    
    breakdown = stats.get('file_breakdown', {})
    if breakdown:
        print(f"  File types:")
        for ext, count in sorted(breakdown.items()):
            print(f"    {ext}: {count} files")