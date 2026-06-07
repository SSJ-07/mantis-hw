# Mantis Upload Guide - Paragraph Resolution

## ✅ CSV Structure for Paragraph-Resolution Embedding

Your scraper outputs a CSV with this structure:

| Column Name | Type in Mantis | Description |
|------------|----------------|-------------|
| `id` | Unused (or ID) | Unique paragraph identifier |
| `section_heading` | Categoric | Section/chapter heading (e.g., "Section 1.2 Fire Safety") |
| `paragraph_text` | **Semantic** ⚠️ | **The actual paragraph text - REQUIRED as semantic field** |
| `source_url` | Links (optional) | URL to the source document |
| `chapter` | Categoric (optional) | Chapter name/identifier |
| `page_number` | Unused (optional) | Page number for PDFs |
| `source_type` | Categoric (optional) | "PDF" or "HTML" |

## 📋 Example CSV Output

```csv
id,section_heading,paragraph_text,source_url,chapter,page_number,source_type
1,Section 1.2 Fire Safety,Every room must have at least one smoke detector installed in accordance with NFPA 72 standards.,https://mass.gov/.../chapter-1,Chapter 1,5,PDF
2,Section 1.2 Fire Safety,Detectors must be interconnected across rooms on the same floor level to ensure comprehensive coverage.,https://mass.gov/.../chapter-1,Chapter 1,5,PDF
3,Section 2.1 Electrical Code,Outlets must be grounded to prevent electrical hazards and comply with NEC requirements.,https://mass.gov/.../chapter-2,Chapter 2,12,PDF
4,Section 2.1 Electrical Code,Circuits should be tested every 6 months for compliance with local building codes.,https://mass.gov/.../chapter-2,Chapter 2,12,PDF
```

## 🎯 Key Requirements

1. **One row per paragraph** - Each paragraph is a separate data point
2. **`paragraph_text` must be Semantic** - This is required to prevent the error: *"At least one semantic or coordinate field is required"*
3. **Meaningful text in `paragraph_text`** - Each paragraph should be substantial (minimum 50 characters)

## 🚀 Mantis Upload Steps

1. Run the scraper: `python scraper.py`
2. Open Mantis and create a new space
3. Upload `MA_Building_Code_Paragraphs.csv`
4. **Set `paragraph_text` as Semantic** (this is critical!)
5. Optionally set `section_heading` as Categoric for filtering
6. Optionally set `source_url` as Links for navigation
7. Upload and explore your paragraph-resolution cognitive map!

## 🧠 What Paragraph Resolution Achieves

- **Granular insights**: Each paragraph gets its own embedding and position on the map
- **Cross-section clustering**: Similar topics from different chapters cluster together
- **Fine-grained search**: Find specific requirements even within large documents
- **Detailed visualization**: Zoom into specific regulatory subthemes

Example: All fire safety paragraphs (from different chapters) will cluster together, creating a visual "fire safety" region on your Mantis map.

