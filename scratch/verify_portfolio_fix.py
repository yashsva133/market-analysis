import sys
import io

# Force UTF-8 on Windows stdout/stderr
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        
        print("Navigating to http://localhost:3000...")
        page.goto("http://localhost:3000", wait_until="networkidle", timeout=30000)
        
        # Click on the PORTFOLIO tab button
        print("Switching to PORTFOLIO workspace...")
        portfolio_btn = page.locator("button:has-text('PORTFOLIO')")
        portfolio_btn.click()
        page.wait_for_timeout(2000)
        
        # Verify Portfolio Header
        header = page.locator("h2:has-text('PORTFOLIO MONITOR // UPSTOX V3 INTEGRATION')")
        if not header.is_visible():
            print("ERROR: Portfolio Monitor header not visible")
            sys.exit(1)
        print("SUCCESS: Portfolio Monitor header visible")
        
        # Extract Summary Cards
        summary_cards = page.locator("div[style*='grid-template-columns: repeat(4, 1fr)'] > div")
        card_count = summary_cards.count()
        print(f"Summary cards found: {card_count}")
        
        for i in range(card_count):
            card_text = summary_cards.nth(i).inner_text()
            print(f"Card {i+1}:\n{card_text}\n---")
            
        # Verify Total P&L text
        pnl_card = summary_cards.nth(2)
        pnl_text = pnl_card.inner_text()
        print(f"Extracted Total P&L Card: {repr(pnl_text)}")
        
        if "+-" in pnl_text or "+₹-" in pnl_text:
            print(f"ERROR: Double sign found in Total P&L card: {pnl_text}")
            sys.exit(1)
            
        if "(+3.07%)" in pnl_text:
            print(f"ERROR: Hardcoded (+3.07%) found in Total P&L card: {pnl_text}")
            sys.exit(1)
            
        if "-₹191.40" not in pnl_text or "-4.30%" not in pnl_text:
            print(f"WARNING: Expected -₹191.40 (-4.30%) in card text, got: {pnl_text}")
            
        # Check Holdings Table
        rows = page.locator("table tbody tr")
        row_count = rows.count()
        print(f"Holdings rows found: {row_count}")
        
        for r in range(row_count):
            row_text = rows.nth(r).inner_text().replace("\t", " | ")
            print(f"Row {r+1}: {row_text}")
            if "+-" in row_text:
                print(f"ERROR: Double sign '+-' detected in row {r+1}: {row_text}")
                sys.exit(1)
                
        # Take screenshot
        screenshot_path = r"C:\Users\yashs\.gemini\antigravity-ide\brain\71cc7b57-7cdb-47b3-af7e-ae25dfa44612\portfolio_fixed_live.png"
        page.screenshot(path=screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")
        
        print("Console errors:", console_errors)
        browser.close()

if __name__ == "__main__":
    run()
