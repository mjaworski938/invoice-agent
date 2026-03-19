import requests

def run_feedback_loop():
    try:
        response = requests.get("http://127.0.0.1:8000/evaluate")
        if response.status_code != 200:
            print(f"Error: API returned {response.status_code}")
            return
            
        data = response.json()
        summary = data.get('summary', {})
        score = summary.get('classification_accuracy', 0)
        details = data.get('details', [])

        print(f"--- System Evaluation Report ---")
        print(f"Current Accuracy: {score}%")

        # Extract only the invoices that failed GL or Treatment matching
        failed_invoices = [
            d['invoice'] for d in details 
            if not d['matches'].get('gl') or not d['matches'].get('treatment')
        ]

        if failed_invoices:
            print(f"Invoices requiring correction: {', '.join(failed_invoices)}")
            print("Status: Refinement needed.")
        else:
            print("Status: All invoices match ground truth.")

    except Exception as e:
        print(f"Failed to run evaluation: {e}")

if __name__ == "__main__":
    run_feedback_loop()