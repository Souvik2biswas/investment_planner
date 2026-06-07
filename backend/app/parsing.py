import os
import re
from typing import Tuple, List
import pdfplumber

def scrub_pii(text: str) -> str:
    """
    Scrubs PII locally using robust regex rules. Masks names, accounts, card numbers,
    emails, phone numbers, and standard Indian tax identifiers (PAN, Aadhar).
    """
    scrubbed = text

    # 1. Email addresses
    scrubbed = re.sub(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        '[EMAIL]',
        scrubbed
    )

    # 2. Credit Cards
    scrubbed = re.sub(
        r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
        '[CARD_NUMBER]',
        scrubbed
    )

    # 3. Indian PAN Cards (5 letters, 4 digits, 1 letter)
    scrubbed = re.sub(
        r'\b[A-Z]{5}[0-9]{4}[A-Z]\b',
        '[PAN_NUMBER]',
        scrubbed
    )

    # 4. Indian Aadhar Card (12 digits, spaced/hyphenated)
    scrubbed = re.sub(
        r'\b\d{4}[- ]\d{4}[- ]\d{4}\b',
        '[AADHAR_NUMBER]',
        scrubbed
    )

    # 5. Standard Bank Account Numbers (usually 9-18 digits sequence)
    # We avoid matching short sequences that could be amounts or transaction numbers
    scrubbed = re.sub(
        r'\b\d{9,18}\b',
        '[ACCOUNT_NUMBER]',
        scrubbed
    )

    # 6. Phone Numbers
    scrubbed = re.sub(
        r'\b(?:\+?\d{1,3}[- ]?)?(?:[6-9]\d{4}[- ]?\d{5}|[6-9]\d{9}|\d{3}[- ]?\d{3}[- ]?\d{4})\b',
        '[PHONE]',
        scrubbed
    )

    # 7. Name markers (e.g. "Name: Souvik Biswas", "Account Holder: John Doe")
    # Captures name-labeled prefixes
    name_patterns = [
        r'(?i)(?:customer name|account holder|holder name|name|payee|recipient)\s*:\s*([A-Za-z ]+)',
        r'(?i)(?:dear|mr\.|ms\.|m/s\.)\s+([A-Za-z ]+)'
    ]
    for pattern in name_patterns:
        def replace_name(match):
            full_match = match.group(0)
            name_part = match.group(1).strip()
            # If name is short/meaningful
            if len(name_part) > 2 and not name_part.upper().startswith(('DEBIT', 'CREDIT', 'STATEMENT', 'DATE', 'AMOUNT')):
                return full_match.replace(name_part, '[CUSTOMER_NAME]')
            return full_match
        
        scrubbed = re.sub(pattern, replace_name, scrubbed)

    return scrubbed

def parse_pdf_statement(file_path: str) -> str:
    """
    Parses a PDF bank statement.
    Attempts to use LlamaParse if LLAMAPARSE_API_KEY is configured in env.
    Otherwise, falls back to local high-fidelity parsing using pdfplumber.
    """
    api_key = os.environ.get("LLAMAPARSE_API_KEY")
    if api_key:
        try:
            # Try to run LlamaParse asynchronously/synchronously
            from llama_parse import LlamaParse
            
            parser = LlamaParse(
                api_key=api_key,
                result_type="markdown",
                table_extraction=True,
                verbose=True
            )
            extractions = parser.load_data(file_path)
            if extractions:
                markdown_text = "\n\n".join([doc.text for doc in extractions])
                return markdown_text
        except Exception as e:
            print(f"LlamaParse failed: {e}. Falling back to pdfplumber.")
    
    # Fallback to pdfplumber
    return parse_pdf_plumber(file_path)

def parse_pdf_plumber(file_path: str) -> str:
    """
    Extracts text and tables from a PDF using pdfplumber, converting tables to markdown format.
    """
    markdown_content = []
    
    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            markdown_content.append(f"## Page {page_num}\n")
            
            # Extract tables first
            tables = page.extract_tables()
            table_texts = []
            
            for table in tables:
                if not table or len(table) == 0:
                    continue
                # Clean headers and rows
                headers = [str(cell or "").strip().replace("\n", " ") for cell in table[0]]
                md_table = []
                md_table.append("| " + " | ".join(headers) + " |")
                md_table.append("| " + " | ".join(["---"] * len(headers)) + " |")
                
                for row in table[1:]:
                    cells = [str(cell or "").strip().replace("\n", " ") for cell in row]
                    # Ensure same length as headers
                    if len(cells) < len(headers):
                        cells += [""] * (len(headers) - len(cells))
                    elif len(cells) > len(headers):
                        cells = cells[:len(headers)]
                    md_table.append("| " + " | ".join(cells) + " |")
                
                table_texts.append("\n".join(md_table))
            
            # Extract plain text
            text = page.extract_text()
            if text:
                # Add text
                markdown_content.append(text)
            
            # Add extracted tables
            if table_texts:
                markdown_content.append("\n### Tables Extracted\n")
                markdown_content.extend(table_texts)
                
            markdown_content.append("\n---\n")
            
    return "\n".join(markdown_content)
