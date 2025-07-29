import argparse
from pathlib import Path
from config.settings import get_processing_config, get_image_config

def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser for vision processing."""
    parser = argparse.ArgumentParser(
        description='Process images using vision API to extract structured data from screenshots',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate screenshots from HTML files and process with vision API
  python app.py --directory ../sample_data/amazon.com --num-files 5
  python app.py -d ../sample_data/cars.com -n 3 -o results.json
  
  # Generate screenshots only (no vision processing)
  python app.py --directory ../sample_data --num-files 10 --screenshots-only
  
  # Process existing screenshots
  python app.py --folder scraped_photos -o results.json
  
  # Show statistics
  python app.py --directory ../sample_data --stats-only
        """
    )
    
    processing_config = get_processing_config()
    image_config = get_image_config()
    
    # Primary mode: HTML directory processing (similar to method2)
    parser.add_argument(
        '--directory', '-d',
        type=str,
        help='Directory containing HTML files to process (e.g., ../sample_data/amazon.com or ../sample_data for all sites)'
    )
    
    parser.add_argument(
        '--num-files', '-n',
        type=int,
        default=5,
        help='Number of HTML files to process (default: 5, or all files if directory contains mixed sites)'
    )
    
    # Alternative mode: Existing image folder processing
    parser.add_argument(
        '--folder', '-f',
        type=str,
        default=processing_config["folder_path"],
        help=f'Folder containing existing images to process (default: {processing_config["folder_path"]})'
    )
    
    # Common arguments
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
        help='Only show statistics without processing'
    )
    
    # Screenshot generation options
    parser.add_argument(
        '--screenshots-only',
        action='store_true',
        help='Only generate screenshots without vision processing'
    )
    
    parser.add_argument(
        '--screenshot-dir',
        type=str,
        default='scraped_photos',
        help='Directory to save screenshots (default: scraped_photos)'
    )
    
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='Show browser window during screenshot capture (default: headless)'
    )
    
    return parser

def validate_arguments(args) -> None:
    """Validate command line arguments."""
    
    # Determine processing mode
    using_directory = bool(args.directory)
    using_folder = not using_directory
    
    if using_directory:
        # Directory mode: processing HTML files
        data_path = Path(args.directory)
        if not data_path.exists():
            raise FileNotFoundError(f"Directory not found: {args.directory}")
        
        if not data_path.is_dir():
            raise ValueError(f"Path is not a directory: {args.directory}")
        
        # Check for HTML files or subdirectories with HTML files
        html_files = list(data_path.glob("*.html"))
        subdirs_with_html = []
        
        if not html_files:
            # Check subdirectories for HTML files
            for subdir in data_path.iterdir():
                if subdir.is_dir() and not subdir.name.startswith('.'):
                    subdir_html = list(subdir.glob("*.html"))
                    if subdir_html:
                        subdirs_with_html.append(subdir.name)
            
            if not subdirs_with_html:
                raise ValueError(f"No HTML files found in {args.directory} or its subdirectories")
    
    else:
        # Folder mode: processing existing images
        if not args.stats_only:
            folder_path = Path(args.folder)
            if not folder_path.exists():
                raise FileNotFoundError(f"Image folder not found: {args.folder}")
            
            if not folder_path.is_dir():
                raise ValueError(f"Path is not a directory: {args.folder}")
    
    # Validate prompt file (unless only showing stats or only generating screenshots)
    if not (args.stats_only or args.screenshots_only):
        prompt_file = Path(args.prompt_file)
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {args.prompt_file}")
        
        if not prompt_file.is_file():
            raise ValueError(f"Prompt path is not a file: {args.prompt_file}")
    
    # Validate output path parent directory
    if not args.stats_only:
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
        
        # Only validate image folder contents if using folder mode and not stats-only
        if not args.directory and not args.stats_only:
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
    
    print(f"\nProcessing Modes:")
    print(f"  Directory mode: Process HTML files from specified directory")
    print(f"  Folder mode: Process existing screenshots from folder")
    print(f"  JavaScript is always disabled for cleaner screenshots")

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

def print_directory_stats(directory: str) -> None:
    """Print statistics about the HTML directory."""
    from services.url_service import get_html_files_from_directory
    
    dir_path = Path(directory)
    
    if not dir_path.exists():
        print(f"Error: Directory not found: {directory}")
        return
    
    print(f"\nHTML Directory Statistics:")
    print(f"  Directory: {directory}")
    
    # Check if it's a single site directory or contains multiple sites
    html_files = list(dir_path.glob("*.html"))
    
    if html_files:
        # Single site directory
        print(f"  HTML files: {len(html_files)}")
        print(f"  Site: {dir_path.name}")
    else:
        # Multiple site directories
        total_files = 0
        for site_dir in dir_path.iterdir():
            if site_dir.is_dir() and not site_dir.name.startswith('.'):
                try:
                    site_html_files = get_html_files_from_directory(str(site_dir))
                    print(f"  {site_dir.name}: {len(site_html_files)} HTML files")
                    total_files += len(site_html_files)
                except Exception as e:
                    print(f"  {site_dir.name}: Error - {e}")
        
        print(f"  Total HTML files: {total_files}")