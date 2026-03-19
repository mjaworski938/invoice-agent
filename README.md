# Accounts Payable Workflow AI Agent

This agent automates the ingestion, classification, and posting of vendor invoices. It uses AI to determine GL accounts and amortization treatments while enforcing strict business rules for Purchase Order (PO) matching and human oversight.


## Quickstart Guide

### 1. Environment Setup
Clone the repository and set up your virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a .env file in the root directory:
```plaintext
OPENAI_API_KEY=your_key_here
DATABASE_URL=sqlite:///./ap_agent.db
GLOBAL_DRY_RUN=False
```

### 3. Initialize and Run Server
```
python db_reset.py
uvicorn app.main:app --reload
```

### 4. Testing - these test scripts will call the API to demonstrate each functionality

#### Process the 6 Sample Invoices
```
python test_sample_invoices.py
```

- Ingests the sample invoices from `test_cases.json`
- Handles exception for missing PO
- Supports dry-run mode by setting environment variable `GLOBAL_DRY_RUN=True`

#### Process the 10 Shadow Invoices
```
python test_shadow_invoices.py
```

- Ingests the unlabeled invoices from `unlabeled_invoices.json`
- Saves invoices with the status SHADOW_PROPOSAL

#### Human-in-the-Loop Approval
```
python test_human_approval.py
```

- Interactive CLI Lists all entries currently in PENDING_APPROVAL or SHADOW_PROPOSAL
- Type the id of the entry to approve it - update invoice status to "POSTED"

#### Feedback
```
python test_feedback.py
```

- Calls the `/evaluate` endpoint
- Compared current records in db against the ground truth test cases `test_cases.json`
- Displays accuracy score and the invoices the require adjustment

### 5. Data and Config
- `app/ai_context_sop.md`: SOP formatted and used as context for LLM

- `chart_of_accounts.json`: Chart of Accounts, contains GL, name, and category

- `purchase_orders.json`: Purchase orders seed data. Loaded into db and used as reference for PO matching stage

- `test_cases.json`: The 6 labeled invoice test casese 

- `unlabeled_invoices.json`: The unlabeled invoices used to demonstrate shadow processing


### Design Decisions

#### Relational Table Schema
- Journal Entries 
- Journal Line Items    
Separation of the two will make it easier for the business to query and analyze line item data

#### Endpoints
Each of the Main features map to an endpoint logically: 
- Ingest and process an invoice - endpoint
- Approve invoice with human in loop - endpoint
- Evaluate for feedback - endpoint

### AI Prompting
- Treat SOP and chart of Accounts as necessary context items for each LLM call
- Format as text/md and make these separate files convenient to edit