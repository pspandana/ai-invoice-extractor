import json
import os
import base64
import csv
from typing import Dict, Any, List
import openai
from pathlib import Path
import fitz  # PyMuPDF
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class InvoiceExtractor:
    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
        
    def pdf_to_images(self, pdf_path: str) -> List[str]:
        """Convert PDF to base64 images at a higher resolution"""
        doc = fitz.open(pdf_path)
        images = []
        
        for page in doc:
            # Use a higher resolution (matrix) for better AI vision performance
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_data = pix.tobytes("png")
            img_base64 = base64.b64encode(img_data).decode('utf-8')
            images.append(img_base64)
        
        doc.close()
        return images
    
    def clean_and_parse_json(self, text: str) -> Any:
        """Clean up and parse a JSON object from a string"""
        
        # Remove markdown formatting
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.rfind("```")
            text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.rfind("```", start)
            text = text[start:end].strip()

        json_start = text.find('{')
        if json_start == -1:
             return {"error": "No JSON object found in response"}
        json_end = text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_text = text[json_start:json_end]
        else:
            return {"error": "Could not determine JSON boundaries"}

        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            return {"error": f"Could not parse JSON: {str(e)} - Snippet: {json_text[:200]}..."}

    def extract_data_from_page(self, base64_image: str, page_num: int) -> Dict[str, Any]:
        """
        Analyzes a SINGLE page image and returns its status and data.
        """
        try:
            prompt = """You are an AI assistant analyzing a single page from a potentially multi-page invoice document. Your task is to extract all invoice data present on THIS PAGE ONLY and determine its context.

Return a single JSON object with two main keys: "status" and "data".

1.  The "status" object must contain these boolean fields:
    - "is_start_of_invoice": true if an invoice header (invoice number, vendor name, etc.) is present.
    - "is_continuation": true if the page contains only line items or totals that belong to a previous page.
    - "is_end_of_invoice": true if a final total (Total Amount Due) is present.
    - "is_blank_or_misc": true if the page contains no invoice data.

2.  The "data" object must contain any of the following fields you can find ON THIS PAGE:
    - invoiceNumber, invoiceDate, vendorName, customerName, totalAmount, subtotal, tax, dueDate, and a "lineItems" array containing an object for each line item found.

EXAMPLE RESPONSE FOR A FIRST PAGE:
{
  "status": { "is_start_of_invoice": true, "is_continuation": false, "is_end_of_invoice": false, "is_blank_or_misc": false },
  "data": { "invoiceNumber": "INV-123", "lineItems": [{"description": "Item A", "amount": 100.00}] }
}
Your response must be ONLY the valid JSON object.
"""
            content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
            ]
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": content}],
                temperature=0,
                max_tokens=1024
            )
            
            raw_text = response.choices[0].message.content.strip()
            print(f"    - Raw AI Response for Page {page_num}:\n{raw_text[:200]}...") # Print snippet
            
            return self.clean_and_parse_json(raw_text)
            
        except Exception as e:
            return {"error": f"Extraction error on page {page_num}: {str(e)}"}

    def create_csv(self, all_results: List[Dict], csv_file: str):
        """
        Creates CSV, now handles multiple invoices from a single file.
        """
        fieldnames = [
            'filename', 'status', 'invoiceNumber', 'invoiceDate', 
            'vendorName', 'customerName', 'totalAmount', 'subtotal', 'tax',
            'dueDate', 'lineItemsCount', 'lineItemsSummary', 'error'
        ]
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in all_results:
                if result['status'] == 'error':
                    writer.writerow({'filename': result['filename'], 'status': 'error', 'error': result.get('error')})
                    continue

                # Loop through each invoice found within a single file's data
                invoices = result.get('data', [])
                if not invoices:
                    writer.writerow({'filename': result['filename'], 'status': 'success', 'invoiceNumber': 'No invoices found'})

                for invoice_data in invoices:
                    line_items = invoice_data.get('lineItems', [])
                    summary = ", ".join([item.get('description', '') for item in line_items if item.get('description')])
                    row = {
                        'filename': result['filename'],
                        'status': 'success',
                        'invoiceNumber': invoice_data.get('invoiceNumber'),
                        'invoiceDate': invoice_data.get('invoiceDate'),
                        'vendorName': invoice_data.get('vendorName'),
                        'customerName': invoice_data.get('customerName'),
                        'totalAmount': invoice_data.get('totalAmount'),
                        'subtotal': invoice_data.get('subtotal'),
                        'tax': invoice_data.get('tax'),
                        'dueDate': invoice_data.get('dueDate'),
                        'lineItemsCount': len(line_items),
                        'lineItemsSummary': summary[:300] # Truncate long summaries
                    }
                    writer.writerow(row)

    def process_folder(self, folder_path: str, output_folder: str = "extracted_data"):
        """
        Main orchestration logic to process PDFs page by page.
        """
        folder = Path(folder_path)
        output = Path(output_folder)
        output.mkdir(exist_ok=True)
        
        pdf_files = list(folder.glob("*.pdf"))
        if not pdf_files:
            print(f"No PDF files found in {folder_path}")
            return
        
        print(f"Processing {len(pdf_files)} invoices with page-by-page strategy...")
        print("=" * 50)
        
        all_results = []
        
        for i, pdf_file in enumerate(pdf_files, 1):
            print(f"\n[{i}/{len(pdf_files)}] Processing: {pdf_file.name}")
            
            try:
                images = self.pdf_to_images(str(pdf_file))
            except Exception as e:
                print(f"  > ERROR: Could not open or process PDF file: {e}")
                all_results.append({'filename': pdf_file.name, 'status': 'error', 'error': str(e)})
                continue

            completed_invoices = []
            current_invoice = {}
            
            for page_num, image in enumerate(images, 1):
                page_result = self.extract_data_from_page(image, page_num)
                
                if "error" in page_result or not isinstance(page_result, dict):
                    print(f"    - Error parsing response for page {page_num}.")
                    continue

                status = page_result.get('status', {})
                data = page_result.get('data', {})

                if not status or not data:
                    continue

                if status.get('is_start_of_invoice'):
                    if current_invoice:
                        completed_invoices.append(current_invoice)
                    current_invoice = data
                
                elif status.get('is_continuation') and current_invoice:
                    current_invoice.setdefault('lineItems', []).extend(data.get('lineItems', []))
                
                if status.get('is_end_of_invoice') and current_invoice:
                    # Merge final details, ensuring existing data isn't overwritten by null
                    for key, value in data.items():
                        if value is not None:
                            current_invoice[key] = value
                    
                    completed_invoices.append(current_invoice)
                    current_invoice = {}

            # After the loop, save any remaining invoice
            if current_invoice:
                completed_invoices.append(current_invoice)

            all_results.append({
                'filename': pdf_file.name,
                'status': 'success',
                'data': completed_invoices
            })
            
            print(f"  > Found {len(completed_invoices)} invoice(s) in this file.")

            # Save the structured data to a single JSON file for this PDF
            json_file = output / f"{pdf_file.stem}.json"
            with open(json_file, 'w', encoding='utf-8') as jf:
                json.dump(completed_invoices, jf, indent=2, ensure_ascii=False)
        
        print("\n" + "=" * 50)
        
        csv_file = output / "invoices_summary.csv"
        self.create_csv(all_results, str(csv_file))
        
        print(f"\nProcessing Complete!")
        successful_files = sum(1 for r in all_results if r['status'] == 'success')
        print(f"Successfully processed {successful_files}/{len(pdf_files)} files.")
        print(f"Failed: {len(pdf_files) - successful_files}/{len(pdf_files)}")
        print(f"\nOutput files:")
        print(f"  CSV Summary: {csv_file}")
        print(f"  JSON Details: {output}/*.json")

def main():
    """Main execution function"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key and ensure it's in a .env file")
        return
    
    print("Invoice Extractor Starting...")
    print("Using OpenAI GPT-4o model")
    
    # Correctly build and use the absolute path to the PDF folder
    script_dir = Path(__file__).parent.resolve()
    folder_to_process = script_dir / "sample_PDFs"
    
    print(f"Looking for PDFs in: {folder_to_process}")
    
    extractor = InvoiceExtractor(api_key)
    # Pass the correct folder path to the function
    extractor.process_folder(folder_path=str(folder_to_process))

if __name__ == "__main__":
    main()