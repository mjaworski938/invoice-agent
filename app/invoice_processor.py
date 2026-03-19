import json
from openai import OpenAI
from sqlalchemy import or_
from sqlalchemy.orm import Session
from .models import PurchaseOrder, JournalEntry, JournalLineItem
from .schemas import InvoiceRequest, AIAnalysisResult

class InvoiceProcessor:
    def __init__(self, db: Session, chat_client: OpenAI, coa: str, sop: str):
        self.db = db
        self.client = chat_client
        self.coa = coa
        self.sop = sop

    def match_po(self, invoice: InvoiceRequest):
        """Step 1"""
        db_po = self.db.query(PurchaseOrder).filter(
            PurchaseOrder.po_number == invoice.po_number
        ).first()
        
        if not db_po:
            return False, "PO not found"
            
        margin = db_po.total_amount * 0.10
        if abs(invoice.total - db_po.total_amount) > margin:
            return False, f"Price variance > 10% (PO: {db_po.total_amount})"
            
        return True, "Match"

    async def ai_analyze_invoice(self, invoice: InvoiceRequest):
        """Steps 2, 3, and 4"""
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "record_invoice_action",
                    "description": "Apply all SOP steps to the invoice.",
                    "parameters": AIAnalysisResult.model_json_schema() 
                }
            }
        ]

        invoice_json = invoice.model_dump_json(
            exclude={
                "line_items": {
                    "__all__": {"expected_gl", "treatment"}
                }
            }
        )

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": f"Follow this SOP exactly: {self.sop}. Use this Chart of Accounts for reference as well: {self.coa}"},
                {"role": "user", "content": f"Process this invoice: {invoice.model_dump_json()}"}
            ],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "record_invoice_action"}}
        )
        
        ai_arguments_hydrated = response.choices[0].message.tool_calls[0].function.arguments
        ai_result = AIAnalysisResult.model_validate_json(ai_arguments_hydrated)
        return ai_result
    
    def save_entry(self, invoice: InvoiceRequest, ai_data: AIAnalysisResult, status: str):
        new_header = JournalEntry(
            invoice_number=invoice.invoice_number,
            vendor_name=invoice.vendor_name,
            po_number=invoice.po_number,
            total_amount=invoice.total,
            status=status,
            approver=ai_data.approver_role,
            summary_memo=ai_data.summary_memo
        )
        
        self.db.add(new_header)
        self.db.flush()

        for item in ai_data.line_items:
            new_line = JournalLineItem(
                parent_id=new_header.id,
                description=item.description,
                gl_code=item.gl_code,
                amount=item.amount,
                treatment=item.treatment
            )
            self.db.add(new_line)

        try:
            self.db.commit()
            return new_header
        except Exception as e:
            self.db.rollback()
            raise e

    # Main workflow
    async def process_invoice(self, invoice: InvoiceRequest, dry_run: bool = False, shadow: bool = False):
        # Match PO and validate amount
        is_valid, msg = self.match_po(invoice)
        if not is_valid:
            status = "FLAGGED"
            
            # Record flagged entry
            if not dry_run:
                flagged_entry = JournalEntry(
                    invoice_number=invoice.invoice_number,
                    vendor_name=invoice.vendor_name,
                    total_amount=invoice.total,
                    status=status
                )
                self.db.add(flagged_entry)
                self.db.commit()
                
            return {
                "status": status, 
                "message": f"Manual Review Required: {msg}",
                "details": None  # No AI items generated
            }

        # Give Invoice to LLM
        ai_data = await self.ai_analyze_invoice(invoice)
        
        # Verify line items total
        line_sum = sum(item.amount for item in invoice.line_items)
        if abs(line_sum - invoice.total) > 0.01:
            return {"status": "FLAGGED", "reason": "Line items don't match total"}

        if shadow:
            status = "SHADOW_PROPOSAL"
        else:
            status = "PENDING_APPROVAL" if ai_data.needs_human_review else "POSTED"
        
        if not dry_run:
            self.save_entry(invoice, ai_data, status)

        return {"status": status, "details": ai_data}
    
    async def approve_invoice(self, db: Session, invoice_number: str):
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

        # 3. Explicitly update and commit
        entry.status = "POSTED"
        db.add(entry) # Ensure SQLAlchemy tracks the change
        db.commit()
        db.refresh(entry) # Pull the fresh state from the DB