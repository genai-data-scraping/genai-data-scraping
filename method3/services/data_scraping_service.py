import logging
from typing import Dict, List
from pathlib import Path

from services.url_service import extract_urls_from_data_directory
from services.screenshot_service import capture_screenshots_from_html_files
from services.processing_service import process_images_from_folder
from utils.logger import get_logger

logger = get_logger(__name__)

class DataScrapingService:
    """Integrated service for HTML file screenshot capture and vision processing."""
    
    def __init__(self, 
                 data_dir: str = "../sample_data",
                 screenshot_dir: str = "scraped_photos",
                 num_files_per_site: int = 5,
                 headless: bool = True,
                 disable_javascript: bool = True,
                 screenshots_per_page: int = 4):
        """
        Initialize the data scraping service.
        
        Args:
            data_dir: Directory containing HTML files
            screenshot_dir: Directory to save screenshots
            num_files_per_site: Number of files to process per site
            headless: Run browser in headless mode
            disable_javascript: Disable JavaScript execution (recommended for cleaner screenshots)
            screenshots_per_page: Number of screenshots to take per HTML file (with scrolling)
        """
        self.data_dir = data_dir
        self.screenshot_dir = screenshot_dir
        self.num_files_per_site = num_files_per_site
        self.headless = headless
        self.disable_javascript = disable_javascript
        self.screenshots_per_page = screenshots_per_page
        
    def extract_and_capture(self) -> Dict:
        """
        Extract HTML files and capture screenshots from them.
        
        Returns:
            Dict containing extraction and capture results
        """
        logger.info("Starting HTML file extraction and screenshot capture process")
        
        try:
            # Step 1: Extract HTML file paths and URLs
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
            
            # Step 2: Capture screenshots from HTML files
            logger.info(f"Step 2: Capturing {self.screenshots_per_page} screenshots per HTML file...")
            screenshot_results = capture_screenshots_from_html_files(
                html_file_list=html_info_list,
                output_dir=self.screenshot_dir,
                headless=self.headless,
                disable_javascript=self.disable_javascript,
                screenshots_per_page=self.screenshots_per_page
            )
            
            # Analyze results
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
        """
        Run the complete pipeline: extract HTML files, capture screenshots, and process with vision API.
        
        Args:
            prompt: Prompt for vision API processing
            
        Returns:
            Dict containing complete pipeline results
        """
        logger.info("Starting full data scraping pipeline")
        
        try:
            # Step 1 & 2: Extract HTML files and capture screenshots
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
            
            # Step 3: Process screenshots with vision API (grouped by HTML file)
            logger.info("Step 3: Processing screenshots with vision API (grouped by HTML file)...")
            vision_results = process_images_from_folder(
                folder_path=self.screenshot_dir,
                prompt=prompt
            )
            
            # Combine results
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
    """
    Convenience function to run the complete data scraping pipeline.
    
    Args:
        data_dir: Directory containing HTML files
        screenshot_dir: Directory to save screenshots
        prompt: Prompt for vision API processing
        num_files_per_site: Number of files to process per site
        headless: Run browser in headless mode
        disable_javascript: Disable JavaScript execution (recommended for cleaner screenshots)
        screenshots_per_page: Number of screenshots to take per HTML file (with scrolling)
        
    Returns:
        Dict containing pipeline results
    """
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