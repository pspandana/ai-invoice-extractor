# Invoice Extractor

An AI-powered invoice data extraction tool that processes PDF invoices using OpenAI's GPT-4o model to extract structured business data into CSV and JSON formats.

## Features

- PDF to image conversion for AI processing
- Structured data extraction using OpenAI GPT-4o
- CSV summary output with 13 standardized fields
- Individual JSON files with complete extraction details
- Batch processing for multiple invoices
- Error handling and logging
- Configurable prompting strategies

## Installation

### Prerequisites

- Python 3.8+
- OpenAI API key with GPT-4o access

### Dependencies

```bash
pip install openai python-dotenv PyMuPDF
```

## Setup

1. **Environment Configuration**:
   Create a `.env` file:
   ```
   OPENAI_API_KEY=your-openai-api-key-here
   ```

2. **Folder Structure**:
   ```
   project/
   ├── invoice_extractor.py
   ├── sample_PDFs/           # Place PDF invoices here
   └── extracted_data/        # Output folder (auto-created)
   ```

## Usage

1. Place PDF invoices in `sample_PDFs/` folder
2. Run: `python invoice_extractor.py`

### Output Files

- **CSV Summary**: `extracted_data/invoices_summary.csv` - 13 standardized columns
- **JSON Details**: `extracted_data/*.json` - Complete extraction data per invoice

### CSV Output Format

| Field | Type | Description |
|-------|------|-------------|
| filename | string | PDF filename |
| status | string | success/error |
| invoiceNumber | string | Invoice identifier |
| invoiceDate | string | Invoice date |
| vendorName | string | Issuing company |
| customerName | string | Billed company |
| totalAmount | number | Final total |
| subtotal | number | Pre-tax amount |
| tax | number | Tax amount |
| dueDate | string | Payment due date |
| lineItemsCount | integer | Number of line items |
| lineItemsSummary | string | Brief item description |
| error | string | Error message if failed |

## Prompt Configurations

### Current Implementation (Structured Extraction)

Used in the code for consistent business reporting:

```
You are an expert invoice data extraction AI. Extract EXACTLY these fields from the invoice document and return as clean JSON.

REQUIRED FIELDS (use exact field names):
- invoiceNumber: The main invoice/document number (look for "Invoice #", "Invoice Number", "Doc #", etc.)
- invoiceDate: The invoice/document date
- vendorName: Company/organization that issued the invoice
- customerName: Company/organization being billed
- totalAmount: Final total amount (just the number, no currency symbols)
- subtotal: Subtotal amount before taxes/fees (number only)
- tax: Tax amount (number only)
- dueDate: Payment due date
- lineItemsCount: Count of distinct line items/products/services
- lineItemsSummary: Brief description of main items (1-2 sentences max)

EXTRACTION RULES:
1. Use the EXACT field names listed above
2. For missing information, use null (not empty string)
3. For amounts, extract only numbers (no $, commas, or currency)
4. Look carefully at headers, footers, and highlighted areas for invoice numbers
5. Return ONLY valid JSON with double-quoted property names. No markdown, no explanations.
6. Do not include any extra fields beyond the 10 required
```

### Alternative: Comprehensive Extraction

For maximum data capture (not currently implemented):

```
You are an expert AI assistant specializing in invoice data extraction. Your task is to analyze the provided invoice document and extract all key information. Return the extracted data in a structured JSON format.

Instructions:
1. Extract All Key Information: Scrutinize the entire document for details including, but not limited to, vendor and client information, invoice identifiers, dates, financial summaries, and detailed line items.
2. JSON Output: The final output must be a single, well-formed JSON object.
3. Descriptive Fields: Use clear, descriptive, and consistent camelCase field names.
4. Handle Missing Data: If a specific piece of information is not present in the invoice, use `null` for its value. Do not invent or infer data that is not explicitly stated.
5. Line Items: Capture each line item as a separate object within a `lineItems` array.
6. Consistency: Use the same field structure across similar invoices for easy comparison.
7. Completeness Check: If you're unsure about any data interpretation, include it rather than omit it.

Return ONLY valid JSON with double-quoted property names. No markdown, no explanations.
```

## Configuration

### Switching Prompts

Modify the `prompt` variable in `extract_data()` method to use different extraction strategies.

### Processing Parameters

```python
response = self.client.chat.completions.create(
    model="gpt-4o",        # Only tested model
    temperature=0,         # Deterministic output
    max_tokens=1000       # Response limit
)
```

### Custom Paths

```python
extractor.process_folder(
    folder_path="your_input_folder",
    output_folder="your_output_folder"
)
```

## Error Handling

Common issues and resolutions:

### JSON Parsing Errors
**Error**: "Expecting ',' delimiter"
**Cause**: Malformed JSON from AI response
**Solution**: Code includes JSON cleanup with fallback parsing

### Missing Data Extraction
**Error**: Fields showing as null in CSV
**Cause**: Information not found in PDF or unclear formatting
**Solution**: Check original PDF for data location/formatting

### API Authentication
**Error**: Invalid API key
**Solution**: Verify OPENAI_API_KEY in environment variables

### File Processing
**Error**: PDF cannot be processed
**Solution**: Ensure PDF is not corrupted and contains text/images

## Development Notes

### Technical Architecture

```
PDF Input → Image Conversion → GPT-4o Processing → JSON Response → Data Validation → CSV + JSON Output
```

### Known Limitations

- Requires clear, readable invoice layouts
- Performance depends on PDF complexity and file size
- API costs apply per processed invoice
- Some invoice formats may require prompt adjustments

### Testing Approach

The tool was developed and tested with various invoice formats including:
- Standard business invoices
- Multi-page documents
- Different vendor layouts
- Various currencies and formats

## Troubleshooting

1. **Verify API key** is correct and has GPT-4o access
2. **Check PDF quality** - ensure text is readable
3. **Review console output** for specific error messages
4. **Test with simpler invoices** first to isolate issues
5. **Examine JSON output** before troubleshooting CSV issues

## Version History

- **v1.0**: Initial working version with structured field extraction
- Resolved model compatibility issues (deprecated vision models)
- Fixed JSON parsing errors through improved prompting
- Implemented robust error handling and logging

---

**Last Updated**: September 2025  
**Tested Model**: GPT-4o  
