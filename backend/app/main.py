import os
import shutil
from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from backend.app.database import init_db, get_db, DBTransaction
from backend.app.schema import (
    StatementUploadResponse,
    TransactionCreate,
    ChatRequest,
    ChatResponse,
    Transaction
)
from backend.app.parsing import parse_pdf_statement, scrub_pii
from backend.app.categorizer import categorize_transactions
from backend.app.orchestrator import run_orchestrator

# Initialize database
init_db()

app = FastAPI(
    title="Autonomous Financial Agent API",
    description="Production-grade API for transaction parsing, categorization, deterministic spending SQL query, and tax advisory.",
    version="1.0.0"
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    # Make sure database is ready
    init_db()

@app.get("/")
def read_root():
    return {"message": "Autonomous Financial Agent API is running."}

@app.post("/api/upload-statement", response_model=StatementUploadResponse)
def upload_statement(
    file: UploadFile = File(...),
    user_id: str = Form("default_user"),
    db: Session = Depends(get_db)
):
    """
    Uploads a bank statement (PDF), scrubs PII, extracts tables/transactions,
    categorizes them, and saves them to the PostgreSQL/SQLite database.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF bank statements are supported.")

    # Save PDF temporarily
    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, file.filename)
    
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 1. Parse PDF (LlamaParse/pdfplumber)
        raw_markdown = parse_pdf_statement(temp_file_path)
        
        # 2. Scrub PII
        clean_markdown = scrub_pii(raw_markdown)
        
        # 3. Categorize transactions (LLM structured extraction/heuristic fallback)
        parsed_transactions = categorize_transactions(clean_markdown)
        
        # 4. Save to database
        db_records = []
        for tx in parsed_transactions:
            db_tx = DBTransaction(
                user_id=user_id,
                transaction_date=tx.transaction_date,
                description=tx.description,
                amount=tx.amount,
                transaction_type=tx.transaction_type,
                category=tx.category.value,
                notes=tx.notes
            )
            db.add(db_tx)
            db_records.append(tx)
            
        db.commit()
        
        return StatementUploadResponse(
            filename=file.filename,
            status="success",
            transactions_parsed=len(db_records),
            transactions=db_records
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to process statement: {str(e)}")
    finally:
        # Clean up temp file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    """
    Orchestrates routing of user natural language queries between
    conversational assistants, deterministic SQL Agents, and Tax Advisory agents.
    """
    try:
        res = run_orchestrator(
            user_id=request.user_id,
            message=request.message,
            history=request.history
        )
        return ChatResponse(
            response=res["response"],
            agent_used=res["agent_used"],
            sql_query=res.get("sql_query"),
            data=res.get("data")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Orchestrator error: {str(e)}")

@app.get("/api/transactions", response_model=List[Transaction])
def get_transactions(user_id: str = "default_user", db: Session = Depends(get_db)):
    """
    Retrieves all stored transactions for a given user.
    """
    transactions = db.query(DBTransaction).filter(DBTransaction.user_id == user_id).order_by(DBTransaction.transaction_date.desc()).all()
    return transactions

@app.get("/api/tax-advice")
def get_tax_advice_endpoint(user_id: str = "default_user"):
    """
    Retrieves tax advisory recommendations for a given user.
    """
    from backend.app.tax_advisor import get_tax_advisory
    res = get_tax_advisory(user_id)
    if "error" in res:
        raise HTTPException(status_code=500, detail=res["error"])
    return res

@app.post("/api/clear-transactions")
def clear_transactions(user_id: str = "default_user", db: Session = Depends(get_db)):
    """
    Clears transactions for a given user (useful for testing/resets).
    """
    try:
        db.query(DBTransaction).filter(DBTransaction.user_id == user_id).delete()
        db.commit()
        return {"status": "success", "message": f"Cleared all transactions for user: {user_id}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
