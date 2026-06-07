import os
import json
from typing import List, Dict, Any
from sqlalchemy import text
from backend.app.database import engine

# Index of relevant Indian Income Tax Code sections
TAX_CODE_DATABASE = [
    {
        "section": "Section 80C",
        "title": "Deductions on Investments and Expenses",
        "description": "Allows deduction for investments in PPF (Public Provident Fund), ELSS (Equity Linked Savings Scheme), EPF, Life Insurance premiums, National Savings Certificates (NSC), school tuition fees, and home loan principal repayment.",
        "max_limit": 150000.0,
        "keywords": ["insurance", "lic", "ppf", "elss", "investment", "provident fund", "tuition", "school fees", "home loan principal"]
    },
    {
        "section": "Section 80D",
        "title": "Deduction for Medical Insurance Premium",
        "description": "Deduction for health insurance premium paid for self, spouse, dependent children (up to ₹25,000), and parents (up to ₹50,000 if senior citizens). Also covers preventive health check-up expenses up to ₹5,000.",
        "max_limit": 75000.0,
        "keywords": ["medical", "health insurance", "hospital", "doctor", "health checkup", "pharmacy", "medicine", "pharmeasy"]
    },
    {
        "section": "Section 44ADA",
        "title": "Presumptive Taxation for Professionals",
        "description": "Applicable to Indian residents engaged in specified professions (like software development, IT consulting, engineering, legal, medical, etc.) with gross receipts under ₹75 Lakhs. Allows declaring 50% of gross receipts as net taxable income, treating the rest as business expenses. No requirement to maintain detailed books of accounts.",
        "max_limit": 3750000.0, # 50% of 75 lakhs
        "keywords": ["software", "aws", "gcp", "hosting", "github", "cursor", "openai", "internet", "broadband", "co-working", "freelance", "consulting", "subscription"]
    },
    {
        "section": "Section 80GG",
        "title": "Deduction for Rent Paid",
        "description": "Available for rent paid for furnished or unfurnished accommodation if the taxpayer does not receive HRA (House Rent Allowance) from an employer. Limit is the least of ₹5,000/month, 25% of total income, or rent paid minus 10% of total income.",
        "max_limit": 60000.0,
        "keywords": ["rent", "landlord", "flat rent", "housing rent", "house rent", "room rent"]
    },
    {
        "section": "Section 80TTA",
        "title": "Deduction for Interest on Savings Account",
        "description": "Allows deduction up to ₹10,000 on interest earned from savings bank accounts with banks, co-operative societies, or post offices. Excludes fixed deposits (FD) interest.",
        "max_limit": 10000.0,
        "keywords": ["savings interest", "interest income", "bank interest", "credit interest", "saving interest"]
    }
]

def search_tax_code(query: str) -> List[Dict[str, Any]]:
    """
    RAG Search Engine: Matches query keywords against indexed tax code entries.
    Computes a simple search score based on keyword intersections.
    """
    query_words = set(query.lower().split())
    scored_results = []
    
    for section in TAX_CODE_DATABASE:
        score = 0
        # Check description and title
        desc_lower = section["description"].lower()
        title_lower = section["title"].lower()
        section_lower = section["section"].lower()
        
        # Word matches
        for word in query_words:
            if word in section_lower:
                score += 10
            if word in title_lower:
                score += 3
            if word in desc_lower:
                score += 1
            # Keywords matching
            for kw in section["keywords"]:
                if word in kw:
                    score += 2
                    
        if score > 0:
            scored_results.append((score, section))
            
    # Sort by score descending
    scored_results.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored_results]

def get_tax_advisory(user_id: str) -> Dict[str, Any]:
    """
    Scans transactions for POTENTIAL_DEDUCTION or specific category keywords,
    cross-references them with the tax code, and drafts personalized recommendations.
    """
    # Fetch transactions from DB
    transactions = []
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT id, transaction_date, description, amount, transaction_type, category, notes FROM transactions WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            keys = result.keys()
            transactions = [dict(zip(keys, row)) for row in result]
    except Exception as e:
        return {"error": f"Failed to query database: {e}"}

    recommendations = []
    
    # 1. Look for Section 80C potential items
    insurance_tx = [t for t in transactions if any(w in t["description"].lower() for w in ["lic", "insurance", "life insurance"]) and t["transaction_type"] == "DEBIT"]
    if insurance_tx:
        total_ins = sum(t["amount"] for t in insurance_tx)
        recommendations.append({
            "section": "Section 80C",
            "finding": f"I identified {len(insurance_tx)} insurance premium transactions totaling ₹{total_ins:,.2f}.",
            "advice": f"Life insurance premiums are eligible for deduction under Section 80C up to a maximum limit of ₹1,50,000. Ensure you file these in your returns.",
            "transactions": insurance_tx
        })
        
    # 2. Look for Section 80D medical items
    medical_tx = [t for t in transactions if any(w in t["description"].lower() for w in ["medical", "health", "hospital", "pharmeasy", "pharmacy", "doctor"]) and t["transaction_type"] == "DEBIT" and t not in insurance_tx]
    if medical_tx:
        total_med = sum(t["amount"] for t in medical_tx)
        recommendations.append({
            "section": "Section 80D",
            "finding": f"I identified {len(medical_tx)} health/medical transactions totaling ₹{total_med:,.2f}.",
            "advice": "Health insurance premiums and preventive health checkups are deductible under Section 80D. Premium deductions are capped at ₹25,000 (self/family) and ₹50,000 (parents if senior citizens). Preventive health checkup deduction is capped at ₹5,000.",
            "transactions": medical_tx
        })
        
    # 3. Look for Section 44ADA (Software, Internet, Freelance SaaS costs)
    saas_tx = [t for t in transactions if any(w in t["description"].lower() for w in ["aws", "gcp", "github", "cursor", "openai", "software", "subscription", "vercel", "internet", "broadband", "jio", "airtel"]) and t["transaction_type"] == "DEBIT"]
    if saas_tx:
        total_saas = sum(t["amount"] for t in saas_tx)
        recommendations.append({
            "section": "Section 44ADA",
            "finding": f"I found {len(saas_tx)} transactions related to software, SaaS, or internet utilities totaling ₹{total_saas:,.2f}.",
            "advice": "If you file tax as a freelancer/independent professional under the Section 44ADA Presumptive Taxation Scheme, you can declare 50% of your gross income as profit and treat these SaaS and utility expenses as business costs. This significantly reduces your compliance paperwork and overall tax liability.",
            "transactions": saas_tx
        })

    # 4. Look for Rent (Section 80GG)
    rent_tx = [t for t in transactions if "rent" in t["description"].lower() and t["transaction_type"] == "DEBIT"]
    if rent_tx:
        total_rent = sum(t["amount"] for t in rent_tx)
        recommendations.append({
            "section": "Section 80GG",
            "finding": f"I identified rental payment transactions totaling ₹{total_rent:,.2f}.",
            "advice": "If you do not receive HRA (House Rent Allowance) from an employer, you can claim rent deductions under Section 80GG up to ₹5,000 per month (₹60,000 per year) by submitting Form 10BA.",
            "transactions": rent_tx
        })

    # Format the advisory response
    openai_key = os.environ.get("OPENAI_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    
    advisory_intro = "Based on scanning your transaction database, here is your customized tax advisory analysis:"
    
    if not recommendations:
        return {
            "summary": "No specific tax-deductible items were identified in your current transactions list.",
            "recommendations": []
        }
        
    # Synthesize natural language advisory when LLM is available
    if openai_key or gemini_key:
        try:
            summary_prompt = f"""
            You are a professional Indian Tax Advisory agent. Summarize the following findings and advise the user on how they can optimize their tax returns based on their actual transactions.
            
            Findings:
            {json.dumps(recommendations, default=str)}
            
            Keep the advice professional, clear, action-oriented, and cite the respective section numbers.
            """
            
            advisory_text = ""
            if openai_key:
                from openai import OpenAI
                client = OpenAI(api_key=openai_key)
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a professional CA (Chartered Accountant) Tax Advisor."},
                        {"role": "user", "content": summary_prompt}
                    ]
                )
                advisory_text = resp.choices[0].message.content
            elif gemini_key:
                import google.generativeai as genai
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                resp = model.generate_content(summary_prompt)
                advisory_text = resp.text
                
            if advisory_text:
                return {
                    "summary": advisory_text,
                    "recommendations": recommendations
                }
        except Exception as e:
            print(f"Failed to generate LLM advisory summary: {e}")

    # Heuristic presentation if LLM fails/is absent
    text_parts = [advisory_intro]
    for r in recommendations:
        text_parts.append(f"\n### {r['section']}\n- **Finding:** {r['finding']}\n- **Advice:** {r['advice']}")
        
    return {
        "summary": "\n".join(text_parts),
        "recommendations": recommendations
    }
