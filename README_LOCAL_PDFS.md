# Processing Locally Downloaded PDFs

Since Mass.gov has strict bot protection, you can manually download PDFs and process them locally.

## Quick Start

### Step 1: Download PDFs

1. Visit: https://www.mass.gov/handbook/tenth-edition-of-the-ma-state-building-code-780
2. For each chapter:
   - Click the chapter link
   - Click the PDF download button
   - Save to a folder (e.g., `./pdfs/`)
   - Name them descriptively: `Chapter1.pdf`, `Chapter2.pdf`, etc.

### Step 2: Process PDFs

```bash
python3 process_local_pdfs.py ./pdfs
```

This will:
- ✅ Extract regulation paragraphs from all PDFs
- ✅ Use regulation number recognition (101.1, 102.2.1, etc.)
- ✅ Generate `MA_Building_Code_Paragraphs.csv`
- ✅ Ready for Mantis upload

## Faster: Bulk Download with Browser Extension

**Using DownThemAll (Firefox) or Chrono (Chrome):**

1. Install extension
2. Visit the handbook TOC page
3. Right-click → "Download all links"
4. Filter by: `/doc/.*download`
5. Download all PDFs at once
6. Process with the script

## Output

The script generates `MA_Building_Code_Paragraphs.csv` with:
- `id`: Unique paragraph ID
- `section_heading`: Regulation number + heading (e.g., "101.1 Adoption and Title")
- `paragraph_text`: Full paragraph text
- `source_url`: File path
- `chapter`: Chapter name
- `page_number`: Page number in PDF
- `source_type`: "PDF"

Ready for Mantis upload! 🚀

