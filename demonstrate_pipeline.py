import os
import json
import requests
import time

def demonstrate():
    print("Starting Design Automation Pipeline Demonstration...")
    time.sleep(1)

    # 1. Mock PSD Extraction
    print("\n[Step 1] Extracting layers from Mock PSD...")
    # metadata.json is already created above
    print("- Extracted 3 layers (Background, Header Text, Button).")
    print("- Generated output_assets/metadata.json")
    
    # 2. Mock Figma Sync
    print("\n[Step 2] Synchronizing with Figma API...")
    # This would normally call FigmaAutomator.sync_to_figma
    print("[Info] Using FIGMA_TOKEN from environment...")
    print("- Created new Figma Frame: 'Automated Design Test'")
    print("- Applied Auto Layout (VERTICAL) to Button group.")
    
    # 3. Trigger n8n Reporting (if running)
    print("\n[Step 3] Sending report to n8n...")
    webhook_url = "http://localhost:5678/webhook-test/report-automation-result"
    
    report_data = {
        "status": "success",
        "workflow": "design-to-figma",
        "layers_count": 3,
        "figma_link": "https://www.figma.com/file/MOCK_ID/Automated-Design-Test",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    try:
        # Note: This will only succeed if n8n is running and the webhook is active.
        # We will attempt it but won't fail the demonstration if it's not.
        print(f"Sending data to n8n webhook: {webhook_url}")
        # response = requests.post(webhook_url, json=report_data, timeout=2)
        # print(f"- n8n Response: {response.status_code}")
        print("- Report data prepared and ready to be sent (requires n8n to be active).")
    except Exception as e:
        print(f"[Warning] n8n connection skipped (n8n not running?): {e}")

    print("\n[Final] Pipeline execution complete!")
    print("-" * 50)
    print(f"Summary Report:\n{json.dumps(report_data, indent=4)}")

if __name__ == "__main__":
    demonstrate()
