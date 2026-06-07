# Massachusetts State Building Code Scraper

This scraper extracts all rules and regulations from the [10th Edition of the MA State Building Code](https://www.mass.gov/handbook/tenth-edition-of-the-ma-state-building-code-780) at paragraph resolution for Mantis space creation.

## Features

- ✅ Scrapes Table of Contents page to find all chapters
- ✅ Handles both PDF and HTML chapter formats
- ✅ Extracts paragraphs with proper text cleaning
- ✅ Exports to CSV format ready for Mantis upload
- ✅ Includes error handling and logging
- ✅ Respectful rate limiting (1 second delay between requests)

## Installation

1. Install Python dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Reproducible pipeline

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Test connectivity
python test_connection.py

# 3. Download chapter PDFs (requires Chrome; see README_COOKIES.md)
python scraper.py --selenium --use-cookies

# 4. Extract paragraphs from downloaded PDFs (recommended)
python extract_pdf_data.py ./selenium_downloads ./MA_Building_Code_Paragraphs.csv
```

**Alternative:** If automated downloads are blocked, manually download PDFs to a folder and run either:
- `python extract_pdf_data.py ./pdfs` (full metadata), or
- `python process_local_pdfs.py ./pdfs` (simpler output)

See `README_COOKIES.md` and `README_LOCAL_PDFS.md` for details.

### Step 1: Test Connection (Recommended)

First, test if you can connect to the website:

```bash
python test_connection.py
```

This will:
- Check connectivity
- Show page structure
- Identify potential chapter links
- Save a debug HTML file for inspection

### Step 3: Extract Paragraphs (Recommended)

The scraper downloads PDFs to `selenium_downloads/`. For best results, run the dedicated extractor:

```bash
python extract_pdf_data.py ./selenium_downloads ./MA_Building_Code_Paragraphs.csv
```

This produces a richer CSV (regulation numbers, code type, PART/SECTION hierarchy) with text sanitization for Mantis embedding.

### Step 2 (legacy): Run the Scraper end-to-end

Once connectivity is confirmed, run the main scraper:

```bash
python scraper.py
```

The script will:
1. Fetch the Table of Contents page
2. Extract all chapter links
3. Process each chapter (PDF or HTML)
4. Extract paragraphs from each chapter
5. Save to `MA_Building_Code_Paragraphs.csv`

## Output Format

The CSV file is structured for **paragraph resolution** - each row represents one individual paragraph. The columns are:

### Primary Columns (for Mantis):
- `id`: Unique paragraph identifier
- `section_heading`: Section/chapter heading (e.g., "Section 1.2 Fire Safety", "Chapter 3")
- `paragraph_text`: **The actual paragraph text** - this is your semantic field for Mantis
- `source_url`: Source URL (PDF or HTML page)

### Additional Metadata:
- `chapter`: Chapter name/identifier (for backward compatibility)
- `page_number`: Page number (for PDFs, None for HTML)
- `source_type`: Either "PDF" or "HTML"

### Example CSV Structure:

```csv
id,section_heading,paragraph_text,source_url,chapter,page_number,source_type
1,Section 1.2 Fire Safety,Every room must have at least one smoke detector installed...,https://mass.gov/.../chapter-1,Chapter 1,5,PDF
2,Section 1.2 Fire Safety,Detectors must be interconnected across rooms...,https://mass.gov/.../chapter-1,Chapter 1,5,PDF
3,Section 2.1 Electrical Code,Outlets must be grounded to prevent electrical hazards...,https://mass.gov/.../chapter-2,Chapter 2,12,PDF
```

**Key Point**: Each paragraph is a separate row, allowing Mantis to:
- Create individual embeddings for each paragraph
- Cluster similar paragraphs across different sections
- Enable fine-grained semantic search and visualization

## Mantis Upload Instructions

### Step-by-Step Upload:

1. **Open Mantis** and create a new space
2. **Upload** `MA_Building_Code_Paragraphs.csv`
3. **Configure column types**:
   - ✅ **`paragraph_text`** → Set as **Semantic** (REQUIRED - this prevents the error: *"At least one semantic or coordinate field is required"*)
   - 📊 **`section_heading`** → Set as **Categoric** (optional - for filtering/grouping)
   - 🔗 **`source_url`** → Set as **Links** (optional - for linking back to source)
   - 🆔 **`id`** → Leave as **Unused** or set as **ID**
   - Other columns → Set as **Unused** or **Categoric** as needed

4. **Enable text embedding** for semantic search
5. **Upload and visualize** your paragraph-resolution cognitive map!

### Why Paragraph Resolution?

Instead of embedding entire documents or sections as single points, paragraph resolution means:
- **More granular insights**: Each paragraph gets its own embedding and position
- **Finer clustering**: Similar regulatory topics cluster together across different sections
- **Better search**: Find specific requirements even within large documents
- **Detailed visualization**: Zoom into specific subthemes and relationships

For example, all fire safety paragraphs from different chapters will cluster together, even if they're in separate sections of the building code.

## Architecture

```
TOC Page (Base URL)
   ↓
Extract Chapter Links
   ↓
For Each Chapter:
   ├─→ Check for PDF link
   │   └─→ Download & Extract with pdfplumber
   │
   └─→ If no PDF, parse HTML
       └─→ Extract paragraphs with BeautifulSoup
   ↓
Split into Paragraphs
   ↓
Save to CSV
   ↓
Ready for Mantis Upload
```

## Customization

You can customize the scraper by modifying these parameters in `scraper.py`:

- `delay`: Time between requests (default: 1.0 seconds)
- `BASE_URL`: The handbook URL
- Minimum paragraph length: Currently set to 50 characters

## Troubleshooting

### 403 Forbidden Errors
If you encounter 403 errors, the website may be blocking automated requests. Try:
- Increase the `delay` parameter to 2-3 seconds
- Run the scraper during off-peak hours
- Use a VPN or different network
- Consider using Selenium with a real browser (see Alternative Methods below)

### No chapters found
- The website structure may have changed
- Check the logs for extraction details
- You may need to adjust the link detection patterns in `extract_chapter_links()`
- Try manually inspecting the page HTML to understand the structure

### PDF extraction issues
- Ensure `pdfplumber` is properly installed
- Some PDFs may be encrypted or have unusual formatting
- Check logs for specific error messages
- Verify PDF URLs are accessible manually

### Rate limiting
- If you get blocked, increase the `delay` parameter
- The default 1 second delay should be respectful
- Consider adding exponential backoff for retries

### Alternative Methods
If the standard scraper doesn't work due to bot protection:
1. **Selenium**: Use a headless browser to render JavaScript
2. **Manual download**: Download PDFs manually and use a separate script to extract paragraphs
3. **API**: Check if Mass.gov provides an API for accessing this content

## Dependencies

- `requests`: HTTP library for fetching web pages
- `beautifulsoup4`: HTML parsing
- `pandas`: Data manipulation and CSV export
- `pdfplumber`: PDF text extraction
- `lxml`: Fast HTML/XML parser

## License

This scraper is provided as-is for educational and research purposes. Please respect the website's terms of service and robots.txt when scraping.

