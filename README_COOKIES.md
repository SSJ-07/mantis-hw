# Using Browser Cookies for PDF Downloads

Mass.gov blocks automated PDF downloads, but you can use your browser's authenticated session to download PDFs legally.

## Quick Start

### Step 1: Export Cookies from Your Browser

**Using Cookie-Editor Extension (Recommended):**

1. Install [Cookie-Editor](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm) (Chrome) or [Cookie-Editor](https://addons.mozilla.org/en-US/firefox/addon/cookie-editor/) (Firefox)

2. Visit Mass.gov in your browser:
   ```
   https://www.mass.gov/handbook/tenth-edition-of-the-ma-state-building-code-780
   ```

3. Click the Cookie-Editor extension icon

4. Click **Export** → **JSON**

5. Save the file as `cookies.json` in this directory

### Step 2: Run the Scraper with Cookies

```bash
python3 scraper.py --selenium --use-cookies
```

The scraper will:
- ✅ Use your browser cookies for authenticated requests
- ✅ Download PDFs using your session
- ✅ Extract regulation paragraphs from PDFs
- ✅ Generate CSV for Mantis

## Alternative: Manual Cookie Export

If you prefer not to use an extension:

1. Visit mass.gov in your browser
2. Open Developer Tools (F12)
3. Go to Application → Cookies → https://www.mass.gov
4. Copy relevant cookies manually (more tedious)

## How It Works

When you visit mass.gov in your browser, it sets cookies that identify your session. By exporting these cookies and using them in the scraper, you're using your own authenticated session - not bypassing security, just reusing your authorized access.

This is:
- ✅ Legal (using your own session)
- ✅ Ethical (not bypassing security)
- ✅ Reliable (works like your browser)

## Troubleshooting

**403 Forbidden errors:**
- Make sure you exported cookies AFTER visiting mass.gov
- Cookies may expire - re-export if needed
- Try visiting a chapter page before exporting cookies

**No cookies found:**
- Make sure `cookies.json` is in the same directory as `scraper.py`
- Check that the JSON file is valid

**PDFs still not downloading:**
- Try using Selenium mode: `python3 scraper.py --selenium --use-cookies`
- Make sure cookies include session cookies (not just preference cookies)

