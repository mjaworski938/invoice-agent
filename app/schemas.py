from pydantic import BaseModel, Field
from typing import List, Optional

class LineItem(BaseModel):
    description: str
    amount: float
    expected_gl: Optional[int]
    treatment: str

class InvoiceRequest(BaseModel):
    invoice_number: str
    vendor_name: str
    po_number: Optional[str] = None
    date: str
    dept: str
    total: float
    line_items: List[LineItem]

    class Config:
        from_attributes = True

class AIAnalysisLineItem(BaseModel):
    description: str = Field(..., description="The original line item description")
    gl_code: str = Field(..., description="The 4-digit GL code (e.g., 5010, 1310) based on SOP Step 2")
    treatment: str = Field(..., description="The accounting treatment explanation (e.g., 'Immediate Expense' or 'Amortize $2k/mo') based on SOP Step 3")
    amount: float = Field(..., description="The dollar amount for this specific line")

class AIAnalysisResult(BaseModel):
    line_items: List[AIAnalysisLineItem]
    total_invoice_amount: float = Field(..., description="The sum total of all line items")
    approver_role: str = Field(..., description="The required approver based on the Threshold Table in SOP Step 4 (e.g., Manager, VP of Finance)")
    needs_human_review: bool = Field(..., description="Set to True if the total amount exceeds the auto-approval threshold for the department")
    summary_memo: str = Field(..., description="A brief internal note explaining the reasoning for this classification")

class ProcessingResponse(BaseModel):
    status: str = Field(..., description="POSTED, PENDING_APPROVAL, or FLAGGED")
    message: str = Field(..., description="Human-readable explanation of the result")
    data: Optional[AIAnalysisResult] = None 
    error_details: Optional[str] = None

    class Config:
        from_attributes = True