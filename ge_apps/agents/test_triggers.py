"""Executes integration tests for the workflow and no-code triggers.

Runs both trigger scripts sequentially to verify their execution.
"""

def run_tests():
    """Runs the no-code and workflow trigger scripts sequentially."""
    print("--- Starting Integration Tests ---")
    
    try:
        print("Executing No-Code Trigger...")
        import trigger_nocode
        trigger_nocode.trigger_nocode()
        print("[PASS] No-Code Trigger executed.")
    except Exception as e:
        print(f"[FAIL] No-Code Trigger failed: {e}")
        
    print("\n" + "="*40 + "\n")
    
    try:
        print("Executing Workflow Trigger...")
        import trigger_workflow
        trigger_workflow.trigger_workflow()
        print("[PASS] Workflow Trigger executed.")
    except Exception as e:
        print(f"[FAIL] Workflow Trigger failed: {e}")

if __name__ == "__main__":
    run_tests()
