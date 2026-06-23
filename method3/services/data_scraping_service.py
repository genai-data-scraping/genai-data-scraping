import logging
from typing import Dict, List
from pathlib import Path

from services.url_service import extract_urls_from_data_directory
from services.screenshot_service import capture_screenshots_from_html_files
from services.processing_service import process_images_from_folder
from utils.logger import get_logger

logger = get_logger(__name__)


def _clear_screenshot_dir(screenshot_dir: str) -> None:

    path = Path(screenshot_dir)
    if not path.is_dir():
        return
    removed = 0
    for image in path.iterdir():
        if image.is_file() and image.suffix.lower() in {
            ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"
        }:
            image.unlink(missing_ok=True)
            removed += 1
    if removed:
        logger.info(f"Cleared {removed} previous screenshot(s) from {path}")


def _group_names_from_capture(screenshot_results: List[Dict]) -> List[str]:

    names = []
    for result in screenshot_results:
        if not result.get("success") or not result.get("filename"):
            continue
        filename = result["filename"]
        base = filename.split("_scroll", 1)[0] if "_scroll" in filename else filename.rsplit(".", 1)[0]
        if base and base not in names:
            names.append(base)
    return names

class DataScrapingService:


    def __init__(self,
                 data_dir: str = "../sample_data",
                 screenshot_dir: str = "scraped_photos",
                 num_files_per_site: int = 5,
                 headless: bool = True,
                 disable_javascript: bool = True,
                 screenshots_per_page: int = 4):


        self.data_dir = data_dir
        self.screenshot_dir = screenshot_dir
        self.num_files_per_site = num_files_per_site
        self.headless = headless
        self.disable_javascript = disable_javascript
        self.screenshots_per_page = screenshots_per_page

    def extract_and_capture(self) -> Dict:


        logger.info("Starting HTML file extraction and screenshot capture process")

        try:

            logger.info("Step 1: Extracting HTML files and URLs...")
            html_info_list = extract_urls_from_data_directory(
                data_dir=self.data_dir,
                num_files_per_site=self.num_files_per_site
            )

            if not html_info_list:
                return {
                    "success": False,
                    "error": "No HTML files found in data directory",
                    "html_files_found": 0,
                    "screenshots_captured": 0
                }

            logger.info(f"Found {len(html_info_list)} HTML files")

            _clear_screenshot_dir(self.screenshot_dir)


            logger.info(f"Step 2: Capturing {self.screenshots_per_page} screenshots per HTML file...")
            screenshot_results = capture_screenshots_from_html_files(
                html_file_list=html_info_list,
                output_dir=self.screenshot_dir,
                headless=self.headless,
                disable_javascript=self.disable_javascript,
                screenshots_per_page=self.screenshots_per_page
            )


            successful_screenshots = [r for r in screenshot_results if r['success']]
            failed_screenshots = [r for r in screenshot_results if not r['success']]

            logger.info(f"Screenshot capture completed: {len(successful_screenshots)}/{len(screenshot_results)} screenshots successful")

            return {
                "success": True,
                "html_files_found": len(html_info_list),
                "screenshots_captured": len(successful_screenshots),
                "screenshots_failed": len(failed_screenshots),
                "screenshots_per_page": self.screenshots_per_page,
                "expected_screenshots": len(html_info_list) * self.screenshots_per_page,
                "screenshot_results": screenshot_results,
                "screenshot_directory": self.screenshot_dir,
                "html_files_info": html_info_list,
                "successful_screenshots": successful_screenshots,
                "failed_screenshots": failed_screenshots
            }

        except Exception as e:
            logger.error(f"Error in extract_and_capture: {e}")
            return {
                "success": False,
                "error": str(e),
                "html_files_found": 0,
                "screenshots_captured": 0
            }

    def full_pipeline(self, prompt: str) -> Dict:


        logger.info("Starting full data scraping pipeline")

        try:

            capture_results = self.extract_and_capture()

            if not capture_results["success"]:
                return {
                    "success": False,
                    "error": f"Screenshot capture failed: {capture_results.get('error', 'Unknown error')}",
                    "stage": "screenshot_capture",
                    "capture_results": capture_results
                }

            if capture_results["screenshots_captured"] == 0:
                return {
                    "success": False,
                    "error": "No screenshots were successfully captured",
                    "stage": "screenshot_capture",
                    "capture_results": capture_results
                }


            logger.info("Step 3: Processing screenshots with vision API (grouped by HTML file)...")
            group_names = _group_names_from_capture(capture_results["screenshot_results"])
            vision_results = process_images_from_folder(
                folder_path=self.screenshot_dir,
                prompt=prompt,
                group_names=group_names,
            )


            pipeline_results = {
                "success": vision_results.get("success", False),
                "pipeline_completed": True,
                "html_files_found": capture_results["html_files_found"],
                "screenshots_captured": capture_results["screenshots_captured"],
                "screenshots_failed": capture_results["screenshots_failed"],
                "screenshots_per_page": capture_results["screenshots_per_page"],
                "expected_screenshots": capture_results["expected_screenshots"],
                "vision_processing": vision_results,
                "capture_results": capture_results,
                "screenshot_directory": self.screenshot_dir
            }

            if vision_results.get("success"):
                api_calls_made = vision_results.get("processing_info", {}).get("total_api_calls", 0)
                successful_groups = vision_results.get("processing_info", {}).get("successful_groups", 0)
                logger.info(f"Full pipeline completed successfully: {successful_groups} groups processed with {api_calls_made} API calls")
            else:
                logger.error(f"Vision processing failed: {vision_results.get('error', 'Unknown error')}")
                pipeline_results["error"] = f"Vision processing failed: {vision_results.get('error', 'Unknown error')}"
                pipeline_results["stage"] = "vision_processing"

            return pipeline_results

        except Exception as e:
            logger.error(f"Error in full pipeline: {e}")
            return {
                "success": False,
                "error": str(e),
                "stage": "pipeline_execution",
                "pipeline_completed": False
            }

def run_data_scraping_pipeline(data_dir: str = "../sample_data",
                             screenshot_dir: str = "scraped_photos",
                             prompt: str = "",
                             num_files_per_site: int = 5,
                             headless: bool = True,
                             disable_javascript: bool = True,
                             screenshots_per_page: int = 4) -> Dict:


    service = DataScrapingService(
        data_dir=data_dir,
        screenshot_dir=screenshot_dir,
        num_files_per_site=num_files_per_site,
        headless=headless,
        disable_javascript=disable_javascript,
        screenshots_per_page=screenshots_per_page
    )

    if prompt:
        return service.full_pipeline(prompt)
    else:
        return service.extract_and_capture()
