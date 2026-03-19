import json
import os
import math
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import  Session
from .models import PurchaseOrder, JournalEntry
from .invoice_processor import InvoiceProcessor
from .schemas import InvoiceRequest, ProcessingResponse
from openai import OpenAI
from sqlalchemy import or_
from .evaluation_service import EvaluationService

from dotenv import load_dotenv
load_dotenv()

from .database import engine, Base, SessionLocal

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)
if not api_key:
    raise ValueError("OPENAI_API_KEY missing from .env file.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))


    # seed purchase orders data so we can do the match
    if not db.query(PurchaseOrder).first():
        # file_path = os.path.join(os.path.dirname(__file__), "seed_data.json")
        po_seed_path =  os.path.join(BASE_DIR, "purchase_orders.json")
        with open(po_seed_path, "r") as f:
            data = json.load(f)
            for po in data:
                new_po = PurchaseOrder(**po)
                db.add(new_po)
            db.commit()
    db.close()

    coa_path = os.path.join(BASE_DIR, "chart_of_accounts.json")
    with open(coa_path, "r") as f:
        APP_CONTEXT["chart_of_accounts"] = json.load(f)
    
    sop_path = os.path.join(BASE_DIR, "ai_context_sop.md")
    with open(sop_path, "r") as f:
        APP_CONTEXT["sop_text"] = f.read()

    yield

    APP_CONTEXT.clear()

app = FastAPI(lifespan=lifespan)

APP_CONTEXT = {}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def health_check():
    return {"status": "alive"}


@app.post("/process-invoice/", response_model=ProcessingResponse)
async def process_invoice(
    invoice: InvoiceRequest, 
    dry_run: bool = False, 
    shadow: bool = False,
    db: Session = Depends(get_db)
):
    processor = InvoiceProcessor(db, client, coa=APP_CONTEXT["chart_of_accounts"], sop=APP_CONTEXT["sop_text"])
    
    result = await processor.process_invoice(invoice, dry_run=dry_run, shadow=shadow)
    
    if result["status"] == "FLAGGED":
        return {
            "status": "FLAGGED",
            "message": result.get("reason", "Invoice not validated"),
            "data": None
        }

    success_msg = "Processing Completed Successfully"

    if dry_run:
        success_msg += " (DRY RUN - No Database Write)"

    return {
        "status": result["status"], 
        "message": success_msg,
        "data": result["details"]
    }

@app.get("/evaluate")
async def evaluate_performance(db: Session = Depends(get_db)):

    # Exit gracefully on empty db
    actuals = db.query(JournalEntry).all()
    if not actuals:
        return {
            "summary": {"classification_accuracy": 0.0},
            "details": [],
            "message": "No data in database to evaluate."
        }


    report = EvaluationService.get_accuracy_report(db)
    
    if not report:
        raise HTTPException(status_code=404, detail="No labeled invoices found to evaluate.")
        
    return report

@app.post("/approve-invoice/{invoice_number}")
async def approve_invoice(invoice_number: str, db: Session = Depends(get_db)):
    entry = db.query(JournalEntry).filter(
        JournalEntry.invoice_number == invoice_number,
        or_(
            JournalEntry.status == "PENDING_APPROVAL",
            JournalEntry.status == "SHADOW_PROPOSAL"
        )
    ).first()

    if not entry:
        already_posted = db.query(JournalEntry).filter(
            JournalEntry.invoice_number == invoice_number,
            JournalEntry.status == "POSTED"
        ).first()
        
        detail_msg = f"Invoice {invoice_number} not found in a pending/shadow state."
        if already_posted:
            detail_msg = f"Invoice {invoice_number} is already POSTED."
            
        raise HTTPException(status_code=404, detail=detail_msg)

    # Update and commit
    entry.status = "POSTED"
    db.add(entry) 
    db.commit()
    db.refresh(entry) 
    
    return {
        "status": "SUCCESS", 
        "message": f"Invoice {invoice_number} promoted to POSTED.",
        "new_status": entry.status
    }