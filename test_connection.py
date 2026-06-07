"""
Quick test script to check connectivity and page structure.
Run this first to debug any connection issues.
"""

import requests
from bs4 import BeautifulSoup
import json

BASE_URL = "https://www.mass.gov/handbook/tenth-edition-of-the-ma-state-building-code-780"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

def test_connection():
    """Test basic connectivity to the website."""
    print("="*60)
    print("Testing Connection to Mass.gov Building Code Handbook")
    print("="*60)
    
    try:
        print(f"\nFetching: {BASE_URL}")
        response = requests.get(BASE_URL, headers=HEADERS, timeout=30)
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response Headers:")
        for key, value in response.headers.items():
            if key.lower() in ['content-type', 'server', 'x-powered-by', 'set-cookie']:
                print(f"  {key}: {value}")
        
        if response.status_code == 200:
            print("\n✅ Successfully connected!")
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check page title
            title = soup.find('title')
            if title:
                print(f"\nPage Title: {title.get_text(strip=True)}")
            
            # Count links
            all_links = soup.find_all('a', href=True)
            print(f"\nTotal links found: {len(all_links)}")
            
            # Find potential chapter links
            chapter_keywords = ['chapter', 'section', 'part', 'appendix']
            chapter_links = []
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()
                if any(kw in text for kw in chapter_keywords) or any(kw in href.lower() for kw in chapter_keywords):
                    chapter_links.append({
                        'text': link.get_text(strip=True)[:50],
                        'href': href
                    })
            
            print(f"\nPotential chapter links found: {len(chapter_links)}")
            if chapter_links:
                print("\nSample chapter links:")
                for i, link in enumerate(chapter_links[:10], 1):
                    print(f"  {i}. {link['text']} -> {link['href']}")
            
            # Check for PDF links
            pdf_links = [a for a in all_links if a.get('href', '').endswith('.pdf')]
            print(f"\nPDF links found: {len(pdf_links)}")
            if pdf_links:
                print("\nSample PDF links:")
                for i, link in enumerate(pdf_links[:5], 1):
                    print(f"  {i}. {link.get_text(strip=True)[:50]} -> {link.get('href')}")
            
            # Save HTML for inspection
            with open('debug_page.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            print("\n✅ Saved page HTML to 'debug_page.html' for inspection")
            
        elif response.status_code == 403:
            print("\n❌ 403 Forbidden - Website is blocking the request")
            print("\nPossible solutions:")
            print("  1. The website may require JavaScript rendering (use Selenium)")
            print("  2. Try increasing delay between requests")
            print("  3. Check if the website has changed its structure")
            print("  4. Try accessing the URL manually in a browser")
            
        else:
            print(f"\n❌ Unexpected status code: {response.status_code}")
            print(f"Response preview: {response.text[:500]}")
            
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Connection error: {e}")
        print("\nPossible issues:")
        print("  1. No internet connection")
        print("  2. Website is down")
        print("  3. Firewall/proxy blocking the request")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    test_connection()

