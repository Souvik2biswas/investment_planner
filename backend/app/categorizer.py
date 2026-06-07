import json
import os
import re
from typing import List
from datetime import datetime, date
from pydantic import BaseModel, Field
from backend.app.schema import TransactionCreate, TransactionCategory

class TransactionListOutput(BaseModel):
    transactions: List[TransactionCreate]

def parse_date_safely(date_str: str) -> date:
    """
    Attempts to parse date strings in common formats, returning a date object.
    Supports both numeric formats (e.g., 05-06-2026) and alphabetic month names (e.g., 05-Jun-2026, Jun 5, 2026).
    """
    cleaned_str = date_str.strip()
    
    # Try common alphabetic and numeric formats directly
    formats = (
        # Alphabetic formats
        '%d-%b-%Y', '%d-%B-%Y', '%d/%b/%Y', '%d/%B/%Y', '%d %b %Y', '%d %B %Y', 
        '%b %d, %Y', '%B %d, %Y', '%b %d %Y', '%B %d %Y',
        # Numeric formats
        '%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d', '%d-%m-%y', '%d/%m/%y', '%Y/%m/%d'
    )
    
    for fmt in formats:
        try:
            return datetime.strptime(cleaned_str, fmt).date()
        except ValueError:
            continue
            
    # As a last-ditch fallback, strip non-date characters and try numeric formats
    digit_only_str = re.sub(r'[^\d/-]', '', cleaned_str)
    for fmt in ('%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d', '%d-%m-%y', '%d/%m/%y', '%Y/%m/%d'):
        try:
            return datetime.strptime(digit_only_str, fmt).date()
        except ValueError:
            continue
            
    # Default to today if parsing fails
    return date.today()

def local_heuristic_categorizer(text: str) -> List[TransactionCreate]:
    """
    Offline/local fallback categorizer using regex heuristics.
    Parses transaction rows from text and applies rule-based categorization.
    """
    transactions = []
    lines = text.split('\n')
    
    # Heuristic regex to match transaction rows (e.g. "05-06-2026 Uber India 350.00 DEBIT")
    # Matches patterns like: [Date] [Description] [Amount] [Type] or table rows like "| Date | Desc | Amt |"
    date_pattern = r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})'
    amount_pattern = r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\d+(?:\.\d{2})?)'
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('| -') or 'Balance' in line:
            continue
            
        # Try to find a date in the line
        date_match = re.search(date_pattern, line)
        if not date_match:
            continue
            
        tx_date_str = date_match.group(1)
        # Remove date and clean the rest of the line
        rest_of_line = line.replace(tx_date_str, "").replace("|", " ").strip()
        
        # Look for amount in the rest of the line
        amt_match = re.findall(amount_pattern, rest_of_line)
        if not amt_match:
            continue
            
        # Take the last or largest numeric amount that matches
        tx_amount = float(amt_match[-1].replace(",", ""))
        
        # Determine type (DEBIT / CREDIT)
        tx_type = "DEBIT"
        if "CREDIT" in rest_of_line.upper() or "CR" in rest_of_line.upper() or "REFUND" in rest_of_line.upper() or "SALARY" in rest_of_line.upper():
            tx_type = "CREDIT"
            
        # Clean description
        tx_desc = rest_of_line
        for amt_str in amt_match:
            tx_desc = tx_desc.replace(amt_str, "")
        tx_desc = re.sub(r'\b(DEBIT|CREDIT|DR|CR)\b', '', tx_desc, flags=re.IGNORECASE)
        tx_desc = re.sub(r'\s+', ' ', tx_desc).strip()
        
        if not tx_desc:
            tx_desc = "Standard Transaction"
            
        # Apply heuristics for category
        desc_lower = tx_desc.lower()
        category = TransactionCategory.OTHERS
        notes = None
        
        if any(w in desc_lower for w in ["uber", "ola", "cab", "taxi", "metro", "railway", "flight", "indigo", "irctc"]):
            category = TransactionCategory.TRAVEL
        elif any(w in desc_lower for w in ["swiggy", "zomato", "food", "restaurant", "cafe", "starbucks", "grocery", "supermarket", "d Mart", "pizza", "burger"]):
            category = TransactionCategory.FOOD
        elif any(w in desc_lower for w in ["electricity", "water", "bill", "broadband", "internet", "airtel", "jio", "power", "utilities"]):
            category = TransactionCategory.UTILITIES
            if "internet" in desc_lower or "broadband" in desc_lower or "jio" in desc_lower or "airtel" in desc_lower:
                notes = "Recurring internet utility. Potential business deduction."
        elif any(w in desc_lower for w in ["aws", "gcp", "github", "cursor", "openai", "software", "subscription", "vercel", "cloud"]):
            category = TransactionCategory.BUSINESS_EXPENSE
            notes = "Software subscription. Potential deduction for freelancer or business."
        elif any(w in desc_lower for w in ["rent", "landlord", "housing", "society"]):
            category = TransactionCategory.RENT
        elif any(w in desc_lower for w in ["salary", "payroll", "direct deposit", "credit interest", "interest"]):
            category = TransactionCategory.SALARY
            tx_type = "CREDIT"
        elif any(w in desc_lower for w in ["mutual fund", "stocks", "zerodha", "groww", "sip", "etf", "invest", "broker"]):
            category = TransactionCategory.INVESTMENT
        elif any(w in desc_lower for w in ["lic", "insurance", "medical", "hospital", "pharmeasy", "pharmacy", "doctor", "health"]):
            category = TransactionCategory.POTENTIAL_DEDUCTION
            if "insurance" in desc_lower or "lic" in desc_lower:
                notes = "Life / Health insurance premium. Eligible for Section 80C / 80D deduction."
            else:
                notes = "Medical expenditure. Eligible for Section 80D deduction."
                
        transactions.append(
            TransactionCreate(
                transaction_date=parse_date_safely(tx_date_str),
                description=tx_desc,
                amount=tx_amount,
                transaction_type=tx_type,
                category=category,
                notes=notes
            )
        )
        
    return transactions

def categorize_transactions(scrubbed_markdown: str) -> List[TransactionCreate]:
    """
    Categorizes transactions from parsed bank statements.
    Tries to use LLM structured outputs (via OpenAI or Gemini) if keys are present.
    Falls back to local heuristic parsing when no LLM API keys are available.
    """
    openai_key = os.environ.get("OPENAI_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    
    if openai_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            
            prompt = f"""
            Analyze the following bank statement markdown. Extract all transaction records.
            For each transaction, clean the description, extract date, amount, transaction type (DEBIT/CREDIT),
            and categorize it into one of: FOOD, UTILITIES, RENT, TRAVEL, ENTERTAINMENT, BUSINESS_EXPENSE, SALARY, INVESTMENT, POTENTIAL_DEDUCTION, OTHERS.
            Add useful flags in notes if it looks like a tax deduction (e.g. software subscriptions, insurance, internet, etc.).
            
            Statement:
            {scrubbed_markdown}
            """
            
            response = client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a professional financial assistant parsing transaction records."},
                    {"role": "user", "content": prompt}
                ],
                response_format=TransactionListOutput,
            )
            return response.choices[0].message.parsed.transactions
        except Exception as e:
            print(f"OpenAI categorization failed: {e}. Falling back to heuristics.")
            
    elif gemini_key:
        try:
            # Try to use Google Generative AI
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            
            # Using structured JSON schema output
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            prompt = f"""
            You are a professional financial assistant. Analyze the following bank statement markdown.
            Extract all transaction records. Return a JSON object matching this schema:
            
            {{
              "transactions": [
                {{
                  "transaction_date": "YYYY-MM-DD",
                  "description": "Clean description",
                  "amount": 123.45,
                  "transaction_type": "DEBIT" or "CREDIT",
                  "category": "FOOD" | "UTILITIES" | "RENT" | "TRAVEL" | "ENTERTAINMENT" | "BUSINESS_EXPENSE" | "SALARY" | "INVESTMENT" | "POTENTIAL_DEDUCTION" | "OTHERS",
                  "notes": "Optional comments/notes"
                }}
              ]
            }}
            
            Statement:
            {scrubbed_markdown}
            """
            
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            data = json.loads(response.text)
            txs = []
            for tx_data in data.get("transactions", []):
                # Ensure date object is parsed
                dt = parse_date_safely(tx_data.get("transaction_date", ""))
                txs.append(
                    TransactionCreate(
                        transaction_date=dt,
                        description=tx_data.get("description", "Transaction"),
                        amount=float(tx_data.get("amount", 0)),
                        transaction_type=tx_data.get("transaction_type", "DEBIT"),
                        category=TransactionCategory(tx_data.get("category", "OTHERS")),
                        notes=tx_data.get("notes")
                    )
                )
            return txs
        except Exception as e:
            print(f"Gemini categorization failed: {e}. Falling back to heuristics.")

    # Fallback to local heuristic categorizer
    return local_heuristic_categorizer(scrubbed_markdown)
