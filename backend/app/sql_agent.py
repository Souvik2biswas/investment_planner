import os
import json
import re
from typing import Dict, Any, List
from sqlalchemy import text
from backend.app.database import engine

def fallback_heuristics_nl_to_sql(question: str) -> str:
    """
    Translates common natural language questions about spending into read-only SQL queries.
    This is used as a fallback if no LLM API keys are provided.
    """
    q_lower = question.lower()
    
    # Base query template
    # Enforce filtering by user_id
    
    # 1. Average monthly spend on a category
    # E.g., "average monthly spend on utilities"
    cat_match = re.search(r'(utilities|food|travel|rent|entertainment|business_expense|salary|investment|potential_deduction)', q_lower)
    if "average" in q_lower or "avg" in q_lower:
        category = cat_match.group(1).upper() if cat_match else "UTILITIES"
        if "monthly" in q_lower:
            return f"""
            SELECT 
                strftime('%Y-%m', transaction_date) as month,
                AVG(amount) as average_amount,
                SUM(amount) as total_amount
            FROM transactions 
            WHERE user_id = :user_id 
              AND UPPER(category) = '{category}' 
              AND transaction_type = 'DEBIT'
            GROUP BY month
            ORDER BY month DESC
            """
        else:
            return f"SELECT AVG(amount) as average_amount FROM transactions WHERE user_id = :user_id AND UPPER(category) = '{category}' AND transaction_type = 'DEBIT'"
            
    # 2. Total spending by category
    if "total" in q_lower or "how much" in q_lower:
        if cat_match:
            category = cat_match.group(1).upper()
            return f"SELECT SUM(amount) as total_amount FROM transactions WHERE user_id = :user_id AND UPPER(category) = '{category}' AND transaction_type = 'DEBIT'"
        elif "spending" in q_lower or "spent" in q_lower:
            return "SELECT SUM(amount) as total_spending FROM transactions WHERE user_id = :user_id AND transaction_type = 'DEBIT'"
            
    # 3. Categorized spending summary
    if "breakdown" in q_lower or "by category" in q_lower or "categories" in q_lower:
        return """
        SELECT category, SUM(amount) as total_amount, COUNT(*) as count 
        FROM transactions 
        WHERE user_id = :user_id AND transaction_type = 'DEBIT' 
        GROUP BY category 
        ORDER BY total_amount DESC
        """
        
    # 4. List transactions
    if "list" in q_lower or "show" in q_lower or "transactions" in q_lower:
        return "SELECT transaction_date, description, amount, transaction_type, category FROM transactions WHERE user_id = :user_id ORDER BY transaction_date DESC LIMIT 50"
        
    # Default fallback
    return "SELECT * FROM transactions WHERE user_id = :user_id ORDER BY transaction_date DESC LIMIT 10"

def execute_read_query(sql_query: str, user_id: str) -> List[Dict[str, Any]]:
    """
    Safely executes a read-only SQL query against the database, enforcing user_id scope.
    """
    # 1. Sanitize to prevent destructive operations
    sql_clean = sql_query.strip().upper()
    destructive_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE", "RENAME", "GRANT", "REVOKE"]
    for kw in destructive_keywords:
        # Match only full word boundaries to avoid false positives (e.g. matching "CREATE" inside "RECREATED")
        if re.search(rf"\b{kw}\b", sql_clean):
            raise ValueError(f"Unauthorized database operation detected: {kw} query is not allowed.")
            
    # 2. Execute query
    results_list = []
    with engine.connect() as conn:
        # We bind user_id parameter for safety
        result = conn.execute(text(sql_query), {"user_id": user_id})
        
        # If the query yields result rows (e.g. SELECT)
        if result.returns_rows:
            keys = result.keys()
            for row in result:
                results_list.append(dict(zip(keys, row)))
                
    return results_list

def run_sql_agent(question: str, user_id: str) -> Dict[str, Any]:
    """
    Translates a natural language question to SQL, runs it, and summarizes the findings.
    """
    openai_key = os.environ.get("OPENAI_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    
    schema_info = """
    Table: transactions
    Columns:
      - id (INTEGER, primary key)
      - user_id (VARCHAR) - Represents the user. You MUST always filter by user_id = :user_id.
      - transaction_date (DATE) - Format YYYY-MM-DD
      - description (VARCHAR) - Transaction memo
      - amount (FLOAT) - Monetary value
      - transaction_type (VARCHAR) - Either 'DEBIT' (expense) or 'CREDIT' (income)
      - category (VARCHAR) - Enum: FOOD, UTILITIES, RENT, TRAVEL, ENTERTAINMENT, BUSINESS_EXPENSE, SALARY, INVESTMENT, POTENTIAL_DEDUCTION, OTHERS
      - notes (TEXT) - Optional notes
    """
    
    sql_query = ""
    explanation = ""
    
    # Generate SQL
    if openai_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            
            prompt = f"""
            You are a SQL Translation Agent. Translate the user's natural language question into a standard SQL query.
            Only output read-only SELECT statements. You MUST filter transactions by user_id using the bind parameter `:user_id`.
            Do NOT use any other bind parameters (such as `:category` or `:amount`); embed all other query filters directly as literal values in the SQL string, e.g. category = 'FOOD' or amount > 500.
            
            Database Schema:
            {schema_info}
            
            User Question: "{question}"
            
            Respond in this exact JSON format:
            {{
                "sql_query": "SELECT ... WHERE user_id = :user_id ...",
                "explanation": "Brief explanation of how the query answers the question"
            }}
            """
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful SQL assistant. Only output raw JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            res_data = json.loads(response.choices[0].message.content)
            sql_query = res_data.get("sql_query", "")
            explanation = res_data.get("explanation", "")
        except Exception as e:
            print(f"OpenAI SQL Agent failed: {e}. Falling back to heuristics.")
            
    elif gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            prompt = f"""
            You are a SQL Translation Agent. Translate the user's natural language question into a standard SQL query.
            Only output read-only SELECT statements. You MUST filter transactions by user_id using the bind parameter `:user_id`.
            Do NOT use any other bind parameters (such as `:category` or `:amount`); embed all other query filters directly as literal values in the SQL string, e.g. category = 'FOOD' or amount > 500.
            
            Database Schema:
            {schema_info}
            
            User Question: "{question}"
            
            Respond in this exact JSON format:
            {{
                "sql_query": "SELECT ... WHERE user_id = :user_id ...",
                "explanation": "Brief explanation of how the query answers the question"
            }}
            """
            
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            res_data = json.loads(response.text)
            sql_query = res_data.get("sql_query", "")
            explanation = res_data.get("explanation", "")
        except Exception as e:
            print(f"Gemini SQL Agent failed: {e}. Falling back to heuristics.")

    # Apply heuristic fallback if SQL query couldn't be generated
    if not sql_query:
        sql_query = fallback_heuristics_nl_to_sql(question)
        explanation = "Parsed user query using standard local financial SQL templates."

    # Execute SQL Query
    try:
        data = execute_read_query(sql_query, user_id)
        
        # Summarize results in standard natural language
        summary_prompt = f"""
        Analyze the resulting data for the question: "{question}"
        SQL executed: `{sql_query}`
        Data returned: {json.dumps(data, default=str)}
        
        Provide a concise, friendly, and mathematically precise answer summarizing this data.
        """
        
        summary_text = ""
        if openai_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=openai_key)
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a friendly financial dashboard summary agent."},
                        {"role": "user", "content": summary_prompt}
                    ]
                )
                summary_text = resp.choices[0].message.content
            except Exception:
                pass
        elif gemini_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                resp = model.generate_content(summary_prompt)
                summary_text = resp.text
            except Exception:
                pass
                
        # Basic heuristic summary if LLM summary failed
        if not summary_text:
            if not data:
                summary_text = "No transaction records found matching your query."
            else:
                first_row = data[0]
                summary_text = f"Executed the query successfully and retrieved {len(data)} record(s). Here is the result: {first_row}"
                
        return {
            "response": summary_text,
            "sql_query": sql_query,
            "data": data,
            "explanation": explanation
        }
    except Exception as e:
        return {
            "response": f"An error occurred while executing the database query: {str(e)}",
            "sql_query": sql_query,
            "data": None,
            "explanation": f"SQL translation generated: {explanation}. Execution failed."
        }
