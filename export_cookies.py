"""
Helper script to export browser cookies for use with the scraper.
Run this after you've visited mass.gov in your browser.
"""

import json
import sys

def export_chrome_cookies():
    """Instructions for exporting Chrome cookies."""
    print("="*60)
    print("EXPORTING CHROME COOKIES")
    print("="*60)
    print("\nMethod 1: Using browser extension (easiest)")
    print("1. Install 'Cookie-Editor' extension for Chrome")
    print("2. Visit: https://www.mass.gov/handbook/tenth-edition-of-the-ma-state-building-code-780")
    print("3. Click Cookie-Editor icon → Export → JSON")
    print("4. Save as 'cookies.json' in this directory")
    print("\nMethod 2: Using browser developer tools")
    print("1. Visit mass.gov in Chrome")
    print("2. Open DevTools (F12) → Application → Cookies")
    print("3. Copy cookies manually (tedious)")
    print("\n" + "="*60)

def export_firefox_cookies():
    """Instructions for exporting Firefox cookies."""
    print("="*60)
    print("EXPORTING FIREFOX COOKIES")
    print("="*60)
    print("\n1. Install 'Cookie-Editor' extension for Firefox")
    print("2. Visit: https://www.mass.gov/handbook/tenth-edition-of-the-ma-state-building-code-780")
    print("3. Click Cookie-Editor icon → Export → JSON")
    print("4. Save as 'cookies.json' in this directory")
    print("\n" + "="*60)

def load_cookies_from_file(filename='cookies.json'):
    """Load cookies from JSON file."""
    try:
        with open(filename, 'r') as f:
            cookies_data = json.load(f)
        return cookies_data
    except FileNotFoundError:
        print(f"❌ Cookie file '{filename}' not found!")
        print("\nPlease export your cookies first using one of the methods above.")
        return None
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON in '{filename}'!")
        return None

if __name__ == "__main__":
    print("\nChoose your browser:")
    print("1. Chrome")
    print("2. Firefox")
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == "1":
        export_chrome_cookies()
    elif choice == "2":
        export_firefox_cookies()
    else:
        print("Invalid choice!")
        sys.exit(1)
    
    print("\nAfter exporting cookies to 'cookies.json',")
    print("run the scraper with: python3 scraper.py --selenium --use-cookies")

