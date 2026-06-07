"""
Massachusetts State Building Code Scraper
Scrapes the 10th Edition handbook and extracts all rules and regulations
at paragraph resolution for Mantis space creation.
"""

import requests
from bs4 import BeautifulSoup
import pdfplumber
import pandas as pd
from io import BytesIO
from urllib.parse import urljoin, urlparse
import time
import logging
from typing import List, Dict, Optional
import re
import json

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import Selenium (optional, for bot protection bypass)
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logger.warning("Selenium not available. Install with: pip install selenium webdriver-manager")

# Logging already configured above

BASE_URL = "https://www.mass.gov/handbook/tenth-edition-of-the-ma-state-building-code-780"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Cache-Control": "max-age=0"
}

class BuildingCodeScraper:
    """Scraper for Massachusetts State Building Code handbook."""
    
    def __init__(self, base_url: str = BASE_URL, delay: float = 1.0, use_selenium: bool = False, cookies_file: Optional[str] = None, headless: bool = True):
        """
        Initialize the scraper.
        
        Args:
            base_url: Base URL of the handbook
            delay: Delay between requests (seconds)
            use_selenium: Use Selenium browser automation (for bypassing bot protection)
            cookies_file: Path to JSON file with browser cookies (for authenticated downloads)
            headless: Run Selenium in headless mode (False = visible browser, better for bot protection)
        """
        self.base_url = base_url
        self.delay = delay
        self.use_selenium = use_selenium and SELENIUM_AVAILABLE
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.data = []
        self.paragraph_id = 1
        self.driver = None
        
        # Load cookies if provided
        if cookies_file:
            self._load_cookies(cookies_file)
        
        if self.use_selenium:
            self._init_selenium(headless=headless)
            # Also load cookies into Selenium if available
            if cookies_file:
                self._load_cookies_to_selenium(cookies_file)
    
    def _init_selenium(self, headless: bool = True):
        """Initialize Selenium WebDriver."""
        try:
            chrome_options = Options()
            if headless:
                chrome_options.add_argument('--headless')  # Run in background
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # Enable performance logging to capture network responses
            chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
            
            # Set download preferences to save PDFs
            import os
            download_dir = os.path.join(os.getcwd(), 'selenium_downloads')
            os.makedirs(download_dir, exist_ok=True)
            prefs = {
                "download.default_directory": download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "plugins.always_open_pdf_externally": True  # Download PDFs instead of viewing
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Selenium WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Selenium: {e}")
            logger.warning("Falling back to requests-only mode")
            self.use_selenium = False
    
    def _load_cookies(self, cookies_file: str) -> None:
        """Load cookies from JSON file into requests session."""
        try:
            import json
            with open(cookies_file, 'r') as f:
                cookies_data = json.load(f)
            
            # Handle different cookie export formats
            if isinstance(cookies_data, list):
                # Cookie-Editor format: list of cookie objects
                for cookie in cookies_data:
                    self.session.cookies.set(
                        cookie.get('name', ''),
                        cookie.get('value', ''),
                        domain=cookie.get('domain', ''),
                        path=cookie.get('path', '/')
                    )
            elif isinstance(cookies_data, dict):
                # Simple dict format: {name: value}
                for name, value in cookies_data.items():
                    self.session.cookies.set(name, value, domain='.mass.gov')
            
            logger.info(f"Loaded cookies from {cookies_file}")
        except FileNotFoundError:
            logger.warning(f"Cookie file '{cookies_file}' not found - continuing without cookies")
        except Exception as e:
            logger.warning(f"Error loading cookies: {e} - continuing without cookies")
    
    def _load_cookies_to_selenium(self, cookies_file: str) -> None:
        """Load cookies from JSON file into Selenium driver."""
        if not self.driver:
            return
        
        try:
            import json
            with open(cookies_file, 'r') as f:
                cookies_data = json.load(f)
            
            # Navigate to domain first (required for setting cookies)
            self.driver.get("https://www.mass.gov")
            time.sleep(1)
            
            # Handle different cookie export formats
            if isinstance(cookies_data, list):
                for cookie in cookies_data:
                    try:
                        # Selenium cookie format
                        self.driver.add_cookie({
                            'name': cookie.get('name', ''),
                            'value': cookie.get('value', ''),
                            'domain': cookie.get('domain', '.mass.gov'),
                            'path': cookie.get('path', '/')
                        })
                    except Exception as e:
                        logger.debug(f"Could not add cookie {cookie.get('name', '')}: {e}")
            
            logger.info(f"Loaded cookies into Selenium from {cookies_file}")
        except Exception as e:
            logger.warning(f"Error loading cookies into Selenium: {e}")
    
    def __del__(self):
        """Clean up Selenium driver on exit."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        
    def get_page(self, url: str, retries: int = 3) -> Optional[BeautifulSoup]:
        """Fetch and parse a webpage, using Selenium if requests fail."""
        # Try Selenium first if enabled
        if self.use_selenium and self.driver:
            try:
                logger.info(f"Fetching with Selenium: {url}")
                self.driver.get(url)
                time.sleep(2)  # Wait for page to load
                html = self.driver.page_source
                time.sleep(self.delay)
                return BeautifulSoup(html, 'html.parser')
            except Exception as e:
                logger.warning(f"Selenium fetch failed: {e}, trying requests...")
        
        # Fallback to requests
        for attempt in range(retries):
            try:
                logger.info(f"Fetching: {url} (attempt {attempt + 1}/{retries})")
                response = self.session.get(url, timeout=30, allow_redirects=True)
                
                if response.status_code == 403:
                    logger.warning(f"403 Forbidden - website is blocking requests")
                    # If we get 403 and Selenium is available but not enabled, suggest using it
                    if SELENIUM_AVAILABLE and not self.use_selenium:
                        logger.warning("Consider using --selenium flag to bypass bot protection")
                    # Try Selenium as fallback if available
                    if SELENIUM_AVAILABLE and attempt == retries - 1:
                        logger.info("Attempting to use Selenium as fallback...")
                        try:
                            if not self.driver:
                                self._init_selenium()
                            if self.driver:
                                self.driver.get(url)
                                time.sleep(2)
                                html = self.driver.page_source
                                return BeautifulSoup(html, 'html.parser')
                        except Exception as e:
                            logger.error(f"Selenium fallback also failed: {e}")
                    
                    if attempt < retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                
                response.raise_for_status()
                time.sleep(self.delay)  # Be respectful to the server
                return BeautifulSoup(response.text, 'html.parser')
            except requests.RequestException as e:
                logger.error(f"Error fetching {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                return None
        return None
    
    def extract_chapter_links(self, soup: BeautifulSoup) -> List[str]:
        """
        Extract only building code chapter links (780-CMR chapters) from the TOC page.
        Filters out navigation pages and focuses on actual regulation chapters.
        
        Args:
            soup: BeautifulSoup object of the TOC page
            
        Returns:
            List of chapter URLs (only 780-CMR building code chapters)
        """
        chapter_links = []
        seen_urls = set()
        
        # Focus on links that are actual 780-CMR building code chapters
        # Pattern: URLs containing "780-CMR" or "regulations/780-CMR"
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True).lower()
            
            # Must be a 780-CMR chapter link
            is_building_code_chapter = (
                '780-cmr' in href.lower() or 
                '780-cmr' in text or
                (href.startswith('/regulations/') and 'chapter' in href.lower())
            )
            
            # Exclude navigation/topic pages
            is_not_navigation = not any(exclude in href.lower() for exclude in [
                '/topics/',
                '/massachusetts-state-organizations',
                '/info-details/',
                'massachusetts-topics'
            ])
            
            if is_building_code_chapter and is_not_navigation:
                full_url = urljoin(self.base_url, href)
                if full_url not in seen_urls and not href.startswith('#'):
                    chapter_links.append(full_url)
                    seen_urls.add(full_url)
                    logger.info(f"Found building code chapter: {text[:60]} -> {full_url}")
        
        logger.info(f"Total building code chapter links found: {len(chapter_links)}")
        return chapter_links
    
    def find_pdf_link(self, soup: BeautifulSoup, page_url: str) -> Optional[str]:
        """
        Find PDF download link on a chapter page.
        Mass.gov PDFs are at: https://www.mass.gov/doc/[chapter-name]/download
        """
        # Strategy 1: Look for links in "Downloads" section (most reliable)
        # Find sections with "Downloads" heading
        downloads_sections = []
        for heading in soup.find_all(['h2', 'h3', 'h4', 'h5'], string=re.compile(r'^downloads?$', re.I)):
            parent = heading.find_parent(['div', 'section', 'article'])
            if parent:
                downloads_sections.append(parent)
        
        # Also find divs/sections with download-related classes
        downloads_sections.extend(soup.find_all(['div', 'section', 'article'], 
                                               class_=lambda x: x and any(kw in str(x).lower() for kw in ['download', 'file', 'document'])))
        
        for downloads_section in downloads_sections:
            for link in downloads_section.find_all('a', href=True):
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()
                
                # Mass.gov PDF links are /doc/ URLs, often with /download at the end
                # Format: /doc/10th-edition-chapter-1-scope-and-administration-of-amendments/download
                is_doc_link = '/doc/' in href.lower()
                is_pdf_link = href.endswith('.pdf') or 'pdf' in href.lower() or '/download' in href.lower()
                
                # Look for chapter PDFs - check link text or href
                link_content = (text + ' ' + href.lower())
                if (is_doc_link or is_pdf_link) and \
                   any(keyword in link_content for keyword in ['chapter', '10th', 'edition', '780-cmr', 'scope', 'definitions', 'amendments']):
                    pdf_url = urljoin(page_url, href)
                    # Ensure /download is at the end for /doc/ URLs
                    if '/doc/' in pdf_url.lower() and not pdf_url.endswith('/download'):
                        if not pdf_url.endswith('.pdf'):
                            pdf_url = pdf_url.rstrip('/') + '/download'
                    logger.info(f"Found PDF link in Downloads section: {pdf_url}")
                    return pdf_url
        
        # Strategy 2: Look for any /doc/ links that might be PDFs
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True).lower()
            
            # Mass.gov document links: /doc/[name]/download
            if '/doc/' in href.lower():
                link_content = (text + ' ' + href.lower())
                # Check if it's related to building code/chapter
                if any(keyword in link_content for keyword in ['chapter', '10th', 'edition', '780-cmr', 'amendments']):
                    pdf_url = urljoin(page_url, href)
                    # Ensure /download is appended if not present
                    if '/doc/' in pdf_url.lower() and not pdf_url.endswith('/download') and not pdf_url.endswith('.pdf'):
                        pdf_url = pdf_url.rstrip('/') + '/download'
                    logger.info(f"Found /doc/ link: {text[:50]} -> {pdf_url}")
                    return pdf_url
        
        # Strategy 3: Look for links with "Open PDF" or "PDF" text
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True).lower()
            
            # Look for "open pdf" or "pdf" in link text
            if ('open pdf' in text or ('pdf' in text and 'file' in text)) and \
               ('/doc/' in href.lower() or href.endswith('.pdf') or '/download' in href.lower()):
                pdf_url = urljoin(page_url, href)
                if '/doc/' in pdf_url.lower() and not pdf_url.endswith('/download') and not pdf_url.endswith('.pdf'):
                    pdf_url = pdf_url.rstrip('/') + '/download'
                logger.info(f"Found PDF link by text: {text[:50]} -> {pdf_url}")
                return pdf_url
        
        # Strategy 4: Look for any PDF links (fallback)
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            if href.endswith('.pdf') or '/download' in href.lower():
                pdf_url = urljoin(page_url, href)
                logger.info(f"Found PDF link (fallback): {pdf_url}")
                return pdf_url
        
        return None
    
    def is_regulation_number(self, text: str) -> bool:
        """
        Check if text starts with a regulation number pattern (e.g., "101.1", "102.2.1").
        
        Args:
            text: Text to check
            
        Returns:
            True if text starts with a regulation number pattern
        """
        # Regulation number patterns:
        # - 101.1, 102.2.1, 201.3.4.5 (numbers with dots)
        # - Must start at beginning of line or after whitespace
        # - Usually followed by a space and then text
        pattern = r'^(\d{3,4}\.\d+(?:\.\d+)*(?:\.[A-Z])?)\s+'
        return bool(re.match(pattern, text.strip()))
    
    def extract_regulation_heading(self, text: str) -> Optional[str]:
        """
        Extract regulation number and heading from text (e.g., "101.1 Adoption and Title").
        
        Args:
            text: Text block to analyze
            
        Returns:
            Regulation heading (e.g., "101.1 Adoption and Title") or None
        """
        # Pattern: regulation number followed by heading text
        # Examples: "101.1 Adoption and Title", "102.2.1 Scope", "201.3.4.5 Requirements"
        pattern = r'^(\d{3,4}\.\d+(?:\.\d+)*(?:\.[A-Z])?)\s+([A-Z][^\n]{0,150})'
        match = re.match(pattern, text.strip())
        
        if match:
            reg_number = match.group(1)
            heading_text = match.group(2).strip()
            # Combine into full heading
            full_heading = f"{reg_number} {heading_text}"
            # Clean up (remove extra whitespace, limit length)
            full_heading = re.sub(r'\s+', ' ', full_heading)[:200]
            return full_heading
        
        return None
    
    def extract_regulation_paragraphs(self, text: str) -> List[tuple]:
        """
        Extract regulation paragraphs from PDF text using regulation number recognition.
        Returns list of (regulation_heading, paragraph_text) tuples.
        
        Args:
            text: Raw text from PDF page
            
        Returns:
            List of (heading, paragraph_text) tuples
        """
        paragraphs = []
        
        if not text:
            return paragraphs
        
        # Split text into lines
        lines = text.split('\n')
        
        current_regulation = None
        current_paragraph = []
        
        for line in lines:
            line = line.strip()
            if not line:
                # Empty line - if we have accumulated text, save it
                if current_paragraph and current_regulation:
                    para_text = ' '.join(current_paragraph).strip()
                    if len(para_text) > 30:  # Minimum meaningful paragraph length
                        paragraphs.append((current_regulation, para_text))
                    current_paragraph = []
                continue
            
            # Check if this line starts with a regulation number
            if self.is_regulation_number(line):
                # Save previous paragraph if exists
                if current_paragraph and current_regulation:
                    para_text = ' '.join(current_paragraph).strip()
                    if len(para_text) > 30:
                        paragraphs.append((current_regulation, para_text))
                
                # Extract new regulation heading
                reg_heading = self.extract_regulation_heading(line)
                if reg_heading:
                    current_regulation = reg_heading
                    # Get the text after the regulation number/heading
                    # Remove the regulation heading part to get just the paragraph text
                    remaining = re.sub(r'^\d{3,4}\.\d+(?:\.\d+)*(?:\.[A-Z])?\s+[A-Z][^\n]{0,150}\s*', '', line, count=1).strip()
                    current_paragraph = [remaining] if remaining else []
                else:
                    # Has regulation number but couldn't extract heading - use number as heading
                    match = re.match(r'^(\d{3,4}\.\d+(?:\.\d+)*(?:\.[A-Z])?)', line)
                    if match:
                        current_regulation = match.group(1)
                        remaining = line[len(match.group(1)):].strip()
                        current_paragraph = [remaining] if remaining else []
            else:
                # Regular text line - add to current paragraph
                if current_regulation:
                    current_paragraph.append(line)
        
        # Don't forget the last paragraph
        if current_paragraph and current_regulation:
            para_text = ' '.join(current_paragraph).strip()
            if len(para_text) > 30:
                paragraphs.append((current_regulation, para_text))
        
        return paragraphs
    
    def download_pdf_via_selenium(self, pdf_url: str, chapter_page_url: str) -> Optional[bytes]:
        """
        Download PDF by navigating to it with Selenium.
        Tries multiple methods: network interception, download folder, and requests with cookies.
        """
        if not self.use_selenium or not self.driver:
            return None
        
        import os
        import glob
        
        try:
            logger.info(f"Loading PDF via Selenium: {pdf_url}")
            
            # Method 1: Try network interception first
            self.driver.get(pdf_url)
            time.sleep(5)  # Wait for PDF to fully load and network requests to complete
            
            current_url = self.driver.current_url
            logger.info(f"Current URL after navigation: {current_url}")
            
            # Try to get PDF from performance logs
            try:
                logs = self.driver.get_log('performance')
                logger.info(f"Checking {len(logs)} performance log entries...")
                
                for log in logs:
                    try:
                        message = json.loads(log['message'])
                        method = message.get('message', {}).get('method', '')
                        
                        if method == 'Network.responseReceived':
                            response = message['message']['params']['response']
                            response_url = response.get('url', '')
                            mime_type = response.get('mimeType', '').lower()
                            
                            if 'pdf' in mime_type or '/doc/' in response_url or response_url.endswith('.pdf'):
                                request_id = message['message']['params']['requestId']
                                logger.info(f"Found PDF response: {response_url}")
                                
                                try:
                                    response_body = self.driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': request_id})
                                    if 'body' in response_body:
                                        import base64
                                        body = response_body['body']
                                        is_base64 = response_body.get('base64Encoded', False)
                                        
                                        if is_base64:
                                            pdf_content = base64.b64decode(body)
                                        else:
                                            try:
                                                pdf_content = base64.b64decode(body)
                                            except:
                                                pdf_content = body.encode('utf-8')
                                        
                                        if len(pdf_content) > 100 and pdf_content[:4] == b'%PDF':
                                            logger.info(f"✅ Successfully extracted PDF from network logs!")
                                            logger.info(f"   Size: {len(pdf_content)} bytes")
                                            return pdf_content
                                except Exception as e:
                                    logger.debug(f"CDP command failed: {e}")
                                    continue
                    except:
                        continue
            except Exception as e:
                logger.debug(f"Performance logs access failed: {e}")
            
            # Method 2: Check download folder
            download_dir = os.path.join(os.getcwd(), 'selenium_downloads')
            if os.path.exists(download_dir):
                # Look for recently downloaded PDF files
                pdf_files = glob.glob(os.path.join(download_dir, '*.pdf'))
                if pdf_files:
                    # Get most recently modified
                    latest_pdf = max(pdf_files, key=os.path.getmtime)
                    # Check if it was downloaded recently (within last 10 seconds)
                    if time.time() - os.path.getmtime(latest_pdf) < 10:
                        logger.info(f"Found PDF in download folder: {latest_pdf}")
                        with open(latest_pdf, 'rb') as f:
                            pdf_content = f.read()
                        if pdf_content[:4] == b'%PDF':
                            logger.info(f"✅ Successfully read PDF from download folder!")
                            logger.info(f"   Size: {len(pdf_content)} bytes")
                            return pdf_content
            
            # Method 3: Fallback to requests with Selenium cookies
            selenium_cookies = self.driver.get_cookies()
            temp_session = requests.Session()
            temp_session.headers.update(HEADERS)
            
            for cookie in selenium_cookies:
                temp_session.cookies.set(
                    cookie['name'],
                    cookie['value'],
                    domain=cookie.get('domain', ''),
                    path=cookie.get('path', '/')
                )
            
            for url_to_try in [current_url, pdf_url]:
                try:
                    response = temp_session.get(url_to_try, timeout=60, allow_redirects=True)
                    if response.status_code == 200:
                        content_type = response.headers.get('content-type', '').lower()
                        is_pdf_content = response.content[:4] == b'%PDF' if len(response.content) >= 4 else False
                        
                        if 'pdf' in content_type or is_pdf_content:
                            logger.info(f"✅ Successfully downloaded PDF via requests!")
                            logger.info(f"   Size: {len(response.content)} bytes")
                            return response.content
                except:
                    continue
            
        except Exception as e:
            logger.warning(f"Selenium PDF download failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        
        return None
        """
        Download PDF by navigating directly to PDF URL with Selenium.
        Uses Selenium's network logs to intercept the PDF response.
        """
        if not self.use_selenium or not self.driver:
            return None
        
        try:
            logger.info(f"Loading PDF via Selenium: {pdf_url}")
            
            # Navigate directly to PDF URL - Selenium will load it
            self.driver.get(pdf_url)
            time.sleep(5)  # Wait for PDF to fully load and network requests to complete
            
            # Get current URL (might have redirected)
            current_url = self.driver.current_url
            logger.info(f"Current URL after navigation: {current_url}")
            
            # Try to get PDF from performance logs (network interception)
            try:
                logs = self.driver.get_log('performance')
                logger.info(f"Checking {len(logs)} performance log entries...")
                
                for log in logs:
                    try:
                        message = json.loads(log['message'])
                        method = message.get('message', {}).get('method', '')
                        
                        if method == 'Network.responseReceived':
                            response = message['message']['params']['response']
                            response_url = response.get('url', '')
                            mime_type = response.get('mimeType', '').lower()
                            
                            # Check if this is a PDF response
                            if 'pdf' in mime_type or '/doc/' in response_url or response_url.endswith('.pdf'):
                                request_id = message['message']['params']['requestId']
                                logger.info(f"Found PDF response in network logs: {response_url}")
                                
                                # Get response body using CDP
                                try:
                                    logger.info(f"Attempting to get PDF body for request {request_id[:20]}...")
                                    response_body = self.driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': request_id})
                                    
                                    if 'body' in response_body:
                                        import base64
                                        body = response_body['body']
                                        is_base64 = response_body.get('base64Encoded', False)
                                        
                                        if is_base64:
                                            pdf_content = base64.b64decode(body)
                                        else:
                                            # Try to decode as base64 first, fallback to UTF-8
                                            try:
                                                pdf_content = base64.b64decode(body)
                                            except:
                                                pdf_content = body.encode('utf-8')
                                        
                                        # Verify it's a PDF
                                        if len(pdf_content) > 100 and pdf_content[:4] == b'%PDF':
                                            logger.info(f"✅ Successfully extracted PDF from network logs!")
                                            logger.info(f"   Size: {len(pdf_content)} bytes")
                                            return pdf_content
                                        else:
                                            logger.warning(f"Response body doesn't look like PDF (first bytes: {pdf_content[:20]})")
                                    else:
                                        logger.warning(f"No body in response: {response_body.keys()}")
                                except Exception as e:
                                    logger.warning(f"Could not get response body for {request_id[:20]}: {e}")
                                    import traceback
                                    logger.debug(traceback.format_exc())
                                    continue
                    except (KeyError, json.JSONDecodeError) as e:
                        continue
            except Exception as e:
                logger.debug(f"Could not access performance logs: {e}")
            
            # Fallback: Try with fresh cookies from Selenium session
            selenium_cookies = self.driver.get_cookies()
            temp_session = requests.Session()
            temp_session.headers.update(HEADERS)
            
            # Add all Selenium cookies
            for cookie in selenium_cookies:
                temp_session.cookies.set(
                    cookie['name'],
                    cookie['value'],
                    domain=cookie.get('domain', ''),
                    path=cookie.get('path', '/')
                )
            
            # Try downloading with fresh Selenium cookies
            for url_to_try in [current_url, pdf_url]:
                try:
                    logger.info(f"Attempting download from: {url_to_try}")
                    response = temp_session.get(url_to_try, timeout=60, allow_redirects=True)
                    
                    if response.status_code == 200:
                        # Check if it's PDF content
                        content_type = response.headers.get('content-type', '').lower()
                        is_pdf_content = response.content[:4] == b'%PDF' if len(response.content) >= 4 else False
                        
                        if 'pdf' in content_type or is_pdf_content:
                            logger.info(f"✅ Successfully downloaded PDF via Selenium!")
                            logger.info(f"   Content type: {content_type}")
                            logger.info(f"   Size: {len(response.content)} bytes")
                            return response.content
                        else:
                            logger.warning(f"Response is not PDF. Content type: {content_type}, Size: {len(response.content)}")
                    else:
                        logger.warning(f"Got status {response.status_code} for {url_to_try}")
                except Exception as e:
                    logger.warning(f"Error downloading from {url_to_try}: {e}")
                    continue
            
        except Exception as e:
            logger.warning(f"Selenium PDF download failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        
        return None
    
    def extract_pdf_paragraphs(self, pdf_url: str, chapter_name: str, chapter_page_url: Optional[str] = None) -> List[Dict]:
        """
        Extract regulation paragraphs from a PDF file using regulation number recognition.
        Only extracts actual regulation paragraphs (e.g., "101.1 Adoption and Title").
        
        Args:
            pdf_url: URL of the PDF file (may be /doc/ URL that redirects to PDF)
            chapter_name: Name/identifier of the chapter
            
        Returns:
            List of paragraph dictionaries with section_heading, paragraph_text, etc.
        """
        paragraphs = []
        
        try:
            logger.info(f"Downloading PDF: {pdf_url}")
            
            pdf_content = None
            
            # Try Selenium download first (most reliable)
            if self.use_selenium and self.driver and chapter_page_url:
                pdf_content = self.download_pdf_via_selenium(pdf_url, chapter_page_url)
            
            # Fallback to requests session with cookies
            response = None
            if pdf_content is None:
                # Use session with cookies (if loaded) to download PDF
                response = self.session.get(pdf_url, timeout=60, allow_redirects=True)
                
                # Check if we got blocked
                if response.status_code == 403:
                    logger.warning("403 Forbidden - PDF download blocked")
                    logger.warning("💡 Tip: Try using Selenium mode: python3 scraper.py --selenium --use-cookies")
                    raise requests.HTTPError(f"403 Forbidden - unable to download PDF")
                
                response.raise_for_status()
                pdf_content = response.content
            
            # Check content-type to verify it's a PDF (only if we have response object)
            if response and hasattr(response, 'headers'):
                content_type = response.headers.get('content-type', '').lower()
                if 'pdf' not in content_type:
                    logger.warning(f"Content-type is {content_type}, but attempting to parse as PDF anyway...")
            elif pdf_content:
                # If we got content from Selenium, verify it's PDF
                if pdf_content[:4] == b'%PDF':
                    logger.info("✅ PDF content obtained via Selenium - verified as PDF")
                else:
                    logger.warning(f"Content doesn't look like PDF (first bytes: {pdf_content[:20]})")
                    raise ValueError("Downloaded content is not a valid PDF")
            
            with pdfplumber.open(BytesIO(pdf_content)) as pdf:
                logger.info(f"PDF has {len(pdf.pages)} pages")
                
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        text = page.extract_text()
                        if not text:
                            continue
                        
                        # Extract regulation paragraphs using regulation recognition
                        reg_paragraphs = self.extract_regulation_paragraphs(text)
                        
                        for reg_heading, para_text in reg_paragraphs:
                            # Skip boilerplate/non-regulation text
                            # Filter out common non-regulation patterns
                            if any(skip in para_text.lower()[:100] for skip in [
                                'this is an unofficial version',
                                'commonwealth of massachusetts',
                                'page',
                                'table of contents',
                                'chapter',
                                'section',
                            ]):
                                continue
                            
                            paragraphs.append({
                                'id': self.paragraph_id,
                                'section_heading': reg_heading,
                                'paragraph_text': para_text,
                                'source_url': pdf_url,
                                'chapter': chapter_name,
                                'page_number': page_num,
                                'source_type': 'PDF'
                            })
                            self.paragraph_id += 1
                            
                    except Exception as e:
                        logger.warning(f"Error processing page {page_num}: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error extracting PDF {pdf_url}: {e}")
        
        logger.info(f"Extracted {len(paragraphs)} regulation paragraphs from PDF")
        return paragraphs
    
    def extract_html_section_heading(self, element) -> str:
        """
        Extract section heading from HTML element.
        Looks for h1-h6 tags or bold text that might be headings.
        
        Args:
            element: BeautifulSoup element to check
            
        Returns:
            Section heading or empty string
        """
        # Check if element itself is a heading
        if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            return element.get_text(strip=True)[:200]
        
        # Check for heading siblings before this element
        prev = element.find_previous(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        if prev:
            return prev.get_text(strip=True)[:200]
        
        # Check for bold text at start of element (might be inline heading)
        first_bold = element.find(['strong', 'b'])
        if first_bold:
            text = first_bold.get_text(strip=True)
            if len(text) < 100 and len(text) > 3:  # Reasonable heading length
                return text
        
        return ""
    
    def extract_html_paragraphs(self, soup: BeautifulSoup, page_url: str, chapter_name: str) -> List[Dict]:
        """
        Extract paragraphs from an HTML page at paragraph resolution.
        
        Args:
            soup: BeautifulSoup object of the page
            page_url: URL of the page
            chapter_name: Name/identifier of the chapter
            
        Returns:
            List of paragraph dictionaries with section_heading, paragraph_text, etc.
        """
        paragraphs = []
        current_section_heading = chapter_name  # Default to chapter name
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "header", "footer"]):
            script.decompose()
        
        # Find main content area
        content = soup.find(['main', 'article', 'div'], 
                          class_=re.compile(r'content|main|body|article', re.I))
        
        if not content:
            content = soup.find('body')
        
        if content:
            # Process content in order to maintain section heading context
            for element in content.find_all(['p', 'div', 'li'], recursive=True):
                # Check if this is a heading
                if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    current_section_heading = element.get_text(strip=True)[:200]
                    continue
                
                # Extract paragraph text
                text = element.get_text(separator=' ', strip=True)
                
                # Skip if too short or empty
                if not text or len(text) < 50:
                    continue
                
                # Check for section heading in this element or nearby
                section_heading = self.extract_html_section_heading(element)
                if section_heading:
                    current_section_heading = section_heading
                
                # If text is very long, split it into multiple paragraphs
                if len(text) > 1000:
                    para_list = self.split_into_paragraphs(text)
                else:
                    para_list = [text]
                
                for para in para_list:
                    if len(para) > 50:  # Minimum paragraph length
                        paragraphs.append({
                            'id': self.paragraph_id,
                            'section_heading': current_section_heading,
                            'paragraph_text': para,
                            'source_url': page_url,
                            'chapter': chapter_name,  # Keep for backward compatibility
                            'page_number': None,
                            'source_type': 'HTML'
                        })
                        self.paragraph_id += 1
        
        logger.info(f"Extracted {len(paragraphs)} paragraphs from HTML")
        return paragraphs
    
    def process_chapter(self, chapter_url: str) -> None:
        """
        Process a single chapter - ONLY extracts PDFs, skips HTML content.
        
        Args:
            chapter_url: URL of the chapter page
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing chapter: {chapter_url}")
        logger.info(f"{'='*60}")
        
        soup = self.get_page(chapter_url)
        if not soup:
            logger.warning(f"Could not fetch chapter: {chapter_url}")
            return
        
        # Extract chapter name from URL or page title
        chapter_name = urlparse(chapter_url).path.split('/')[-1] or "unknown"
        title = soup.find('title')
        if title:
            title_text = title.get_text(strip=True)
            # Extract chapter name from title (e.g., "780 CMR Tenth Edition, Chapter 1: ...")
            match = re.search(r'Chapter\s+(\d+[^\:]*?)(?:\:|$)', title_text, re.I)
            if match:
                chapter_name = f"Chapter {match.group(1).strip()}"
            else:
                chapter_name = title_text[:100]  # Limit length
        
        # ONLY look for PDF - skip HTML content
        pdf_link = self.find_pdf_link(soup, chapter_url)
        
        if pdf_link:
            logger.info(f"Found PDF link: {pdf_link}")
            paragraphs = self.extract_pdf_paragraphs(pdf_link, chapter_name, chapter_url)
            self.data.extend(paragraphs)
            logger.info(f"Total paragraphs collected so far: {len(self.data)}")
        else:
            logger.warning(f"No PDF found for chapter: {chapter_url} - skipping HTML content")
    
    def scrape_all(self) -> pd.DataFrame:
        """
        Scrape all chapters and return as DataFrame.
        
        Returns:
            DataFrame with all paragraphs
        """
        logger.info("Starting scraper...")
        logger.info(f"Base URL: {self.base_url}")
        
        # Get TOC page
        soup = self.get_page(self.base_url)
        if not soup:
            logger.error("Could not fetch TOC page!")
            return pd.DataFrame()
        
        # Extract chapter links
        chapter_links = self.extract_chapter_links(soup)
        
        if not chapter_links:
            logger.warning("No chapter links found! Trying alternative extraction...")
            # Fallback: try to find any links that might be chapters
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                if href and not href.startswith('#') and 'mass.gov' in href:
                    full_url = urljoin(self.base_url, href)
                    if full_url not in chapter_links:
                        chapter_links.append(full_url)
        
        logger.info(f"Found {len(chapter_links)} chapters to process")
        
        # Process each chapter
        for i, chapter_url in enumerate(chapter_links, 1):
            logger.info(f"\nProcessing chapter {i}/{len(chapter_links)}")
            try:
                self.process_chapter(chapter_url)
            except Exception as e:
                logger.error(f"Error processing chapter {chapter_url}: {e}")
                continue
        
        # Create DataFrame
        df = pd.DataFrame(self.data)
        logger.info(f"\n{'='*60}")
        logger.info(f"Scraping complete!")
        logger.info(f"Total paragraphs extracted: {len(df)}")
        logger.info(f"{'='*60}")
        
        return df
    
    def save_to_csv(self, df: pd.DataFrame, filename: str = "MA_Building_Code_Paragraphs.csv") -> None:
        """
        Save DataFrame to CSV file with proper column ordering for Mantis.
        
        Column order: id, section_heading, paragraph_text, source_url, (other metadata)
        """
        if df.empty:
            logger.warning("No data to save!")
            return
        
        # Define preferred column order for Mantis (matching user's specification)
        preferred_order = ['id', 'section_heading', 'paragraph_text', 'source_url']
        
        # Get all columns, prioritizing preferred order
        other_columns = [col for col in df.columns if col not in preferred_order]
        column_order = preferred_order + other_columns
        
        # Reorder DataFrame columns
        df_ordered = df[[col for col in column_order if col in df.columns]]
        
        df_ordered.to_csv(filename, index=False, encoding='utf-8')
        logger.info(f"Data saved to {filename}")
        logger.info(f"Columns (in order): {list(df_ordered.columns)}")
        logger.info(f"Shape: {df_ordered.shape}")
        logger.info(f"\n✅ CSV is ready for Mantis upload!")
        logger.info(f"   - Set 'paragraph_text' as Semantic field (required)")
        logger.info(f"   - Set 'section_heading' as Categoric field (optional)")
        logger.info(f"   - Set 'source_url' as Links field (optional)")


def main():
    """Main execution function."""
    import sys
    
    # Check if --selenium flag is provided
    use_selenium = '--selenium' in sys.argv or '-s' in sys.argv
    
    # Check for cookies file
    cookies_file = None
    if '--use-cookies' in sys.argv or '--cookies' in sys.argv:
        cookies_file = 'cookies.json'  # Default filename
        # Check if custom filename provided
        try:
            cookies_idx = sys.argv.index('--cookies-file')
            cookies_file = sys.argv[cookies_idx + 1]
        except (ValueError, IndexError):
            try:
                cookies_idx = sys.argv.index('--use-cookies')
                if cookies_idx + 1 < len(sys.argv) and not sys.argv[cookies_idx + 1].startswith('-'):
                    cookies_file = sys.argv[cookies_idx + 1]
            except (ValueError, IndexError):
                pass
    
    if use_selenium and not SELENIUM_AVAILABLE:
        print("❌ Selenium not available. Install with: pip install selenium webdriver-manager")
        print("   Falling back to requests-only mode...")
        use_selenium = False
    
    if cookies_file:
        print(f"📋 Using cookies from: {cookies_file}")
        print("   Make sure you've exported cookies after visiting mass.gov in your browser!")
    
    scraper = BuildingCodeScraper(delay=1.0, use_selenium=use_selenium, cookies_file=cookies_file)
    
    # Scrape all chapters
    df = scraper.scrape_all()
    
    # Save to CSV
    if not df.empty:
        scraper.save_to_csv(df, "MA_Building_Code_Paragraphs.csv")
        
        # Print summary
        print("\n" + "="*60)
        print("SCRAPING SUMMARY")
        print("="*60)
        print(f"Total paragraphs: {len(df)}")
        
        if 'chapter' in df.columns:
            print(f"\nChapters processed: {df['chapter'].nunique()}")
        if 'section_heading' in df.columns:
            print(f"Unique sections: {df['section_heading'].nunique()}")
        if 'source_type' in df.columns:
            print(f"\nSource types:")
            print(df['source_type'].value_counts())
        
        print(f"\nSample paragraphs (first 3):")
        display_cols = ['id', 'section_heading', 'paragraph_text']
        available_cols = [col for col in display_cols if col in df.columns]
        if available_cols:
            for idx, row in df[available_cols].head(3).iterrows():
                print(f"\n  Paragraph {row['id']}:")
                if 'section_heading' in row:
                    print(f"    Section: {row['section_heading'][:80]}...")
                print(f"    Text: {row['paragraph_text'][:150]}...")
        
        print("\n" + "="*60)
        print("✅ CSV file ready for Mantis upload!")
        print("="*60)
        print("\n📋 Mantis Upload Instructions:")
        print("1. Open Mantis and create a new space")
        print("2. Upload MA_Building_Code_Paragraphs.csv")
        print("3. Set 'paragraph_text' as the Semantic field (REQUIRED)")
        print("4. Set 'section_heading' as a Categoric field (optional)")
        print("5. Set 'source_url' as a Links field (optional)")
        print("\n⚠️  Important: 'paragraph_text' must be set as Semantic")
        print("   to prevent the error: 'At least one semantic or coordinate")
        print("   field is required'")
    else:
        print("❌ No data was scraped. Please check the logs for errors.")


if __name__ == "__main__":
    main()

