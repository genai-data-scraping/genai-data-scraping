import json
import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)

def load_prompt_from_file(prompt_file: str) -> str:
    """Load prompt from text file."""
    try:
        prompt_path = Path(prompt_file)
        
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt = f.read().strip()
        
        if not prompt:
            raise ValueError(f"Prompt file is empty: {prompt_file}")
        
        logger.info(f"Loaded prompt from {prompt_file} (length: {len(prompt)} chars)")
        return prompt
        
    except Exception as e:
        logger.error(f"Failed to load prompt from {prompt_file}: {e}")
        raise

def save_results_to_json(results: Dict, output_path: str) -> None:
    """Save processing results to JSON file."""
    try:
        output_file = Path(output_path)
        
        # Create output directory if it doesn't exist
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to: {output_path}")
        
        # Log file size
        file_size = output_file.stat().st_size
        logger.info(f"Output file size: {file_size:,} bytes")
        
    except Exception as e:
        logger.error(f"Failed to save results to {output_path}: {e}")
        raise

def validate_output_path(output_path: str) -> None:
    """Validate that output path is writable."""
    try:
        output_file = Path(output_path)
        
        # Check if parent directory exists or can be created
        parent_dir = output_file.parent
        if not parent_dir.exists():
            try:
                parent_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created output directory: {parent_dir}")
            except Exception as e:
                raise ValueError(f"Cannot create output directory {parent_dir}: {e}")
        
        # Test write permissions by creating a temporary file
        test_file = parent_dir / ".write_test"
        try:
            test_file.touch()
            test_file.unlink()  # Remove test file
        except Exception as e:
            raise ValueError(f"No write permission in directory {parent_dir}: {e}")
        
        logger.debug(f"Output path validated: {output_path}")
        
    except Exception as e:
        logger.error(f"Output path validation failed: {e}")
        raise

def create_backup_if_exists(output_path: str) -> None:
    """Create backup of existing output file."""
    output_file = Path(output_path)
    
    if output_file.exists():
        backup_path = output_file.with_suffix(f"{output_file.suffix}.backup")
        try:
            output_file.rename(backup_path)
            logger.info(f"Created backup: {backup_path}")
        except Exception as e:
            logger.warning(f"Failed to create backup: {e}")

def load_existing_results(output_path: str) -> Dict:
    """Load existing results if file exists."""
    try:
        output_file = Path(output_path)
        
        if not output_file.exists():
            return {}
        
        with open(output_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        logger.info(f"Loaded existing results from {output_path}")
        return results
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in existing file {output_path}: {e}")
        return {}
    except Exception as e:
        logger.error(f"Failed to load existing results from {output_path}: {e}")
        return {}

def get_file_info(file_path: str) -> Dict:
    """Get information about a file."""
    try:
        file_obj = Path(file_path)
        
        if not file_obj.exists():
            return {"exists": False, "path": file_path}
        
        stat = file_obj.stat()
        return {
            "exists": True,
            "path": str(file_obj.absolute()),
            "size_bytes": stat.st_size,
            "modified_time": stat.st_mtime,
            "is_file": file_obj.is_file(),
            "is_directory": file_obj.is_dir()
        }
        
    except Exception as e:
        logger.error(f"Error getting file info for {file_path}: {e}")
        return {"exists": False, "path": file_path, "error": str(e)}