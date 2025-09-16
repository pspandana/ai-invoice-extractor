import json
import os
import base64
import csv
from typing import Dict, Any, List
import openai
from pathlib import Path
import fitz  # PyMuPDF
from dotenv import load_dotenv
import re


load_dotenv()

class InvoiceExtractor:
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
        
    def pdf_to_images(self, pdf_path: str) -> List[str]:
        """Convert PDF to base64 images"""
        doc = fitz.open(pdf_path)
        images = []
        
        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_data = pix.tobytes("png")
            img_base64 = base64.b64encode(img_data).decode('utf-8')
            images.append(img_base64)
        
        doc.close()
        return images
    
    def extract_data(self, pdf_path: str) -> Dict[str, Any]:
        """Extract invoice data using LLM with improved prompt"""
        try:
            images = self.pdf_to_images(pdf_path)
            
            # Improved prompt with specific field definitions and extraction guidance
            prompt = """You are an expert invoice data extraction AI. Extract EXACTLY these fields from the invoice document and return as clean JSON.

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
5. ** Return ONLY valid JSON with double-quoted property names. No markdown, no explanations.**
6. Do not include any extra fields beyond the 10 required

Example format:
{
  "invoiceNumber": "INV-12345",
  "invoiceDate": "2025-01-15",
  "vendorName": "ABC Company",
  "customerName": "XYZ Corp",
  "totalAmount": 1500.00,
  "subtotal": 1200.00,
  "tax": 300.00,
  "dueDate": "2025-02-15",
  "lineItemsCount": 3,
  "lineItemsSummary": "Office supplies and consulting services"
}"""

            content = [{"type": "text", "text": prompt}]
            for img in images:
                content.append({
                    "type": "image_url", 
                    "image_url": {"url": f"data:image/png;base64,{img}"}
                })
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": content}],
                temperature=0
            )
            
            # Clean up response and parse JSON
            text = response.choices[0].message.content.strip()
            
            # Remove markdown formatting if present
            if "```json" in text:
                start = text.find("```json") + 7
                end = text.find("```", start)
                text = text[start:end].strip()
            elif "```" in text:
                start = text.find("```") + 3
                end = text.find("```", start)
                text = text[start:end].strip()
            
            # Find JSON object boundaries
            json_start = text.find('{')
            json_end = text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_text = text[json_start:json_end]
    
                try:
                    return json.loads(json_text)
                except json.JSONDecodeError:
                # Only if that fails, try cleanup
                    try:
                    # Clean up common JSON issues
                        json_text = json_text.replace("'", '"')  
                        json_text = json_text.replace('\n', ' ')  
                    # Remove trailing commas
                        json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
                        return json.loads(json_text)
                    except json.JSONDecodeError as e:
                        return {"error": f"JSON parsing failed: {str(e)}"}
            else:
                return {"error": "No valid JSON found in response"}
            
        except Exception as e:
            return {"error": f"Extraction error: {str(e)}"}
    
    def create_csv(self, all_results: List[Dict], csv_file: str):
        """Create CSV with debug information and error handling"""
        
        fieldnames = [
            'filename', 'invoiceNumber', 'invoiceDate', 
            'vendorName', 'customerName', 'totalAmount', 'subtotal', 'tax',
            'dueDate', 'lineItemsCount', 'lineItemsSummary',  'status','error'
        ]
        
        print(f"Creating CSV with {len(fieldnames)} columns...")
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in all_results:
                filename = result['filename']
                
                if result['status'] == 'error':
                    row = {field: None for field in fieldnames}
                    row.update({
                        'filename': filename,
                        'status': 'error',
                        'error': result.get('error', 'Unknown error')[:200]  # Truncate long errors
                    })
                    print(f"Error row: {filename}")
                    
                else:
                    data = result['data']
                    
                    # Debug: Show what fields we found
                    available_fields = list(data.keys())
                    missing_fields = []
                    
                    # Check each required field
                    invoice_num = data.get('invoiceNumber')
                    if not invoice_num:
                        missing_fields.append('invoiceNumber')
                    
                    vendor = data.get('vendorName')
                    if not vendor:
                        missing_fields.append('vendorName')
                    
                    total = data.get('totalAmount')
                    if total is None:
                        missing_fields.append('totalAmount')
                    
                    # Print debug info for problematic extractions
                    if missing_fields:
                        print(f"Missing fields in {filename}: {missing_fields}")
                        print(f"  Available fields: {available_fields}")
                    
                    row = {
                        'filename': filename,
                        'status': 'success',
                        'error': None,
                        'invoiceNumber': invoice_num,
                        'invoiceDate': data.get('invoiceDate'),
                        'vendorName': vendor,
                        'customerName': data.get('customerName'),
                        'totalAmount': total,
                        'subtotal': data.get('subtotal'),
                        'tax': data.get('tax'),
                        'dueDate': data.get('dueDate'),
                        'lineItemsCount': data.get('lineItemsCount'),
                        'lineItemsSummary': data.get('lineItemsSummary')
                    }
                
                writer.writerow(row)
    
    def process_folder(self, folder_path: str = "sample_PDFs", output_folder: str = "extracted_data"):
        """Process all PDFs in folder with comprehensive error handling"""
        folder = Path(folder_path)
        output = Path(output_folder)
        output.mkdir(exist_ok=True)
        
        pdf_files = list(folder.glob("*.pdf"))
        if not pdf_files:
            print(f"No PDF files found in {folder_path}")
            return
        
        print(f"Processing {len(pdf_files)} invoices...")
        print("=" * 50)
        
        all_results = []
        successful_count = 0
        
        # Process each PDF
        for i, pdf_file in enumerate(pdf_files, 1):
            print(f"\n[{i}/{len(pdf_files)}] Processing: {pdf_file.name}")
            
            # Extract data
            data = self.extract_data(str(pdf_file))
            
            # Create result
            if "error" in data:
                result = {
                    'filename': pdf_file.name,
                    'status': 'error',
                    'error': data['error']
                }
                print(f"  Status: ERROR - {data['error'][:100]}...")
                
            else:
                result = {
                    'filename': pdf_file.name,
                    'status': 'success',
                    'data': data
                }
                
                # Show extracted key info
                vendor = data.get('vendorName', 'N/A')
                invoice_num = data.get('invoiceNumber', 'N/A')
                total = data.get('totalAmount', 'N/A')
                
                print(f"  Status: SUCCESS")
                print(f"  Invoice: {invoice_num}")
                print(f"  Vendor: {vendor}")
                print(f"  Total: ${total}")
                
                successful_count += 1
            
            all_results.append(result)
            
            # Save individual JSON file
            json_file = output / f"{pdf_file.stem}.json"
            with open(json_file, 'w', encoding='utf-8') as jf:
                json.dump(data, jf, indent=2, ensure_ascii=False)
        
        print("\n" + "=" * 50)
        print("Creating CSV summary...")
        
        # Create CSV
        csv_file = output / "invoices_summary.csv"
        self.create_csv(all_results, str(csv_file))
        
        # Final summary
        print(f"\nProcessing Complete!")
        print(f"Successful: {successful_count}/{len(pdf_files)}")
        print(f"Failed: {len(pdf_files) - successful_count}/{len(pdf_files)}")
        print(f"\nOutput files:")
        print(f"  CSV Summary: {csv_file}")
        print(f"  JSON Details: {output}/*.json")
        
        if successful_count < len(pdf_files):
            print(f"\nCheck the error messages above for failed extractions.")

def main():
    """Main execution function"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key:")
        print("  export OPENAI_API_KEY='your-key-here'")
        return
    
    print("Invoice Extractor Starting...")
    print("Using OpenAI GPT-4o model")
    
    extractor = InvoiceExtractor(api_key)
    extractor.process_folder()

if __name__ == "__main__":
    main()