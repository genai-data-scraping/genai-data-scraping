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

from config.settings import (
    SCREENSHOT_SCROLL_OVERLAP,
    SCREENSHOTS_PER_PAGE,
)

logger = logging.getLogger(__name__)

WIKIPEDIA_INITIAL_SCROLL_RATIO = 0.30

class ScreenshotCapture:


    def __init__(self,
                 output_dir: str = "scraped_photos",
                 window_width: int = 1920,
                 window_height: int = 1080,
                 wait_time: int = 3,
                 page_load_timeout: int = 15,
                 headless: bool = True,
                 disable_javascript: bool = True,
                 screenshots_per_page: int = 4,
                 scroll_overlap: int = 270):


        self.output_dir = Path(output_dir)
        self.window_width = window_width
        self.window_height = window_height
        self.wait_time = wait_time
        self.page_load_timeout = page_load_timeout
        self.headless = headless
        self.disable_javascript = disable_javascript
        self.screenshots_per_page = screenshots_per_page
        self.scroll_overlap = scroll_overlap
        self.driver = None


        self.output_dir.mkdir(exist_ok=True)

    @staticmethod
    def _is_wikipedia_page(html_file_path: str, site: str) -> bool:
        haystack = f"{site} {html_file_path}".lower()
        return "wikipedia" in haystack

    @staticmethod
    def _site_kind(html_file_path: str, site: str) -> str:
        haystack = f"{site} {html_file_path}".lower()
        if "wikipedia" in haystack:
            return "wikipedia"
        if "reuters" in haystack:
            return "reuters"
        if "cars" in haystack:
            return "cars"
        if "yahoo" in haystack or "finance" in haystack:
            return "yahoo"
        return "default"

    def _scroll_y_for_selector(self, selector: str) -> int | None:
        try:
            el = self.driver.find_element(By.CSS_SELECTOR, selector)
            return int(
                self.driver.execute_script(
                    "return Math.max(0, Math.round("
                    "arguments[0].getBoundingClientRect().top + window.pageYOffset - 24));",
                    el,
                )
            )
        except Exception:
            return None

    def _finalize_scroll_plan(
        self, raw_positions: list[int | None], max_scroll: int, count: int
    ) -> list[int]:
        positions: list[int] = []
        seen: set[int] = set()
        for y in raw_positions:
            if y is None:
                continue
            y = max(0, min(int(y), max_scroll))
            if y not in seen:
                seen.add(y)
                positions.append(y)
        positions.sort()
        if not positions:
            positions = [0]
        step = max(1, max_scroll // max(1, count - 1))
        while len(positions) < count:
            candidate = min(positions[-1] + step, max_scroll)
            if candidate in seen:
                if candidate >= max_scroll:
                    break
                candidate = min(candidate + step, max_scroll)
            if candidate in seen:
                break
            positions.append(candidate)
            seen.add(candidate)
        if len(positions) > count:
            keep = {positions[0], positions[-1]}
            mids = count - 2
            if mids > 0:
                for i in range(1, mids + 1):
                    keep.add(positions[min(len(positions) - 1, i * (len(positions) - 1) // (mids + 1))])
            positions = sorted(keep)[:count]
        return positions[:count]

    def _scroll_positions(
        self, total_height: int, viewport_height: int, start_offset: int = 0
    ) -> List[int]:

        count = self.screenshots_per_page
        max_scroll = max(0, total_height - viewport_height)
        start_offset = min(max(0, start_offset), max_scroll)

        if total_height <= viewport_height:
            return [start_offset]

        overlap = min(max(0, self.scroll_overlap), viewport_height - 1)
        step = max(1, viewport_height - overlap)
        positions = []
        for i in range(count):
            scroll_y = min(start_offset + i * step, max_scroll)
            if positions and scroll_y == positions[-1]:
                break
            positions.append(scroll_y)
        return positions

    def _build_scroll_plan(
        self, html_file_path: str, site: str, total_height: int, viewport_height: int
    ) -> list[int]:
        max_scroll = max(0, total_height - viewport_height)
        kind = self._site_kind(html_file_path, site)
        overlap = min(max(0, self.scroll_overlap), viewport_height - 1)
        step = max(1, viewport_height - overlap)

        if kind == "wikipedia":
            start_offset = int(total_height * WIKIPEDIA_INITIAL_SCROLL_RATIO)
            start_offset = min(max(0, start_offset), max_scroll)
            # 4th screenshot is always the page bottom (footer / last-edited line).
            return self._finalize_scroll_plan(
                [start_offset, start_offset + step, start_offset + 2 * step, max_scroll],
                max_scroll,
                self.screenshots_per_page,
            )

        if kind == "reuters":
            return self._finalize_scroll_plan(
                [0, step, step * 2, max_scroll],
                max_scroll,
                self.screenshots_per_page,
            )

        if kind == "cars":
            dealer_y = self._scroll_y_for_selector(".dealer-address")
            if dealer_y is None:
                dealer_y = self._scroll_y_for_selector("h3.seller-name")
            return self._finalize_scroll_plan(
                [0, dealer_y, step, max_scroll],
                max_scroll,
                self.screenshots_per_page,
            )

        if kind == "yahoo":
            stats_y = self._scroll_y_for_selector("[data-testid='quote-statistics']")
            return self._finalize_scroll_plan(
                [0, stats_y, step, max_scroll],
                max_scroll,
                self.screenshots_per_page,
            )

        return self._scroll_positions(total_height, viewport_height, start_offset=0)

    def _setup_driver(self) -> webdriver.Chrome:

        try:

            options = Options()

            if self.headless:
                options.add_argument('--headless')


            options.add_argument(f'--window-size={self.window_width},{self.window_height}')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-web-security')
            options.add_argument('--allow-running-insecure-content')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-plugins')


            if self.disable_javascript:
                options.add_argument('--disable-javascript')

                options.add_argument('--disable-plugins')
                options.add_argument('--disable-extensions')
                options.add_argument('--disable-default-apps')


                prefs = {
                    "profile.managed_default_content_settings.javascript": 2,
                    "profile.default_content_setting_values.javascript": 2
                }
                options.add_experimental_option("prefs", prefs)

                logger.info("JavaScript comprehensively disabled for screenshot capture")


            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')


            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(self.page_load_timeout)

            logger.info("Chrome driver initialized successfully")
            return driver

        except Exception as e:
            logger.error(f"Failed to setup Chrome driver: {e}")
            raise

    def _generate_filename(self, html_file_path: str, site: str, index: int, screenshot_num: int) -> str:


        html_filename = Path(html_file_path).stem

        safe_name = ''.join(c for c in html_filename if c.isalnum() or c in ('-', '_', '.'))
        safe_name = safe_name[:30]

        filename = f"{site}_{index:03d}_{safe_name}_scroll{screenshot_num}.png"
        return filename

    def capture_scrolled_screenshots_from_html(self, html_file_path: str, site: str, index: int) -> List[Dict[str, any]]:


        results = []

        try:

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

            logger.info(
                f"Capturing {self.screenshots_per_page} screenshot(s): {html_path.name}"
            )

            file_url = f"file://{html_path.absolute()}"


            self.driver.get(file_url)


            time.sleep(self.wait_time)


            logger.info("Waiting 2 seconds before starting screenshot capture...")
            time.sleep(2)


            total_height = self.driver.execute_script("return document.body.scrollHeight")
            viewport_height = self.window_height

            logger.info(f"Page height: {total_height}px, Viewport: {viewport_height}px")

            scroll_positions = self._build_scroll_plan(
                html_file_path, site, total_height, viewport_height
            )
            overlap = min(max(0, self.scroll_overlap), viewport_height - 1)
            step = max(1, viewport_height - overlap)
            logger.info(
                f"Scroll plan: {len(scroll_positions)} shot(s), "
                f"step={step}px, overlap={overlap}px, positions={scroll_positions}"
            )


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

                    self.driver.execute_script(f"window.scrollTo(0, {scroll_y});")
                    time.sleep(1)


                    filename = self._generate_filename(html_file_path, site, index, screenshot_num)
                    filepath = self.output_dir / filename


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


        all_results = []

        try:
            logger.info(f"Starting screenshot capture for {len(html_file_list)} HTML files ({self.screenshots_per_page} screenshots each)")

            for index, file_info in enumerate(html_file_list, 1):
                try:

                    file_results = self.capture_scrolled_screenshots_from_html(
                        html_file_path=file_info['source_file'],
                        site=file_info['site'],
                        index=index
                    )


                    for result in file_results:
                        if 'url' in file_info:
                            result['original_url'] = file_info['url']

                    all_results.extend(file_results)


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


        successful = sum(1 for r in all_results if r['success'])
        total_html_files = len(html_file_list)
        expected_screenshots = total_html_files * self.screenshots_per_page

        logger.info(f"Screenshot capture completed: {successful}/{expected_screenshots} screenshots successful from {total_html_files} HTML files")

        return all_results

    def close(self):

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


    capture_service = ScreenshotCapture(
        output_dir=output_dir,
        headless=headless,
        disable_javascript=disable_javascript,
        screenshots_per_page=screenshots_per_page,
        scroll_overlap=SCREENSHOT_SCROLL_OVERLAP,
    )

    return capture_service.capture_multiple_screenshots_from_html(html_file_list)


def capture_screenshots_from_urls(url_list: List[Dict[str, str]],
                                output_dir: str = "scraped_photos",
                                headless: bool = True) -> List[Dict[str, any]]:


    logger.warning("capture_screenshots_from_urls is deprecated. Use capture_screenshots_from_html_files instead.")
    return capture_screenshots_from_html_files(url_list, output_dir, headless, disable_javascript=True, screenshots_per_page=4)
