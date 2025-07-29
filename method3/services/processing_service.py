import logging
from datetime import datetime
from typing import Dict, List
from collections import defaultdict
from pathlib import Path

from models.data_models import create_processing_result, create_summary_stats
from services.image_service import prepare_images_for_api, validate_image_folder, get_image_stats, find_image_files, encode_image_to_base64
from services.api_service import make_vision_api_request
from config.settings import get_image_config
from models.data_models import create_image_content_item

logger = logging.getLogger(__name__)

def group_screenshots_by_html_file(folder_path: str) -> Dict[str, List[str]]:
    """Group screenshot files by their source HTML file."""
    try:
        image_files = find_image_files(folder_path)
        grouped_files = defaultdict(list)
        
        for image_file in image_files:
            filename = image_file.name
            
            # Extract the base identifier (before _scroll)
            # Format: site_001_filename_scroll1.png -> site_001_filename
            if '_scroll' in filename:
                base_name = filename.split('_scroll')[0]
                grouped_files[base_name].append(str(image_file))
            else:
                # Fallback for files that don't follow the scrolled naming convention
                base_name = filename.rsplit('.', 1)[0]  # Remove extension
                grouped_files[base_name].append(str(image_file))
        
        # Sort files within each group to ensure consistent order
        for base_name in grouped_files:
            grouped_files[base_name].sort()
        
        logger.info(f"Grouped {len(image_files)} screenshots into {len(grouped_files)} HTML file groups")
        return dict(grouped_files)
        
    except Exception as e:
        logger.error(f"Error grouping screenshots: {e}")
        return {}

def prepare_image_group_for_api(image_paths: List[str]) -> List[Dict]:
    """Prepare a group of images (from same HTML file) for API call."""
    try:
        image_config = get_image_config()
        content_list = []
        
        for image_path in image_paths:
            try:
                # Encode image to base64
                base64_image = encode_image_to_base64(Path(image_path))
                
                # Create content item for API
                content_item = create_image_content_item(
                    base64_image, 
                    image_config["default_format"]
                )
                content_list.append(content_item)
                
                logger.debug(f"Prepared image: {Path(image_path).name}")
                
            except Exception as e:
                logger.error(f"Failed to prepare {image_path}: {e}")
                continue
        
        return content_list
        
    except Exception as e:
        logger.error(f"Error preparing image group: {e}")
        return []

def process_images_from_folder(folder_path: str, prompt: str) -> Dict:
    """Main processing function to extract data from grouped screenshots."""
    logger.info(f"Starting grouped image processing for folder: {folder_path}")
    
    try:
        # Validate folder first
        validate_image_folder(folder_path)
        
        # Get image statistics
        image_stats = get_image_stats(folder_path)
        logger.info(f"Image folder stats: {image_stats['total_files']} files, "
                   f"{image_stats['total_size_bytes']:,} bytes total")
        
        # Group screenshots by HTML file
        grouped_screenshots = group_screenshots_by_html_file(folder_path)
        
        if not grouped_screenshots:
            error_msg = "No screenshot groups could be created"
            logger.error(error_msg)
            return create_processing_result(
                success=False,
                error=error_msg,
                folder_path=folder_path
            )
        
        logger.info(f"Processing {len(grouped_screenshots)} HTML file groups")
        
        # Process each group separately
        all_api_results = []
        successful_groups = 0
        failed_groups = 0
        
        for group_name, image_paths in grouped_screenshots.items():
            logger.info(f"Processing group '{group_name}' with {len(image_paths)} screenshots")
            
            try:
                # Prepare images for this group
                image_content = prepare_image_group_for_api(image_paths)
                
                if not image_content:
                    logger.warning(f"No valid images in group '{group_name}'")
                    failed_groups += 1
                    continue
                
                # Make API request for this group
                api_result = make_vision_api_request(prompt, image_content)
                
                # Add group information to result
                api_result['group_name'] = group_name
                api_result['image_count'] = len(image_content)
                api_result['image_paths'] = image_paths
                
                if "error" not in api_result:
                    successful_groups += 1
                    logger.info(f"Successfully processed group '{group_name}'")
                else:
                    failed_groups += 1
                    logger.error(f"Failed to process group '{group_name}': {api_result['error']}")
                
                all_api_results.append(api_result)
                
            except Exception as e:
                logger.error(f"Error processing group '{group_name}': {e}")
                failed_groups += 1
                all_api_results.append({
                    'group_name': group_name,
                    'error': str(e),
                    'image_count': len(image_paths),
                    'image_paths': image_paths
                })
        
        # Determine overall success
        overall_success = successful_groups > 0
        
        # Create result
        result = create_processing_result(
            success=overall_success,
            data=all_api_results,
            image_count=sum(len(paths) for paths in grouped_screenshots.values()),
            folder_path=folder_path
        )
        
        # Add additional metadata
        result["timestamp"] = datetime.now().isoformat()
        result["image_stats"] = image_stats
        result["processing_info"] = {
            "total_groups": len(grouped_screenshots),
            "successful_groups": successful_groups,
            "failed_groups": failed_groups,
            "total_api_calls": len(all_api_results)
        }
        result["summary"] = create_summary_stats(
            total_found=len(grouped_screenshots),
            successfully_processed=successful_groups,
            failed=failed_groups,
            folder_path=folder_path
        )
        
        if overall_success:
            logger.info(f"Successfully processed {successful_groups}/{len(grouped_screenshots)} groups with {len(all_api_results)} API calls")
        else:
            logger.error(f"All groups failed processing")
            
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