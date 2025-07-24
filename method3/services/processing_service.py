import logging
from datetime import datetime
from typing import Dict

from models.data_models import create_processing_result, create_summary_stats
from services.image_service import prepare_images_for_api, validate_image_folder, get_image_stats
from services.api_service import make_vision_api_request

logger = logging.getLogger(__name__)

def process_images_from_folder(folder_path: str, prompt: str) -> Dict:
    """Main processing function to extract data from all images in a folder."""
    logger.info(f"Starting image processing for folder: {folder_path}")
    
    try:
        # Validate folder first
        validate_image_folder(folder_path)
        
        # Get image statistics
        image_stats = get_image_stats(folder_path)
        logger.info(f"Image folder stats: {image_stats['total_files']} files, "
                   f"{image_stats['total_size_bytes']:,} bytes total")
        
        # Prepare images for API
        image_content, processing_info = prepare_images_for_api(folder_path)
        
        if not image_content:
            error_msg = "No valid images could be prepared for processing"
            logger.error(error_msg)
            return create_processing_result(
                success=False,
                error=error_msg,
                folder_path=folder_path
            )
        
        logger.info(f"Prepared {len(image_content)} images for API processing")
        
        # Make API request
        api_result = make_vision_api_request(prompt, image_content)
        
        # Process API response
        if "error" in api_result:
            logger.error(f"API processing failed: {api_result['error']}")
            return create_processing_result(
                success=False,
                error=api_result["error"],
                image_count=len(image_content),
                folder_path=folder_path
            )
        
        # Create successful result
        result = create_processing_result(
            success=True,
            data=api_result.get("data"),
            image_count=len(image_content),
            folder_path=folder_path
        )
        
        # Add additional metadata
        result["timestamp"] = datetime.now().isoformat()
        result["image_stats"] = image_stats
        result["processing_info"] = processing_info
        result["summary"] = create_summary_stats(
            total_found=len(processing_info),
            successfully_processed=len(image_content),
            failed=len(processing_info) - len(image_content),
            folder_path=folder_path
        )
        
        logger.info(f"Successfully processed {len(image_content)} images")
        return result
        
    except FileNotFoundError as e:
        error_msg = f"Folder not found: {e}"
        logger.error(error_msg)
        return create_processing_result(
            success=False,
            error=error_msg,
            folder_path=folder_path
        )
    except ValueError as e:
        error_msg = f"Invalid folder or no images: {e}"
        logger.error(error_msg)
        return create_processing_result(
            success=False,
            error=error_msg,
            folder_path=folder_path
        )
    except Exception as e:
        error_msg = f"Unexpected error during processing: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return create_processing_result(
            success=False,
            error=error_msg,
            folder_path=folder_path
        )

def validate_processing_inputs(folder_path: str, prompt: str) -> None:
    """Validate inputs before processing."""
    if not folder_path or not folder_path.strip():
        raise ValueError("Folder path cannot be empty")
    
    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty")
    
    # Additional validation
    validate_image_folder(folder_path)
    
    logger.info("Processing inputs validated successfully")