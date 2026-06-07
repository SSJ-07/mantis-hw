"""
Extract regulation paragraphs from downloaded building code PDFs and export CSV for Mantis.

Run this after scraper.py (or manual PDF download) to produce the final dataset.
Includes text sanitization and filtering to prevent Mantis embedding errors.

Usage:
    python extract_pdf_data.py [pdf_directory] [output_csv]

Example:
    python extract_pdf_data.py ./selenium_downloads ./MA_Building_Code_Paragraphs.csv
"""

import os
import pdfplumber
import pandas as pd
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Map PDF filenames to chapter names and source URLs
CHAPTER_MAPPING = {
    '10th-Edition-Chapter-1-Scope-and-Administration-of-Amendments.pdf': {
        'chapter': 'Chapter 1',
        'url': 'https://www.mass.gov/doc/10th-edition-chapter-1-scope-and-administration-of-amendments/download',
        'order': 1
    },
    '10th-Edition-Chapter-2-Definitions.pdf': {
        'chapter': 'Chapter 2',
        'url': 'https://www.mass.gov/doc/chapter-2-definitions/download',
        'order': 2
    },
    '10th-Edition-Chapter-3-Use-and-Occupancy-Classification.pdf': {
        'chapter': 'Chapter 3',
        'url': 'https://www.mass.gov/doc/10th-edition-chapter-3-use-and-occupancy-classification/download',
        'order': 3
    },
    '10th-Edition-Chapter-4-Special-Detailed-Requirements-Based-On-Use-and-Occupancy.pdf': {
        'chapter': 'Chapter 4',
        'url': 'https://www.mass.gov/doc/10th-edition-chapter-4-special-detailed-requirements-based-on-use-and-occupancy/download',
        'order': 4
    },
}

def extract_chapter_number(filename: str) -> int:
    """Extract chapter number from filename for sorting."""
    # Check if in mapping first
    if filename in CHAPTER_MAPPING:
        return CHAPTER_MAPPING[filename].get('order', 9999)
    
    # Prioritize main building code chapters (10th-Edition-Chapter-X) over residential
    is_main_chapter = '10th-Edition-Chapter-' in filename and 'Residential' not in filename
    is_residential = '10th-Edition-Residential-Chapter-' in filename or 'Residential-Chapter-' in filename
    
    # Pattern: Chapter-X (main chapters)
    match = re.search(r'Chapter-(\d+)', filename, re.IGNORECASE)
    if match:
        num = int(match.group(1))
        if is_main_chapter:
            # Main chapters: 1-35 come first
            return num
        elif is_residential:
            # Residential chapters: after main chapters
            return 1000 + num
        elif num >= 110:
            # Special chapters (110.R1, etc.): after residential
            return 2000 + num
        return num
    
    # Default: put at end, but main chapters before residential
    if is_main_chapter:
        return 100
    elif is_residential:
        return 2000
    return 9999

def get_chapter_info(pdf_filename: str) -> Dict[str, str]:
    """Get chapter name, URL, and code type from PDF filename."""
    # Standardize code_type: Base, Residential, Fire, Specialized
    if "Residential" in pdf_filename:
        code_type = "Residential"
    elif "Fire" in pdf_filename:
        code_type = "Fire"
    elif any(x in pdf_filename for x in ["110.R", "Special", "Appendix"]):
        code_type = "Specialized"
    else:
        code_type = "Base"
    
    if pdf_filename in CHAPTER_MAPPING:
        info = CHAPTER_MAPPING[pdf_filename].copy()
        info.pop('order', None)  # Remove order from return value
        info['code_type'] = code_type
        return info
    
    # Try to extract from filename pattern
    match = re.search(r'Chapter-(\d+(?:\.\d+)?(?:\.R\d+)?)', pdf_filename, re.IGNORECASE)
    if match:
        chapter_num = match.group(1)
        # Generate URL pattern
        url_slug = pdf_filename.replace('.pdf', '').replace('10th-Edition-', '').lower()
        url_slug = re.sub(r'[^\w-]', '-', url_slug)
        url_slug = re.sub(r'-+', '-', url_slug)
        
        return {
            'chapter': f'Chapter {chapter_num}',
            'url': f'https://www.mass.gov/doc/{url_slug}/download',
            'code_type': code_type
        }
    
    # Fallback
    chapter_name = Path(pdf_filename).stem.replace('_', ' ').replace('-', ' ')
    return {
        'chapter': chapter_name,
        'url': f'file://{pdf_filename}',
        'code_type': code_type
    }

def is_part_heading(text: str) -> bool:
    """Check if text is a PART heading (e.g., "PART 1 - SCOPE AND APPLICATION")."""
    pattern = r'^PART\s+\d+\s*[-–]\s*[A-Z]'
    return bool(re.match(pattern, text.strip(), re.IGNORECASE))

def is_section_heading(text: str) -> bool:
    """Check if text is a SECTION heading (e.g., "SECTION 101 GENERAL")."""
    pattern = r'^SECTION\s+\d{3,4}\s+[A-Z]'
    return bool(re.match(pattern, text.strip(), re.IGNORECASE))

def extract_part_heading(text: str) -> Optional[str]:
    """Extract PART heading text."""
    # Pattern: "PART 1 - SCOPE AND APPLICATION" or "PART 1 – SCOPE AND APPLICATION"
    pattern = r'^PART\s+(\d+)\s*[-–]\s*(.+)'
    match = re.match(pattern, text.strip(), re.IGNORECASE)
    if match:
        part_num = match.group(1)
        part_title = match.group(2).strip()
        return f"PART {part_num} - {part_title}"
    return None

def extract_section_heading_text(text: str) -> Optional[str]:
    """Extract SECTION heading text."""
    # Pattern: "SECTION 101 GENERAL"
    pattern = r'^SECTION\s+(\d{3,4})\s+(.+)'
    match = re.match(pattern, text.strip(), re.IGNORECASE)
    if match:
        section_num = match.group(1)
        section_title = match.group(2).strip()
        return f"SECTION {section_num} {section_title}"
    return None

def extract_source_modifier(text: str) -> Optional[str]:
    """Extract source modifier like [F] from regulation text."""
    # Pattern: [F], [BS], etc.
    match = re.search(r'^\[([A-Z]+)\]', text.strip())
    if match:
        return match.group(1)
    return None

def sanitize_text(text: str) -> str:
    """
    Sanitize text to remove invisible/control characters that can break embeddings.
    Removes null bytes, control characters, and other problematic unicode.
    """
    if not text or not isinstance(text, str):
        return ''
    
    # Remove null bytes and control characters (0x00-0x1F, 0x7F)
    # Keep newlines (0x0A), carriage returns (0x0D), and tabs (0x09) as they're useful
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    # Remove other problematic unicode characters
    # Remove zero-width spaces, zero-width non-joiners, etc.
    text = text.replace('\u200B', '')  # Zero-width space
    text = text.replace('\u200C', '')  # Zero-width non-joiner
    text = text.replace('\u200D', '')  # Zero-width joiner
    text = text.replace('\uFEFF', '')  # Zero-width no-break space (BOM)
    
    # Normalize whitespace (replace multiple spaces/tabs with single space)
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    return text

def normalize_quotes(text: str) -> str:
    """Normalize smart quotes to ASCII quotes."""
    if not text:
        return ''
    # Replace typographic quotes with ASCII quotes
    # Unicode left double quote (U+201C) and right double quote (U+201D) -> straight quote (")
    text = text.replace('\u201C', '"').replace('\u201D', '"')
    # Unicode left single quote (U+2018) and right single quote (U+2019) -> straight quote (')
    text = text.replace('\u2018', "'").replace('\u2019', "'")
    # Also handle other quote variants
    text = text.replace('"', '"').replace('"', '"')  # Fallback for other encodings
    text = text.replace(''', "'").replace(''', "'")  # Fallback for other encodings
    return text

def clean_boilerplate(text: str) -> str:
    """Remove boilerplate pollution from paragraph text."""
    if not text:
        return ''
    
    # Remove sentences containing boilerplate phrases
    sentences = re.split(r'([.!?]\s+)', text)
    cleaned_sentences = []
    
    boilerplate_phrases = [
        'this is an unofficial copy',
        'official copies must be obtained',
        'commonwealth of massachusetts',
        'secretary of the commonwealth',
    ]
    
    for i in range(0, len(sentences), 2):
        if i < len(sentences):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]
            
            # Check if sentence contains boilerplate
            sentence_lower = sentence.lower()
            is_boilerplate = any(phrase in sentence_lower for phrase in boilerplate_phrases)
            
            if not is_boilerplate:
                cleaned_sentences.append(sentence)
    
    return ''.join(cleaned_sentences).strip()

# Updated to handle both standard sections and Residential sections (R-prefixed)
def is_regulation_number(text: str) -> bool:
    """Check if text starts with a regulation number pattern."""
    text = text.strip()
    
    # Pattern 1: Standard format with space (e.g., "101.1 Adoption")
    pattern1 = r'^(\d{3,4}\.\d+(?:\.\d+)*(?:\.[A-Z])?)\s+'
    if re.match(pattern1, text):
        return True
    
    # Pattern 2: Format with period then space (e.g., "304.1. Replace")
    pattern2 = r'^(\d{3,4}\.\d+(?:\.\d+)*(?:\.[A-Z])?)\.\s+'
    if re.match(pattern2, text):
        return True
    
    # Pattern 3: Residential format (e.g., "R101.4.2", "R702")
    pattern3 = r'^(R\d{1,4}\.\d+(?:\.\d+)*(?:\.[A-Z])?)\s+'
    if re.match(pattern3, text):
        return True
    
    # Pattern 4: Residential format with period (e.g., "R101.4.2.")
    pattern4 = r'^(R\d{1,4}\.\d+(?:\.\d+)*(?:\.[A-Z])?)\.\s+'
    return bool(re.match(pattern4, text))

def extract_regulation_number_and_heading(text: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extract regulation number, heading title, and source modifier from text.
    Returns (regulation_number, heading_title, source_modifier).
    Example: "[F] 307.1.1 Uses other than Group H." -> ("307.1.1", "Uses other than Group H", "F")
    """
    text = text.strip()
    source_modifier = extract_source_modifier(text)
    
    # Remove source modifier from text if present
    if source_modifier:
        text = re.sub(r'^\[[A-Z]+\]\s+', '', text)
    
    # Pattern 1: Standard format (e.g., "101.1 Adoption and Title. The Board...")
    pattern1 = r'^(\d{3,4}\.\d+(?:\.\d+)*(?:\.[A-Z])?)\s+([A-Z][^.]*?\.)'
    match = re.match(pattern1, text)
    
    if match:
        reg_number = match.group(1)
        heading_text = match.group(2).strip()
        # Remove trailing period from heading title
        heading_text = heading_text.rstrip('.')
        return reg_number, heading_text, source_modifier
    
    # Pattern 2: Format with period (e.g., "304.1. Replace...")
    pattern2 = r'^(\d{3,4}\.\d+(?:\.\d+)*(?:\.[A-Z])?)\.\s+([A-Z][^.]*?\.)'
    match = re.match(pattern2, text)
    
    if match:
        reg_number = match.group(1)
        heading_text = match.group(2).strip()
        heading_text = heading_text.rstrip('.')
        return reg_number, heading_text, source_modifier
    
    # Pattern 3: Residential format (e.g., "R101.4.2 Title. Text...")
    pattern3 = r'^(R\d{1,4}\.\d+(?:\.\d+)*(?:\.[A-Z])?)\s+([A-Z][^.]*?\.)'
    match = re.match(pattern3, text)
    
    if match:
        reg_number = match.group(1)
        heading_text = match.group(2).strip()
        heading_text = heading_text.rstrip('.')
        return reg_number, heading_text, source_modifier
    
    # Pattern 4: Residential format with period (e.g., "R101.4.2. Title...")
    pattern4 = r'^(R\d{1,4}\.\d+(?:\.\d+)*(?:\.[A-Z])?)\.\s+([A-Z][^.]*?\.)'
    match = re.match(pattern4, text)
    
    if match:
        reg_number = match.group(1)
        heading_text = match.group(2).strip()
        heading_text = heading_text.rstrip('.')
        return reg_number, heading_text, source_modifier
    
    return None, None, source_modifier

def extract_regulation_paragraphs(text: str) -> List[Tuple[str, str, str, Optional[str], Optional[str], Optional[str]]]:
    """
    Extract regulation paragraphs from PDF text.
    Returns list of (regulation_number, heading_title, paragraph_text, part, section, source_modifier) tuples.
    """
    paragraphs = []
    
    if not text:
        return paragraphs
    
    lines = text.split('\n')
    current_regulation_number = None
    current_heading_title = None
    current_paragraph = []
    current_part = None
    current_section = None
    current_source_modifier = None
    pending_source_modifier = None  # Store modifier from previous line
    
    for line in lines:
        line = line.strip()
        if not line:
            if current_paragraph and current_regulation_number:
                para_text = ' '.join(current_paragraph).strip()
                if len(para_text) > 30:
                    paragraphs.append((current_regulation_number, current_heading_title or '', para_text, current_part, current_section, current_source_modifier))
                current_paragraph = []
            continue
        
        # Check for source modifier on its own line (e.g., "[F] 307.1.1")
        source_modifier = extract_source_modifier(line)
        if source_modifier and not is_regulation_number(line):
            # This line has a modifier but isn't a regulation number - check if next line is
            pending_source_modifier = source_modifier
            # Remove modifier from line and continue processing
            line = re.sub(r'^\[[A-Z]+\]\s+', '', line)
        
        # Check for PART heading
        if is_part_heading(line):
            part_heading = extract_part_heading(line)
            if part_heading:
                current_part = part_heading
            continue
        
        # Check for SECTION heading
        if is_section_heading(line):
            section_heading = extract_section_heading_text(line)
            if section_heading:
                current_section = section_heading
            continue
        
        if is_regulation_number(line):
            if current_paragraph and current_regulation_number:
                para_text = ' '.join(current_paragraph).strip()
                if len(para_text) > 30:
                    paragraphs.append((current_regulation_number, current_heading_title or '', para_text, current_part, current_section, current_source_modifier))
            
            reg_number, heading_title, source_modifier = extract_regulation_number_and_heading(line)
            if reg_number:
                current_regulation_number = reg_number
                current_heading_title = heading_title
                # Use pending modifier if present, otherwise use extracted one
                current_source_modifier = pending_source_modifier if pending_source_modifier else source_modifier
                pending_source_modifier = None  # Reset after using
                
                # Extract paragraph text - everything after the heading period
                heading_patterns = [
                    r'^(\d{3,4}\.\d+(?:\.\d+)*(?:\.[A-Z])?)\s+([A-Z][^.]*?\.)',
                    r'^(\d{3,4}\.\d+(?:\.\d+)*(?:\.[A-Z])?)\.\s+([A-Z][^.]*?\.)',
                    r'^(R\d{1,4}\.\d+(?:\.\d+)*(?:\.[A-Z])?)\s+([A-Z][^.]*?\.)',
                    r'^(R\d{1,4}\.\d+(?:\.\d+)*(?:\.[A-Z])?)\.\s+([A-Z][^.]*?\.)',
                ]
                
                remaining = line.strip()
                # Remove source modifier if present
                if source_modifier:
                    remaining = re.sub(r'^\[[A-Z]+\]\s+', '', remaining)
                
                for pattern in heading_patterns:
                    match = re.match(pattern, remaining)
                    if match:
                        heading_end = match.end()
                        remaining = remaining[heading_end:].strip()
                        break
                
                if remaining == line.strip():
                    remaining = re.sub(r'^\[[A-Z]+\]\s*', '', remaining)  # Remove modifier
                    remaining = re.sub(r'^[R]?\d{1,4}\.\d+(?:\.\d+)*(?:\.[A-Z])?\.?\s+[A-Z][^.]*?\.\s*', '', remaining, count=1).strip()
                
                current_paragraph = [remaining] if remaining else []
            else:
                # Try to extract just the number
                match = re.match(r'^(\d{3,4}\.\d+(?:\.\d+)*(?:\.[A-Z])?)', line)
                if match:
                    current_regulation_number = match.group(1)
                    current_heading_title = None
                    remaining = line[len(match.group(1)):].strip()
                    remaining = remaining.lstrip('. ')
                    current_paragraph = [remaining] if remaining else []
        else:
            if current_regulation_number:
                current_paragraph.append(line)
    
    if current_paragraph and current_regulation_number:
        para_text = ' '.join(current_paragraph).strip()
        if len(para_text) > 30:
            paragraphs.append((current_regulation_number, current_heading_title or '', para_text, current_part, current_section, current_source_modifier))
    
    return paragraphs

def process_pdf_file(pdf_path: str, chapter_info: Dict[str, str], paragraph_id: int) -> tuple:
    """
    Process a single PDF file and extract regulation paragraphs.
    Returns (paragraphs_list, next_paragraph_id).
    """
    paragraphs = []
    code_type = chapter_info.get('code_type', 'Base')
    chapter = chapter_info.get('chapter', '')
    
    try:
        logger.info(f"Processing PDF: {pdf_path}")
        
        with pdfplumber.open(pdf_path) as pdf:
            logger.info(f"PDF has {len(pdf.pages)} pages")
            
            # Extract all text from all pages first to maintain PART/SECTION context
            all_text_parts = []
            page_map = []  # Map text position to page number
            
            for page_num, page in enumerate(pdf.pages, 1):
                try:
                    text = page.extract_text()
                    if text:
                        all_text_parts.append(text)
                        page_map.extend([page_num] * len(text.split('\n')))
                except Exception as e:
                    logger.warning(f"Error extracting text from page {page_num}: {e}")
                    continue
            
            # Process all text together to maintain PART/SECTION context
            full_text = '\n'.join(all_text_parts)
            reg_paragraphs = extract_regulation_paragraphs(full_text)
            
            for reg_number, heading_title, para_text, part, section, source_modifier in reg_paragraphs:
                # Clean boilerplate from paragraph text
                para_text = clean_boilerplate(para_text)
                
                # Skip if paragraph is too short after cleaning
                if len(para_text) < 30:
                    continue
                
                # Sanitize text (remove invisible characters)
                para_text = sanitize_text(para_text)
                heading_title = sanitize_text(heading_title) if heading_title else ''
                
                # Skip if paragraph is empty or too short after sanitization
                if not para_text or len(para_text.strip()) < 20:
                    continue
                
                # Normalize quotes
                para_text = normalize_quotes(para_text)
                heading_title = normalize_quotes(heading_title) if heading_title else ''
                
                # Skip boilerplate/non-regulation text
                if any(skip in para_text.lower()[:100] for skip in [
                    'this is an unofficial version',
                    'commonwealth of massachusetts',
                    'page',
                    'table of contents',
                ]):
                    continue
                
                # Try to determine page number from text position
                page_num = 1
                for i, page_text in enumerate(all_text_parts, 1):
                    if reg_number in page_text or para_text[:100] in page_text:
                        page_num = i
                        break
                
                # Generate regulation_uid: regulation_number::chapter
                regulation_uid = f"{reg_number}::{chapter}"
                
                paragraphs.append({
                    'id': paragraph_id,
                    'regulation_number': reg_number,
                    'section_heading': heading_title if heading_title else '',
                    'paragraph_text': para_text,
                    'part': part if part else '',
                    'section': section if section else '',
                    'code_type': code_type,
                    'source_modifier': source_modifier if source_modifier else '',
                    'regulation_uid': regulation_uid,
                    'source_url': chapter_info['url'],
                    'chapter': chapter,
                    'page_number': page_num,
                    'source_type': 'PDF'
                })
                paragraph_id += 1
        
        logger.info(f"Extracted {len(paragraphs)} regulation paragraphs from {pdf_path}")
        
    except Exception as e:
        logger.error(f"Error processing PDF {pdf_path}: {e}")
    
    return paragraphs, paragraph_id

def process_pdf_directory(pdf_dir: str = "./selenium_downloads") -> pd.DataFrame:
    """Process all PDFs in a directory, maintaining order and continuous IDs."""
    pdf_dir_path = Path(pdf_dir)
    
    if not pdf_dir_path.exists():
        logger.error(f"PDF directory not found: {pdf_dir}")
        return pd.DataFrame()
    
    pdf_files = list(pdf_dir_path.glob("*.pdf"))
    
    if not pdf_files:
        logger.warning(f"No PDF files found in {pdf_dir}")
        return pd.DataFrame()
    
    # Sort PDFs by chapter number to maintain proper order (main chapters first)
    pdf_files.sort(key=lambda f: extract_chapter_number(f.name))
    
    logger.info(f"Found {len(pdf_files)} PDF files to process (sorted by chapter)")
    
    all_paragraphs = []
    paragraph_id = 1  # Single global counter across all PDFs
    
    for pdf_file in pdf_files:
        chapter_info = get_chapter_info(pdf_file.name)
        paragraphs, paragraph_id = process_pdf_file(str(pdf_file), chapter_info, paragraph_id)
        all_paragraphs.extend(paragraphs)
    
    df = pd.DataFrame(all_paragraphs)
    
    # Final cleaning and filtering before saving
    logger.info(f"Total paragraphs before filtering: {len(df)}")
    
    if not df.empty:
        # Remove rows with empty or too short paragraph_text
        initial_count = len(df)
        df = df[df['paragraph_text'].notna()]
        df = df[df['paragraph_text'].astype(str).str.len() > 20]
        
        # Sanitize all text columns
        text_columns = ['paragraph_text', 'section_heading', 'part', 'section']
        for col in text_columns:
            if col in df.columns:
                df[col] = df[col].astype(str).apply(sanitize_text)
        
        # Remove rows where paragraph_text is empty or just whitespace after sanitization
        df = df[df['paragraph_text'].str.strip().str.len() > 20]
        
        # Remove rows where paragraph_text is just "." or similar
        df = df[~df['paragraph_text'].str.strip().isin(['.', '..', '...', ''])]
        
        filtered_count = len(df)
        logger.info(f"Filtered out {initial_count - filtered_count} rows with empty/invalid text")
        logger.info(f"Total paragraphs after filtering: {filtered_count}")
    
    return df

def main():
    """Main execution."""
    import sys
    
    pdf_dir = sys.argv[1] if len(sys.argv) > 1 else "./selenium_downloads"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "MA_Building_Code_Paragraphs.csv"
    
    print("="*60)
    print("MA BUILDING CODE PDF EXTRACTION")
    print("="*60)
    print(f"\nLooking for PDFs in: {pdf_dir}")
    print(f"Output CSV: {output_file}")
    
    df = process_pdf_directory(pdf_dir)
    
    if not df.empty:
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"\n✅ CSV saved to: {output_file}")
        print(f"   Total paragraphs: {len(df)}")
        print(f"   Chapters processed: {df['chapter'].nunique()}")
        print(f"   Code types: {df['code_type'].value_counts().to_dict()}")
        print(f"   Source modifiers: {df[df['source_modifier'] != '']['source_modifier'].value_counts().to_dict()}")
        
        # Verify no empty paragraph_text
        empty_count = len(df[df['paragraph_text'].str.strip().str.len() <= 20])
        print(f"   Empty/short paragraphs: {empty_count}")
        
        print(f"\n📋 Columns: {', '.join(df.columns)}")
        print("\n📋 Ready for Mantis upload!")
    else:
        print("\n❌ No data extracted. Make sure PDFs are in the directory.")

if __name__ == "__main__":
    main()

