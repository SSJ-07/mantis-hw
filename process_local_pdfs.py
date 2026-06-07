"""
Process locally downloaded PDFs from Mass.gov building code chapters.
Use this if automated PDF downloads are blocked.

Instructions:
1. Manually download PDFs from each chapter page to a folder (e.g., ./pdfs/)
2. Name them descriptively (e.g., Chapter1.pdf, Chapter2.pdf)
3. Run this script to extract regulation paragraphs
"""

import os
import pdfplumber
import pandas as pd
import re
from pathlib import Path
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def is_regulation_number(text: str) -> bool:
    """Check if text starts with a regulation number pattern."""
    pattern = r'^(\d{3,4}\.\d+(?:\.\d+)*(?:\.[A-Z])?)\s+'
    return bool(re.match(pattern, text.strip()))

def extract_regulation_heading(text: str) -> Optional[str]:
    """Extract regulation number and heading from text."""
    pattern = r'^(\d{3,4}\.\d+(?:\.\d+)*(?:\.[A-Z])?)\s+([A-Z][^\n]{0,150})'
    match = re.match(pattern, text.strip())
    
    if match:
        reg_number = match.group(1)
        heading_text = match.group(2).strip()
        full_heading = f"{reg_number} {heading_text}"
        full_heading = re.sub(r'\s+', ' ', full_heading)[:200]
        return full_heading
    
    return None

def extract_regulation_paragraphs(text: str) -> List[tuple]:
    """Extract regulation paragraphs from PDF text."""
    paragraphs = []
    
    if not text:
        return paragraphs
    
    lines = text.split('\n')
    current_regulation = None
    current_paragraph = []
    
    for line in lines:
        line = line.strip()
        if not line:
            if current_paragraph and current_regulation:
                para_text = ' '.join(current_paragraph).strip()
                if len(para_text) > 30:
                    paragraphs.append((current_regulation, para_text))
                current_paragraph = []
            continue
        
        if is_regulation_number(line):
            if current_paragraph and current_regulation:
                para_text = ' '.join(current_paragraph).strip()
                if len(para_text) > 30:
                    paragraphs.append((current_regulation, para_text))
            
            reg_heading = extract_regulation_heading(line)
            if reg_heading:
                current_regulation = reg_heading
                remaining = re.sub(r'^\d{3,4}\.\d+(?:\.\d+)*(?:\.[A-Z])?\s+[A-Z][^\n]{0,150}\s*', '', line, count=1).strip()
                current_paragraph = [remaining] if remaining else []
            else:
                match = re.match(r'^(\d{3,4}\.\d+(?:\.\d+)*(?:\.[A-Z])?)', line)
                if match:
                    current_regulation = match.group(1)
                    remaining = line[len(match.group(1)):].strip()
                    current_paragraph = [remaining] if remaining else []
        else:
            if current_regulation:
                current_paragraph.append(line)
    
    if current_paragraph and current_regulation:
        para_text = ' '.join(current_paragraph).strip()
        if len(para_text) > 30:
            paragraphs.append((current_regulation, para_text))
    
    return paragraphs

def process_pdf_file(pdf_path: str, chapter_name: str) -> List[Dict]:
    """Process a single PDF file and extract regulation paragraphs."""
    paragraphs = []
    paragraph_id = 1
    
    try:
        logger.info(f"Processing PDF: {pdf_path}")
        
        with pdfplumber.open(pdf_path) as pdf:
            logger.info(f"PDF has {len(pdf.pages)} pages")
            
            for page_num, page in enumerate(pdf.pages, 1):
                try:
                    text = page.extract_text()
                    if not text:
                        continue
                    
                    reg_paragraphs = extract_regulation_paragraphs(text)
                    
                    for reg_heading, para_text in reg_paragraphs:
                        if any(skip in para_text.lower()[:100] for skip in [
                            'this is an unofficial version',
                            'commonwealth of massachusetts',
                            'page',
                            'table of contents',
                        ]):
                            continue
                        
                        paragraphs.append({
                            'id': paragraph_id,
                            'section_heading': reg_heading,
                            'paragraph_text': para_text,
                            'source_url': f'file://{os.path.abspath(pdf_path)}',
                            'chapter': chapter_name,
                            'page_number': page_num,
                            'source_type': 'PDF'
                        })
                        paragraph_id += 1
                        
                except Exception as e:
                    logger.warning(f"Error processing page {page_num}: {e}")
                    continue
        
        logger.info(f"Extracted {len(paragraphs)} regulation paragraphs from {pdf_path}")
        
    except Exception as e:
        logger.error(f"Error processing PDF {pdf_path}: {e}")
    
    return paragraphs

def process_pdf_directory(pdf_dir: str = "./pdfs") -> pd.DataFrame:
    """Process all PDFs in a directory."""
    pdf_dir_path = Path(pdf_dir)
    
    if not pdf_dir_path.exists():
        logger.error(f"PDF directory not found: {pdf_dir}")
        logger.info(f"Creating directory: {pdf_dir}")
        pdf_dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Please download PDFs to {pdf_dir} and run again")
        return pd.DataFrame()
    
    pdf_files = list(pdf_dir_path.glob("*.pdf"))
    
    if not pdf_files:
        logger.warning(f"No PDF files found in {pdf_dir}")
        logger.info("Please download PDFs from Mass.gov chapters to this directory")
        return pd.DataFrame()
    
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    
    all_paragraphs = []
    
    for pdf_file in sorted(pdf_files):
        # Extract chapter name from filename
        chapter_name = pdf_file.stem.replace('_', ' ').replace('-', ' ')
        
        paragraphs = process_pdf_file(str(pdf_file), chapter_name)
        all_paragraphs.extend(paragraphs)
    
    df = pd.DataFrame(all_paragraphs)
    logger.info(f"\nTotal paragraphs extracted: {len(df)}")
    
    return df

def main():
    """Main execution."""
    import sys
    
    pdf_dir = sys.argv[1] if len(sys.argv) > 1 else "./pdfs"
    
    print("="*60)
    print("PROCESSING LOCAL PDFs")
    print("="*60)
    print(f"\nLooking for PDFs in: {pdf_dir}")
    
    df = process_pdf_directory(pdf_dir)
    
    if not df.empty:
        output_file = "MA_Building_Code_Paragraphs.csv"
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"\n✅ CSV saved to: {output_file}")
        print(f"   Total paragraphs: {len(df)}")
        print(f"   Chapters processed: {df['chapter'].nunique()}")
        print("\n📋 Ready for Mantis upload!")
    else:
        print("\n❌ No data extracted. Make sure PDFs are in the directory.")

if __name__ == "__main__":
    main()

