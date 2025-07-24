import json
import random
import logging
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)

def get_random_html_files(directory: str, num_files: int) -> List[str]:
    """Get random HTML files from the specified directory."""
    dir_path = Path(directory)
    
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory {directory} not found")
    
    # Find all HTML files
    html_files = list(dir_path.glob("*.html"))
    
    if not html_files:
        raise FileNotFoundError(f"No HTML files found in {directory}")
    
    if len(html_files) < num_files:
        logger.warning(f"Only {len(html_files)} HTML files found, but {num_files} requested")
        num_files = len(html_files)
    
    # Randomly select files
    selected_files = random.sample(html_files, num_files)
    return [str(f) for f in selected_files]

def save_results_to_json(results: Dict, output_path: str) -> None:
    """Save results to JSON file."""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"Results saved to: {output_path}")
    except Exception as e:
        logger.error(f"Failed to save results to {output_path}: {e}")
        raise

def load_prompt_from_file(prompt_file: str) -> str:
    """Load prompt from text file."""
    try:
        with open(prompt_file, 'r', encoding='utf-8') as f:
            prompt = f.read().strip()
        logger.info(f"Loaded prompt from {prompt_file} (length: {len(prompt)} chars)")
        return prompt
    except FileNotFoundError:
        logger.error(f"Prompt file not found: {prompt_file}")
        raise
    except Exception as e:
        logger.error(f"Failed to load prompt from {prompt_file}: {e}")
        raise

def validate_directory(directory: str) -> None:
    """Validate that directory exists and contains HTML files."""
    dir_path = Path(directory)
    
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory {directory} not found")
    
    if not dir_path.is_dir():
        raise ValueError(f"{directory} is not a directory")
    
    html_files = list(dir_path.glob("*.html"))
    if not html_files:
        raise FileNotFoundError(f"No HTML files found in {directory}")
    
    logger.info(f"Found {len(html_files)} HTML files in {directory}")

def create_output_directory(output_path: str) -> None:
    """Create output directory if it doesn't exist."""
    output_dir = Path(output_path).parent
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created output directory: {output_dir}")