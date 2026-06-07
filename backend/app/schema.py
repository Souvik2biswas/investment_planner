from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date

class TransactionCategory(str, Enum):
    FOOD = "FOOD"
    UTILITIES = "UTILITIES"
    RENT = "RENT"
    TRAVEL = "TRAVEL"
    ENTERTAINMENT = "ENTERTAINMENT"
    BUSINESS_EXPENSE = "BUSINESS_EXPENSE"
    SALARY = "SALARY"
    INVESTMENT = "INVESTMENT"
    POTENTIAL_DEDUCTION = "POTENTIAL_DEDUCTION"
    OTHERS = "OTHERS"

class TransactionBase(BaseModel):
    transaction_date: date = Field(..., description="The date of the transaction")
    description: str = Field(..., description="Cleaned description of the transaction")
    amount: float = Field(..., description="The monetary amount of the transaction (positive for expense/income, depending on type)")
    transaction_type: str = Field(..., description="DEBIT or CREDIT")
    category: TransactionCategory = Field(default=TransactionCategory.OTHERS, description="The classified category")
    notes: Optional[str] = Field(None, description="Any additional context, flags (e.g., potential tax deductions)")

class TransactionCreate(TransactionBase):
    pass

class Transaction(TransactionBase):
    id: int
    user_id: str

    class Config:
        from_attributes = True

class StatementUploadResponse(BaseModel):
    filename: str
    status: str
    transactions_parsed: int
    transactions: List[TransactionBase]

class ChatMessage(BaseModel):
    role: str = Field(..., description="user or assistant")
    content: str = Field(..., description="The message content")

class ChatRequest(BaseModel):
    user_id: str
    message: str
    history: List[ChatMessage] = Field(default_factory=list)

class ChatResponse(BaseModel):
    response: str
    agent_used: str  # e.g., "orchestrator", "sql_agent", "tax_advisor"
    sql_query: Optional[str] = None
    data: Optional[List[dict]] = None
