import subprocess
import time
import sys
import socket
import os
from playwright.sync_api import sync_playwright

def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def main():
    port = 3005
    web_dir = os.path.join(os.path.dirname(__file__), "..", "apps", "web")
    web_dir = os.path.abspath(web_dir)

    print(f"Starting Next.js production server on port {port} from {web_dir}...")
    # On Windows, use npx next start or npm run start
    server_process = subprocess.Popen(
        f"npx next start -p {port}",
        cwd=web_dir,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Wait for server to become ready
    start_time = time.time()
    ready = False
    while time.time() - start_time < 30:
        if is_port_open(port):
            ready = True
            break
        time.sleep(1)

    if not ready:
        print("ERROR: Server failed to start within 30 seconds.")
        server_process.terminate()
        sys.exit(1)

    print(f"Server is responding on port {port}. Running Playwright headless test...")
    console_errors = []
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 900})
            page = context.new_page()

            # Track console errors
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
            page.on("pageerror", lambda err: console_errors.append(str(err)))

            # Navigate to terminal UI
            page.goto(f"http://localhost:{port}", wait_until="networkidle")
            print("Page loaded successfully.")

            # Validate header
            title = page.title()
            print(f"Page Title: {title}")
            assert "terminal" in title.lower(), f"Unexpected title: {title}"

            # Check for header elements
            header = page.locator("header")
            assert header.is_visible(), "Header is not visible"
            header_text = header.inner_text()
            assert "INDIA TERMINAL" in header_text, f"Header text mismatch: {header_text}"
            assert "5,182" in header_text or "ISIN" in header_text, "Universe stats missing in header"
            print("Header verified successfully.")

            # Check market status clock
            assert "NSE/BSE" in header_text, "Market status indicator not found in header"
            print("Market status indicator verified.")

            # Verify Tab Switching & Deep Interactions
            tabs = [
                ("DASHBOARD", "REAL-TIME MATERIAL EVENTS FEED"),
                ("EQUITY UNIVERSE", "INDIAN LISTED EQUITY UNIVERSE"),
                ("EVENT STREAM", "ALL CORPORATE EVENTS"),
                ("AI RESEARCH DESK", "AI DEEP RESEARCH DESK"),
                ("SOURCE HEALTH", "DATA SOURCE REGISTRY"),
            ]
            for tab_label, expected_heading in tabs:
                tab_btn = page.locator(f"button:has-text('{tab_label}')").first
                assert tab_btn.is_visible(), f"Tab button '{tab_label}' not visible"
                tab_btn.click()
                time.sleep(0.5)
                # Verify tab view rendered
                assert page.locator(f"text={expected_heading}").first.is_visible(), f"Heading '{expected_heading}' not visible after clicking '{tab_label}'"
                print(f"Tab '{tab_label}' verified with content heading: {expected_heading}")

            # Save dashboard screenshot first
            page.locator("button:has-text('DASHBOARD')").first.click()
            time.sleep(0.5)
            artifact_dir = r"C:\Users\yashs\.gemini\antigravity-ide\brain\71cc7b57-7cdb-47b3-af7e-ae25dfa44612"
            dashboard_screenshot_path = os.path.join(artifact_dir, "dashboard_ui.png")
            page.screenshot(path=dashboard_screenshot_path, full_page=True)
            print(f"Dashboard screenshot saved to: {dashboard_screenshot_path}")

            # Switch to research and generate dossier
            research_tab = page.locator("button:has-text('AI RESEARCH DESK')").first
            research_tab.click()
            time.sleep(0.5)
            generate_btn = page.locator("button:has-text('CONDUCT RESEARCH')").first
            if generate_btn.is_visible():
                generate_btn.click()
                dossier_elem = page.wait_for_selector("text=STRUCTURED RESEARCH DOSSIER", timeout=5000)
                assert dossier_elem is not None, "Research dossier output not visible after generation"
                print("AI Research dossier generation interaction verified.")

            # Save dossier screenshot
            dossier_screenshot_path = os.path.join(artifact_dir, "dossier_ui.png")
            page.screenshot(path=dossier_screenshot_path, full_page=True)
            print(f"Dossier screenshot saved to: {dossier_screenshot_path}")

            # Save full terminal screenshot
            screenshot_path = os.path.join(artifact_dir, "terminal_ui.png")
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"Full terminal screenshot saved to: {screenshot_path}")

            browser.close()
    finally:
        print("Stopping Next.js server...")
        # Kill the server process and its children on Windows
        subprocess.run(f"taskkill /F /T /PID {server_process.pid}", shell=True, capture_output=True)

    if console_errors:
        print(f"WARNING: Captured console errors: {console_errors}")
    else:
        print("Zero console errors captured.")

    print("Playwright UI verification SUCCESSFUL!")

if __name__ == "__main__":
    main()
