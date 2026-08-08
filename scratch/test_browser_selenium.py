import os
import time
from playwright.sync_api import sync_playwright

def main():
    print("==========================================================")
    # Target directory for visual screenshots
    artifacts_dir = r"C:\Users\min2a\.gemini\antigravity-ide\brain\30d13870-8bb4-4041-8492-d0c16bf9a735"
    os.makedirs(artifacts_dir, exist_ok=True)
    
    print(f"Screenshots will be saved to: {artifacts_dir}")
    
    with sync_playwright() as p:
        print("Launching browser...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Set a standard desktop viewport size
        page.set_viewport_size({"width": 1280, "height": 800})
        
        # 1. Navigate to landing page
        url = "http://127.0.0.1:8000/"
        print(f"Navigating to {url}...")
        page.goto(url)
        time.sleep(2)  # Wait for page & candidates list to load
        
        # Capture Landing view
        landing_path = os.path.join(artifacts_dir, "landing_page.png")
        page.screenshot(path=landing_path)
        print(f"Saved: {landing_path}")
        
        # 2. Select Sarah Johnson
        print("Selecting Sarah Johnson...")
        page.select_option("#candidate-select", label="Sarah Johnson (Senior Data Engineer)")
        time.sleep(1)  # wait for transition
        
        # Capture selected state
        select_path = os.path.join(artifacts_dir, "candidate_selected.png")
        page.screenshot(path=select_path)
        print(f"Saved: {select_path}")
        
        # 3. Click start button
        print("Clicking Start button...")
        page.click("#start-interview-btn")
        time.sleep(3)  # wait for REST call and chat load
        
        # Capture chat initial question
        chat_path = os.path.join(artifacts_dir, "chat_initial.png")
        page.screenshot(path=chat_path)
        print(f"Saved: {chat_path}")
        
        # 4. Input candidate response
        print("Submitting candidate response...")
        page.fill("#chat-input", "I built clear constraints, few-shot examples, and zero-shot templates to ensure LLM consistency.")
        page.click("#send-btn")
        time.sleep(3)  # wait for response to load
        
        # Capture chat progression
        chat_prog_path = os.path.join(artifacts_dir, "chat_progress.png")
        page.screenshot(path=chat_prog_path)
        print(f"Saved: {chat_prog_path}")
        
        browser.close()
        print("Browser testing complete!")

if __name__ == "__main__":
    main()
