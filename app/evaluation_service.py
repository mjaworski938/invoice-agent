import json
from sqlalchemy.orm import Session
from app.models import JournalEntry

class EvaluationService:
    @staticmethod
    def get_accuracy_report(db: Session):
        # Load ground truth
        with open("test_cases.json", "r", encoding="utf-8") as f:
            ground_truth_list = json.load(f)
            ground_truth = {inv["invoice_number"]: inv for inv in ground_truth_list}

        # Get processed journal entries from db
        results = db.query(JournalEntry).filter(
            JournalEntry.invoice_number.in_(list(ground_truth.keys()))
        ).all()

        if not results:
            return None

        metrics = {"gl": 0, "treat": 0, "logic": 0, "total": len(results)}
        details = []

        for entry in results:
            truth = ground_truth.get(entry.invoice_number)
            if not truth or not entry.line_items:
                continue

            db_lines = entry.line_items
            true_lines = truth.get("line_items", [])

            # Validate invoice by checking line-items
            invoice_gl_match = True
            invoice_treat_match = True

            # Check for obvious mismatch
            if len(db_lines) != len(true_lines):
                invoice_gl_match = False
                invoice_treat_match = False
            else:
                for db_line, true_line in zip(db_lines, true_lines):
                    expected_gl = str(true_line.get("expected_gl") or true_line.get("gl_code"))
                    expected_tr = true_line.get("expected_treatment") or true_line.get("treatment") or true_line.get("amortization_treatment")

                    if str(db_line.gl_code) != expected_gl:
                        invoice_gl_match = False
                    if db_line.treatment != expected_tr:
                        invoice_treat_match = False

            # If JSON says needs_review, status MUST be PENDING_APPROVAL or SHADOW_PROPOSAL
            exp_needs_review = truth.get("needs_human_review", False)

            # Check for record that are labelled as "POSTED" but require approval
            is_logic_correct = True
            if exp_needs_review and entry.status == "POSTED":
                is_logic_correct = False
            elif not exp_needs_review and entry.status == "PENDING_APPROVAL":
                # Check for false "needs review" status 
                is_logic_correct = False

            # Update Metrics
            if invoice_gl_match: metrics["gl"] += 1
            if invoice_treat_match: metrics["treat"] += 1
            if is_logic_correct: metrics["logic"] += 1

            details.append({
                "invoice": entry.invoice_number,
                "line_count_match": len(db_lines) == len(true_lines),
                "matches": {
                    "gl": invoice_gl_match, 
                    "treatment": invoice_treat_match, 
                    "logic": is_logic_correct
                }
            })

        return {
            "summary": {
                "classification_accuracy": f"{(metrics['gl']/metrics['total'])*100:.1f}%",
                "treatment_accuracy": f"{(metrics['treat']/metrics['total'])*100:.1f}%",
                "approval_accuracy": f"{(metrics['logic']/metrics['total'])*100:.1f}%"
            },
            "details": details
        }