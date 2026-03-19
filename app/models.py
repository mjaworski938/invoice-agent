from sqlalchemy import Column, String, Float, Integer, ForeignKey, Date
from sqlalchemy.orm import relationship
from .database import Base

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    po_number = Column(String, primary_key=True)
    total_amount = Column(Float)
    vendor_name = Column(String)

class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String)
    vendor_name = Column(String)
    po_number = Column(String)
    total_amount = Column(Float)
    approver = Column(String) 
    status = Column(String)
    summary_memo = Column(String)

    line_items = relationship("JournalLineItem", back_populates="parent_entry")

class JournalLineItem(Base):
    __tablename__ = "journal_line_items"

    id = Column(Integer, primary_key=True, index=True)
    parent_id = Column(Integer, ForeignKey("journal_entries.id"))
    
    description = Column(String)
    amount = Column(Float)
    gl_code = Column(String) 
    treatment = Column(String) 

    parent_entry = relationship("JournalEntry", back_populates="line_items")