import base64
import logging
from pathlib import Path
from typing import List, Dict, Tuple

from config.settings import get_image_config
from models.data_models import create_image_content_item, create_image_info

logger = logging.getLogger(__name__)

def find_image_files(folder_path: str) -> List[Path]:
    """Find all supported image files in the folder."""
    try:
        image_config = get_image_config()
        folder = Path(folder_path)
        
        if not folder.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        
        if not folder.is_dir():
            raise ValueError(f"Path is not a directory: {folder_path}")
        
        # Find all image files with supported extensions
        image_files = [
            f for f in folder.iterdir() 
            if f.is_file() and f.suffix.lower() in image_config["supported_extensions"]
        ]
        
        # Sort for consistent ordering
        image_files.sort()
        
        logger.info(f"Found {len(image_files)} image files in {folder_path}")
        return image_files
        
    except Exception as e:
        logger.error(f"Error finding image files in {folder_path}: {e}")
        raise

def encode_image_to_base64(image_path: Path) -> str:
    """Encode a single image file to base64."""
    try:
        with open(image_path, "rb") as f:
            image_data = f.read()
        
        base64_encoded = base64.b64encode(image_data).decode('utf-8')
        logger.debug(f"Successfully encoded {image_path.name} to base64")
        return base64_encoded
        
    except Exception as e:
        logger.error(f"Failed to encode {image_path}: {e}")
        raise

def prepare_images_for_api(folder_path: str) -> Tuple[List[Dict], List[Dict]]:
    """Prepare all images for API call, return content list and processing info."""
    logger.info(f"Preparing images from folder: {folder_path}")
    
    image_files = find_image_files(folder_path)
    
    if not image_files:
        logger.warning(f"No image files found in {folder_path}")
        return [], []
    
    content_list = []
    processing_info = []
    image_config = get_image_config()
    
    for image_file in image_files:
        try:
            # Encode image to base64
            base64_image = encode_image_to_base64(image_file)
            
            # Create content item for API
            content_item = create_image_content_item(
                base64_image, 
                image_config["default_format"]
            )
            content_list.append(content_item)
            
            # Create processing info
            info = create_image_info(image_file, success=True)
            processing_info.append(info)
            
            logger.debug(f"Successfully prepared {image_file.name}")
            
        except Exception as e:
            logger.error(f"Failed to prepare {image_file.name}: {e}")
            
            # Add failed processing info
            info = create_image_info(image_file, success=False, error=str(e))
            processing_info.append(info)
            continue
    
    logger.info(f"Successfully prepared {len(content_list)} out of {len(image_files)} images")
    return content_list, processing_info

def validate_image_folder(folder_path: str) -> None:
    """Validate that the image folder exists and contains images."""
    folder = Path(folder_path)
    
    if not folder.exists():
        raise FileNotFoundError(f"Image folder not found: {folder_path}")
    
    if not folder.is_dir():
        raise ValueError(f"Path is not a directory: {folder_path}")
    
    image_files = find_image_files(folder_path)
    if not image_files:
        raise ValueError(f"No supported image files found in {folder_path}")
    
    logger.info(f"Validated image folder: {folder_path} ({len(image_files)} images)")

def get_image_stats(folder_path: str) -> Dict:
    """Get statistics about images in the folder."""
    try:
        image_files = find_image_files(folder_path)
        image_config = get_image_config()
        
        stats = {
            "total_files": len(image_files),
            "total_size_bytes": sum(f.stat().st_size for f in image_files),
            "supported_extensions": list(image_config["supported_extensions"]),
            "file_breakdown": {}
        }
        
        # Count files by extension
        for image_file in image_files:
            ext = image_file.suffix.lower()
            stats["file_breakdown"][ext] = stats["file_breakdown"].get(ext, 0) + 1
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting image stats for {folder_path}: {e}")
        return {"error": str(e)}