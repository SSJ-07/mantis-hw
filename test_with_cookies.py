"""
Test script to verify cookie-based PDF downloading works.
"""

from scraper import BuildingCodeScraper
import logging
import os
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_pdf_download_with_cookies():
    """Test PDF download with cookies."""
    
    cookies_file = 'cookies.json'
    
    if not os.path.exists(cookies_file):
        print("="*60)
        print("❌ cookies.json not found!")
        print("="*60)
        print("\n📋 To export cookies:")
        print("1. Install Cookie-Editor extension in your browser")
        print("2. Visit: https://www.mass.gov/handbook/tenth-edition-of-the-ma-state-building-code-780")
        print("3. Click Cookie-Editor icon → Export → JSON")
        print("4. Save as 'cookies.json' in this directory")
        print("\nThen run this test again.")
        return
    
    print("="*60)
    print("TESTING PDF DOWNLOAD WITH COOKIES")
    print("="*60)
    print(f"✅ Found cookies.json")
    
    # Test with a single chapter
    test_url = "https://www.mass.gov/regulations/780-CMR-tenth-edition-chapter-1-scope-and-administration-of-amendments"
    
    # Try with visible browser first (non-headless) - better for bot protection
    scraper = BuildingCodeScraper(use_selenium=True, delay=1.0, cookies_file=cookies_file, headless=False)
    
    logger.info(f"Testing chapter: {test_url}")
    
    # First, navigate to mass.gov with Selenium to establish session
    if scraper.use_selenium and scraper.driver:
        logger.info("Establishing session by visiting mass.gov...")
        scraper.driver.get("https://www.mass.gov")
        time.sleep(2)
        scraper.driver.get("https://www.mass.gov/handbook/tenth-edition-of-the-ma-state-building-code-780")
        time.sleep(2)
        # Get fresh cookies from Selenium session
        selenium_cookies = scraper.driver.get_cookies()
        # Update requests session with fresh cookies
        scraper.session.cookies.clear()
        for cookie in selenium_cookies:
            scraper.session.cookies.set(
                cookie['name'],
                cookie['value'],
                domain=cookie.get('domain', ''),
                path=cookie.get('path', '/')
            )
        logger.info(f"Updated session with {len(selenium_cookies)} cookies from Selenium")
    
    # Get the page
    soup = scraper.get_page(test_url)
    if not soup:
        logger.error("Failed to fetch page!")
        return
    
    # Find PDF link
    pdf_link = scraper.find_pdf_link(soup, test_url)
    
    if pdf_link:
        logger.info(f"✅ Found PDF link: {pdf_link}")
        
        # Try to download PDF
        logger.info("\nAttempting to download PDF with cookies...")
        chapter_name = "Chapter 1: Scope and Administration of Amendments"
        
        try:
            paragraphs = scraper.extract_pdf_paragraphs(pdf_link, chapter_name, test_url)
            logger.info(f"\n✅ SUCCESS! Extracted {len(paragraphs)} regulation paragraphs")
            
            if paragraphs:
                logger.info("\nSample paragraphs (first 3):")
                for i, para in enumerate(paragraphs[:3], 1):
                    logger.info(f"\n  Paragraph {i}:")
                    logger.info(f"    Section: {para['section_heading']}")
                    logger.info(f"    Text: {para['paragraph_text'][:150]}...")
        except Exception as e:
            logger.error(f"\n❌ Failed to download PDF: {e}")
            logger.info("\n💡 Make sure:")
            logger.info("   - Cookies were exported AFTER visiting mass.gov")
            logger.info("   - cookies.json is valid JSON")
            logger.info("   - Your browser session is still active")
    else:
        logger.error("❌ No PDF link found!")
    
    # Cleanup
    if scraper.driver:
        scraper.driver.quit()
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    test_pdf_download_with_cookies()

