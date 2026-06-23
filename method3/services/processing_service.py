import logging
from datetime import datetime
from typing import Dict, List
from collections import defaultdict
from pathlib import Path

from models.data_models import create_processing_result, create_summary_stats
from services.image_service import (
    validate_image_folder,
    get_image_stats,
    find_image_files,
    encode_image_to_base64,
    mime_type_for_image,
)
from services.api_service import make_vision_api_request
from models.data_models import create_image_content_item

logger = logging.getLogger(__name__)


def _sum_llm_times(api_results: List[Dict]) -> float:
    times = [
        r["llm_processing_time_seconds"]
        for r in api_results
        if r.get("llm_processing_time_seconds") is not None
    ]
    return round(sum(times), 3) if times else 0.0

def group_screenshots_by_html_file(folder_path: str) -> Dict[str, List[str]]:

    try:
        image_files = find_image_files(folder_path)
        grouped_files = defaultdict(list)

        for image_file in image_files:
            filename = image_file.name


            if '_scroll' in filename:
                base_name = filename.split('_scroll')[0]
                grouped_files[base_name].append(str(image_file))
            else:

                base_name = filename.rsplit('.', 1)[0]
                grouped_files[base_name].append(str(image_file))


        for base_name in grouped_files:
            grouped_files[base_name].sort()

        logger.info(f"Grouped {len(image_files)} screenshots into {len(grouped_files)} HTML file groups")
        return dict(grouped_files)

    except Exception as e:
        logger.error(f"Error grouping screenshots: {e}")
        return {}

def prepare_image_group_for_api(image_paths: List[str]) -> List[Dict]:

    try:
        content_list = []

        for image_path in image_paths:
            try:

                base64_image = encode_image_to_base64(Path(image_path))


                content_item = create_image_content_item(
                    base64_image,
                    mime_type_for_image(Path(image_path)),
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

def process_image_group(
    image_paths: List[str],
    prompt: str,
    group_name: str,
    folder_path: str = "",
) -> Dict:

    logger.info(
        f"Processing group '{group_name}' with {len(image_paths)} screenshot(s)"
    )

    image_content = prepare_image_group_for_api(image_paths)
    if not image_content:
        error_msg = f"No valid images in group '{group_name}'"
        logger.error(error_msg)
        return create_processing_result(
            success=False,
            error=error_msg,
            folder_path=folder_path or str(Path(image_paths[0]).parent),
        )

    api_result = make_vision_api_request(
        prompt, image_content, group_name=group_name
    )
    api_result["group_name"] = group_name
    api_result["image_count"] = len(image_content)
    api_result["image_paths"] = image_paths

    success = "error" not in api_result
    if success:
        logger.info(f"Successfully processed group '{group_name}'")
    else:
        logger.error(
            f"Failed to process group '{group_name}': {api_result['error']}"
        )

    parent = folder_path or str(Path(image_paths[0]).parent)
    result = create_processing_result(
        success=success,
        data=[api_result],
        image_count=len(image_paths),
        folder_path=parent,
    )
    result["timestamp"] = datetime.now().isoformat()
    result["image_stats"] = {
        "total_files": len(image_paths),
        "total_size_bytes": sum(Path(p).stat().st_size for p in image_paths),
    }
    result["processing_info"] = {
        "total_groups": 1,
        "successful_groups": 1 if success else 0,
        "failed_groups": 0 if success else 1,
        "total_api_calls": 1,
        "group_name": group_name,
        "total_llm_processing_time_seconds": _sum_llm_times([api_result]),
    }
    result["summary"] = create_summary_stats(
        total_found=1,
        successfully_processed=1 if success else 0,
        failed=0 if success else 1,
        folder_path=parent,
    )
    return result


def process_images_from_folder(folder_path: str, prompt: str,
                               group_names: List[str] = None) -> Dict:

    logger.info(f"Starting grouped image processing for folder: {folder_path}")

    try:

        validate_image_folder(folder_path)


        image_stats = get_image_stats(folder_path)
        logger.info(f"Image folder stats: {image_stats['total_files']} files, "
                   f"{image_stats['total_size_bytes']:,} bytes total")


        grouped_screenshots = group_screenshots_by_html_file(folder_path)

        if group_names is not None:
            allowed = set(group_names)
            grouped_screenshots = {
                name: paths
                for name, paths in grouped_screenshots.items()
                if name in allowed
            }
            logger.info(
                f"Filtered to {len(grouped_screenshots)} requested group(s): "
                f"{sorted(grouped_screenshots.keys())}"
            )

        if not grouped_screenshots:
            error_msg = "No screenshot groups could be created"
            logger.error(error_msg)
            return create_processing_result(
                success=False,
                error=error_msg,
                folder_path=folder_path
            )

        logger.info(f"Processing {len(grouped_screenshots)} HTML file groups")


        all_api_results = []
        successful_groups = 0
        failed_groups = 0

        for group_name, image_paths in grouped_screenshots.items():
            logger.info(f"Processing group '{group_name}' with {len(image_paths)} screenshots")

            try:

                image_content = prepare_image_group_for_api(image_paths)

                if not image_content:
                    logger.warning(f"No valid images in group '{group_name}'")
                    failed_groups += 1
                    continue


                api_result = make_vision_api_request(
                    prompt, image_content, group_name=group_name
                )


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


        overall_success = successful_groups > 0


        result = create_processing_result(
            success=overall_success,
            data=all_api_results,
            image_count=sum(len(paths) for paths in grouped_screenshots.values()),
            folder_path=folder_path
        )


        result["timestamp"] = datetime.now().isoformat()
        result["image_stats"] = image_stats
        result["processing_info"] = {
            "total_groups": len(grouped_screenshots),
            "successful_groups": successful_groups,
            "failed_groups": failed_groups,
            "total_api_calls": len(all_api_results),
            "total_llm_processing_time_seconds": _sum_llm_times(all_api_results),
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

    if not folder_path or not folder_path.strip():
        raise ValueError("Folder path cannot be empty")

    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty")


    validate_image_folder(folder_path)

    logger.info("Processing inputs validated successfully")
