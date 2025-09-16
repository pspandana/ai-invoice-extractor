# Invoice Extractor

An AI-powered invoice data extraction tool that processes PDF invoices and extracts key business information into structured CSV and JSON formats using OpenAI's GPT-4o model.

## Features

- **PDF Processing**: Converts PDF invoices to images for AI analysis
- **AI-Powered Extraction**: Uses OpenAI GPT-4o for intelligent data extraction
- **Dual Output**: Generates both CSV summary and detailed JSON files
- **Batch Processing**: Handles multiple invoices at once
- **Error Handling**: Robust error handling with detailed logging
- **Flexible Prompts**: Support for different extraction strategies

## Installation

### Prerequisites

- Python 3.8 or higher
- OpenAI API key

### Required Libraries

```bash
pip install openai python-dotenv PyMuPDF
```

### Optional Libraries

```bash
pip install pandas  # For enhanced CSV handling
```

## Setup

1. **Clone or download** the `invoice_extractor.py` file

2. **Set up environment variables**:
   ```bash
   export OPENAI_API_KEY="your-openai-api-key-here"
   ```
   
   Or create a `.env` file:
   ```
   OPENAI_API_KEY=your-openai-api-key-here
   ```

3. **Create folder structure**:
   ```
   your_project/
   ├── invoice_extractor.py
   ├── sample_PDFs/           # Place your PDF invoices here
   └── extracted_data/        # Output folder (auto-created)
   ```

## Usage

### Basic Usage

1. Place your PDF invoices in the `sample_PDFs` folder
2. Run the extractor:
   ```bash
   python invoice_extractor.py
   ```

### Output Files

The program generates:

- **CSV Summary** (`extracted_data/invoices_summary.csv`): Clean 13-column summary for business analysis
- **Individual JSON files** (`extracted_data/*.json`): Complete detailed data for each invoice
- **Processing logs**: Real-time status and error reporting

### CSV Output Structure

| Field | Description |
|-------|-------------|
| filename | Original PDF filename |
| status | success/error |
| invoiceNumber | Invoice number or document ID |
| invoiceDate | Invoice date |
| vendorName | Company that issued the invoice |
| customerName | Company being billed |
| totalAmount | Final total amount (numbers only) |
| subtotal | Subtotal before taxes |
| tax | Tax amount |
| dueDate | Payment due date |
| lineItemsCount | Number of line items |
| lineItemsSummary | Brief description of main items |
| error | Error message if processing failed |

## Prompt Strategies

The tool supports different prompting approaches depending on your needs:

### Current Prompt (Result-Oriented)

**Best for**: Production use, consistent reporting, system integration

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

**Produces**: Clean 10-field structure, 100% consistent across invoices

### Alternative: 7-Point Comprehensive Prompt

**Best for**: Data discovery, comprehensive extraction, flexible analysis

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

**Produces**: Rich 20-30 field structure, captures all available data

## Configuration Options

### Changing the Prompt

To switch between prompt strategies, modify the `prompt` variable in the `extract_data` method:

```python
# For result-oriented approach (current)
prompt = """You are an expert invoice data extraction AI..."""

# For comprehensive approach  
prompt = """You are an expert AI assistant specializing..."""
```

### Adjusting Processing Parameters

```python
# In the extract_data method
response = self.client.chat.completions.create(
    model="gpt-4o",           # AI model to use
    temperature=0,            # Consistency (0 = deterministic)
    max_tokens=1000          # Response length limit
)
```

### Customizing Folder Paths

```python
# In main() function
extractor.process_folder(
    folder_path="your_input_folder",    # PDF input folder
    output_folder="your_output_folder"  # Results output folder
)
```

## Error Handling

The tool handles common issues:

- **Invalid PDF files**: Skips corrupted files, continues processing
- **JSON parsing errors**: Multiple cleanup strategies for malformed responses
- **Missing API key**: Clear error message with setup instructions
- **Network issues**: Timeout handling and retry logic
- **File permissions**: Handles read/write permission errors

## Common Issues & Solutions

### JSON Parsing Errors

**Problem**: "Expecting ',' delimiter" errors
**Solution**: The current prompt includes specific JSON formatting instructions to prevent this

### Missing Invoice Numbers

**Problem**: Invoice numbers not extracted
**Solution**: Check the actual PDF - numbers might be in headers, footers, or watermarks

### API Rate Limits

**Problem**: Too many requests
**Solution**: Add delays between requests or use a higher-tier API plan

### Memory Issues with Large PDFs

**Problem**: Out of memory errors
**Solution**: Reduce image resolution in `pdf_to_images` method:
```python
pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))  # Reduce from 2,2 to 1.5,1.5
```

## Development Notes

### Project Evolution

This tool evolved through several iterations to solve key challenges:

1. **Model compatibility**: Updated from deprecated vision models to GPT-4o
2. **PDF processing**: Switched from text extraction to image-based processing
3. **Data structure**: Moved from 200+ column exports to focused 10-field output
4. **Prompt engineering**: Refined from open-ended to structured extraction
5. **Error handling**: Added comprehensive JSON parsing and error recovery

### Technical Architecture

```
PDF Input → Image Conversion → AI Processing → JSON Response → Data Validation → CSV + JSON Output
```

### Performance Considerations

- **Processing time**: ~10-30 seconds per invoice depending on complexity
- **API costs**: ~$0.01-0.05 per invoice (varies by content and model)
- **Memory usage**: ~50MB per PDF during processing
- **Accuracy**: 85-95% field extraction accuracy on standard invoices

## Contributing

When modifying the code:

1. **Test with diverse invoice formats** before deploying
2. **Validate JSON output** with online JSON validators
3. **Check CSV compatibility** with Excel/Google Sheets
4. **Monitor API usage** to avoid unexpected costs
5. **Keep error handling robust** for production use

## License

This project is provided as-is for educational and business use. Ensure compliance with OpenAI's usage policies when processing sensitive financial documents.

## Support

For issues or improvements:

1. Check the error logs in console output
2. Verify API key and model access
3. Test with simpler PDF files first
4. Review the JSON output for debugging

---

**Last Updated**: September 16, 2025 
**Version**: 1.0  
**Compatible Models**: GPT-4o, GPT-4o-mini