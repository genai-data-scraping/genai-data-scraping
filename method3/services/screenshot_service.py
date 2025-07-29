import os
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

logger = logging.getLogger(__name__)

class ScreenshotCapture:
    """Service for capturing multiple scrolled screenshots of local HTML files using Selenium."""
    
    def __init__(self, 
                 output_dir: str = "scraped_photos",
                 window_width: int = 1920,
                 window_height: int = 1080,
                 wait_time: int = 3,
                 page_load_timeout: int = 15,
                 headless: bool = True,
                 disable_javascript: bool = True,
                 screenshots_per_page: int = 4):
        """
        Initialize screenshot capture service.
        
        Args:
            output_dir: Directory to save screenshots
            window_width: Browser window width
            window_height: Browser window height  
            wait_time: Time to wait after page load
            page_load_timeout: Maximum time to wait for page load
            headless: Run browser in headless mode
            disable_javascript: Disable JavaScript execution
            screenshots_per_page: Number of screenshots to take per HTML file (with scrolling)
        """
        self.output_dir = Path(output_dir)
        self.window_width = window_width
        self.window_height = window_height
        self.wait_time = wait_time
        self.page_load_timeout = page_load_timeout
        self.headless = headless
        self.disable_javascript = disable_javascript
        self.screenshots_per_page = screenshots_per_page
        self.driver = None
        
        # Create output directory
        self.output_dir.mkdir(exist_ok=True)
        
    def _setup_driver(self) -> webdriver.Chrome:
        """Setup Chrome driver with optimal settings for screenshots."""
        try:
            # Use regular Chrome options
            options = Options()
            
            if self.headless:
                options.add_argument('--headless')
            
            # Essential options for screenshot capture
            options.add_argument(f'--window-size={self.window_width},{self.window_height}')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-web-security')
            options.add_argument('--allow-running-insecure-content')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins')
            
            # Comprehensive JavaScript disabling (especially important for sites like Upwork)
            if self.disable_javascript:
                options.add_argument('--disable-javascript')
                # Also disable other script-related features
                options.add_argument('--disable-plugins')
                options.add_argument('--disable-extensions')
                options.add_argument('--disable-default-apps')
                
                # Set content settings to block JavaScript
                prefs = {
                    "profile.managed_default_content_settings.javascript": 2,  # 2 = block
                    "profile.default_content_setting_values.javascript": 2
                }
                options.add_experimental_option("prefs", prefs)
                
                logger.info("JavaScript comprehensively disabled for screenshot capture")
            
            # Don't disable images for local HTML files - we want to see the full page
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            # Create driver
            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(self.page_load_timeout)
            
            logger.info("Chrome driver initialized successfully")
            return driver
            
        except Exception as e:
            logger.error(f"Failed to setup Chrome driver: {e}")
            raise
    
    def _generate_filename(self, html_file_path: str, site: str, index: int, screenshot_num: int) -> str:
        """Generate a safe filename for the screenshot."""
        # Extract filename from HTML file path
        html_filename = Path(html_file_path).stem
        # Clean filename for screenshot
        safe_name = ''.join(c for c in html_filename if c.isalnum() or c in ('-', '_', '.'))
        safe_name = safe_name[:30]  # Shorter limit to accommodate screenshot number
        
        filename = f"{site}_{index:03d}_{safe_name}_scroll{screenshot_num}.png"
        return filename
    
    def capture_scrolled_screenshots_from_html(self, html_file_path: str, site: str, index: int) -> List[Dict[str, any]]:
        """
        Capture multiple screenshots of a local HTML file with scrolling.
        
        Args:
            html_file_path: Path to local HTML file
            site: Site name (for filename)
            index: Index number (for filename)
            
        Returns:
            List of screenshot results for this HTML file
        """
        results = []
        
        try:
            # Check if HTML file exists
            html_path = Path(html_file_path)
            if not html_path.exists():
                error_result = {
                    'html_file': html_file_path,
                    'site': site,
                    'index': index,
                    'screenshot_num': 0,
                    'success': False,
                    'filename': None,
                    'filepath': None,
                    'error': f"HTML file not found: {html_file_path}",
                    'file_size': 0
                }
                logger.error(error_result['error'])
                return [error_result]
            
            if not self.driver:
                self.driver = self._setup_driver()
            
            logger.info(f"Capturing {self.screenshots_per_page} scrolled screenshots of: {html_path.name}")
            
            # Convert to file:// URL for local file access
            file_url = f"file://{html_path.absolute()}"
            
            # Navigate to local HTML file
            self.driver.get(file_url)
            
            # Wait for page to load
            time.sleep(self.wait_time)
            
            # Additional wait before starting screenshots (ensures page is fully loaded)
            logger.info("Waiting 2 seconds before starting screenshot capture...")
            time.sleep(2)
            
            # Get page dimensions
            total_height = self.driver.execute_script("return document.body.scrollHeight")
            viewport_height = self.window_height
            
            logger.info(f"Page height: {total_height}px, Viewport: {viewport_height}px")
            
            # Calculate scroll positions
            scroll_positions = []
            if total_height <= viewport_height:
                # Page fits in one viewport
                scroll_positions = [0]
            else:
                # Calculate scroll positions to capture the full page
                for i in range(self.screenshots_per_page):
                    if i == 0:
                        scroll_positions.append(0)  # Top of page
                    elif i == self.screenshots_per_page - 1:
                        scroll_positions.append(max(0, total_height - viewport_height))  # Bottom of page
                    else:
                        # Evenly distribute middle positions
                        position = int((total_height - viewport_height) * i / (self.screenshots_per_page - 1))
                        scroll_positions.append(position)
            
            # Take screenshots at each scroll position
            for screenshot_num, scroll_y in enumerate(scroll_positions, 1):
                result = {
                    'html_file': html_file_path,
                    'site': site,
                    'index': index,
                    'screenshot_num': screenshot_num,
                    'scroll_position': scroll_y,
                    'success': False,
                    'filename': None,
                    'filepath': None,
                    'error': None,
                    'file_size': 0
                }
                
                try:
                    # Scroll to position
                    self.driver.execute_script(f"window.scrollTo(0, {scroll_y});")
                    time.sleep(1)  # Wait for scroll to complete
                    
                    # Generate filename and full path
                    filename = self._generate_filename(html_file_path, site, index, screenshot_num)
                    filepath = self.output_dir / filename
                    
                    # Take screenshot
                    success = self.driver.save_screenshot(str(filepath))
                    
                    if success and filepath.exists():
                        result.update({
                            'success': True,
                            'filename': filename,
                            'filepath': str(filepath),
                            'file_size': filepath.stat().st_size
                        })
                        logger.info(f"Screenshot saved: {filename} (scroll pos: {scroll_y}px, {result['file_size']} bytes)")
                    else:
                        result['error'] = "Screenshot file was not created"
                        logger.error(f"Failed to save screenshot {screenshot_num} for {html_file_path}")
                        
                except Exception as e:
                    result['error'] = f"Error taking screenshot {screenshot_num}: {str(e)}"
                    logger.error(result['error'])
                
                results.append(result)
                
                # Break if we only need one screenshot and page is small
                if len(scroll_positions) == 1:
                    break
                    
        except TimeoutException:
            error_result = {
                'html_file': html_file_path,
                'site': site,
                'index': index,
                'screenshot_num': 0,
                'success': False,
                'error': f"Page load timeout after {self.page_load_timeout}s",
                'filename': None,
                'filepath': None,
                'file_size': 0
            }
            logger.error(f"Timeout loading {html_file_path}")
            results.append(error_result)
            
        except WebDriverException as e:
            error_result = {
                'html_file': html_file_path,
                'site': site,
                'index': index,
                'screenshot_num': 0,
                'success': False,
                'error': f"WebDriver error: {str(e)}",
                'filename': None,
                'filepath': None,
                'file_size': 0
            }
            logger.error(f"WebDriver error for {html_file_path}: {e}")
            results.append(error_result)
            
        except Exception as e:
            error_result = {
                'html_file': html_file_path,
                'site': site,
                'index': index,
                'screenshot_num': 0,
                'success': False,
                'error': f"Unexpected error: {str(e)}",
                'filename': None,
                'filepath': None,
                'file_size': 0
            }
            logger.error(f"Unexpected error capturing {html_file_path}: {e}")
            results.append(error_result)
        
        return results
    
    def capture_multiple_screenshots_from_html(self, html_file_list: List[Dict[str, str]]) -> List[Dict[str, any]]:
        """
        Capture multiple scrolled screenshots for multiple HTML files.
        
        Args:
            html_file_list: List of dicts with 'source_file', 'site' keys
            
        Returns:
            List of capture results (grouped by HTML file)
        """
        all_results = []
        
        try:
            logger.info(f"Starting screenshot capture for {len(html_file_list)} HTML files ({self.screenshots_per_page} screenshots each)")
            
            for index, file_info in enumerate(html_file_list, 1):
                try:
                    # Get screenshots for this HTML file
                    file_results = self.capture_scrolled_screenshots_from_html(
                        html_file_path=file_info['source_file'],
                        site=file_info['site'], 
                        index=index
                    )
                    
                    # Add original URL info if available
                    for result in file_results:
                        if 'url' in file_info:
                            result['original_url'] = file_info['url']
                    
                    all_results.extend(file_results)
                    
                    # Small delay between HTML files
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error processing HTML file {index}: {e}")
                    error_result = {
                        'html_file': file_info.get('source_file', ''),
                        'site': file_info.get('site', ''),
                        'index': index,
                        'screenshot_num': 0,
                        'success': False,
                        'error': str(e),
                        'original_url': file_info.get('url', ''),
                        'filename': None,
                        'filepath': None,
                        'file_size': 0
                    }
                    all_results.append(error_result)
                    
        finally:
            self.close()
        
        # Log summary
        successful = sum(1 for r in all_results if r['success'])
        total_html_files = len(html_file_list)
        expected_screenshots = total_html_files * self.screenshots_per_page
        
        logger.info(f"Screenshot capture completed: {successful}/{expected_screenshots} screenshots successful from {total_html_files} HTML files")
        
        return all_results
    
    def close(self):
        """Close the browser driver."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser driver closed")
            except Exception as e:
                logger.error(f"Error closing driver: {e}")
            finally:
                self.driver = None

def capture_screenshots_from_html_files(html_file_list: List[Dict[str, str]], 
                                      output_dir: str = "scraped_photos",
                                      headless: bool = True,
                                      disable_javascript: bool = True,
                                      screenshots_per_page: int = 4) -> List[Dict[str, any]]:
    """
    Convenience function to capture multiple scrolled screenshots from a list of HTML files.
    
    Args:
        html_file_list: List of HTML file dictionaries with 'source_file', 'site' keys
        output_dir: Directory to save screenshots
        headless: Run browser in headless mode
        disable_javascript: Disable JavaScript execution
        screenshots_per_page: Number of screenshots to take per HTML file (with scrolling)
        
    Returns:
        List of capture results
    """
    capture_service = ScreenshotCapture(
        output_dir=output_dir,
        headless=headless,
        disable_javascript=disable_javascript,
        screenshots_per_page=screenshots_per_page
    )
    
    return capture_service.capture_multiple_screenshots_from_html(html_file_list)

# Keep the old function for backwards compatibility, but mark as deprecated
def capture_screenshots_from_urls(url_list: List[Dict[str, str]], 
                                output_dir: str = "scraped_photos",
                                headless: bool = True) -> List[Dict[str, any]]:
    """
    DEPRECATED: Use capture_screenshots_from_html_files instead.
    This function now captures screenshots from local HTML files rather than URLs.
    """
    logger.warning("capture_screenshots_from_urls is deprecated. Use capture_screenshots_from_html_files instead.")
    return capture_screenshots_from_html_files(url_list, output_dir, headless, disable_javascript=True, screenshots_per_page=4) 