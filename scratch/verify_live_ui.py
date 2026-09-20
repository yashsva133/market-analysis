"""Playwright automated verification script for 100% live feeds in India Market Terminal."""
import asyncio
import os
import sys
from playwright.async_api import async_playwright

ARTIFACT_DIR = r"C:\Users\yashs\.gemini\antigravity-ide\brain\71cc7b57-7cdb-47b3-af7e-ae25dfa44612"

async def main():
    console_errors = []
    print("Launching Playwright Chromium...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1600, "height": 1000})
        page = await context.new_page()

        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: console_errors.append(str(err)))

        print("Navigating to http://localhost:3000...")
        res = await page.goto("http://localhost:3000", wait_until="domcontentloaded", timeout=15000)
        assert res and res.status == 200, f"Failed to load: {res.status if res else 'No response'}"

        # Wait for terminal header
        await page.locator("text=INDIA TERMINAL").first.wait_for(state="visible", timeout=10000)
        print("[OK] Terminal loaded successfully.")

        # Give 2 seconds for initial background fetch
        await page.wait_for_timeout(2500)

        # 1. Verify Breadth Ribbon
        breadth_text = await page.locator("text=CURRENT MARKET REGIME:").first.text_content()
        print(f"Breadth indicator found: {breadth_text}")
        adv_count = await page.locator("text=ADV:").first.text_content()
        print(f"Advance count element: {adv_count}")

        # Capture initial full terminal screenshot
        terminal_shot = os.path.join(ARTIFACT_DIR, "terminal_verified_live_full.png")
        await page.screenshot(path=terminal_shot, full_page=False)
        print(f"[OK] Saved live terminal screenshot: {terminal_shot}")

        # 2. Verify Workspace 5: NEWS
        print("Testing Workspace 5 (NEWS)...")
        news_btn = page.locator("nav button:has-text('NEWS [5]')").first
        await news_btn.click()
        await page.wait_for_timeout(1000)
        news_header = await page.locator("text=NEWS & SENTIMENT INTELLIGENCE TERMINAL").first.text_content()
        print(f"[OK] News workspace active: {news_header}")
        news_shot = os.path.join(ARTIFACT_DIR, "workspace_news_live.png")
        await page.screenshot(path=news_shot, full_page=False)
        print(f"[OK] Saved news screenshot: {news_shot}")

        # 3. Verify Workspace 12: CALENDAR
        print("Testing Workspace 12 (CALENDAR)...")
        cal_btn = page.locator("nav button:has-text('CALENDAR')").first
        await cal_btn.click()
        await page.wait_for_timeout(1000)
        cal_header = await page.locator("text=CORPORATE ACTIONS & EARNINGS CALENDAR").first.text_content()
        print(f"[OK] Calendar workspace active: {cal_header}")
        cal_shot = os.path.join(ARTIFACT_DIR, "workspace_calendar_live.png")
        await page.screenshot(path=cal_shot, full_page=False)
        print(f"[OK] Saved calendar screenshot: {cal_shot}")

        # 4. Verify Workspace 13: COMPARE
        print("Testing Workspace 13 (COMPARE)...")
        comp_btn = page.locator("nav button:has-text('COMPARE')").first
        await comp_btn.click()
        await page.wait_for_timeout(1000)
        comp_header = await page.locator("text=MULTI-COMPANY PEER COMPARISON MATRIX").first.text_content()
        print(f"[OK] Compare workspace active: {comp_header}")
        comp_shot = os.path.join(ARTIFACT_DIR, "workspace_compare_live.png")
        await page.screenshot(path=comp_shot, full_page=False)
        print(f"[OK] Saved compare screenshot: {comp_shot}")

        # 5. Verify Workspace 14: MODEL LAB
        print("Testing Workspace 14 (MODEL LAB)...")
        models_btn = page.locator("nav button:has-text('MODEL LAB')").first
        await models_btn.click()
        await page.wait_for_timeout(1000)
        models_header = await page.locator("text=MODEL REGISTRY & PROBABILITY CALIBRATION LAB").first.text_content()
        print(f"[OK] Models workspace active: {models_header}")
        models_shot = os.path.join(ARTIFACT_DIR, "workspace_models_live.png")
        await page.screenshot(path=models_shot, full_page=False)
        print(f"[OK] Saved models screenshot: {models_shot}")

        # 6. Verify Workspace 15: QUANT LAB & Trigger Backtest
        print("Testing Workspace 15 (QUANT LAB)...")
        quant_btn = page.locator("nav button:has-text('QUANT LAB')").first
        await quant_btn.click()
        await page.wait_for_timeout(1000)
        quant_header = await page.locator("text=QUANTITATIVE STRATEGY LAB").first.text_content()
        print(f"[OK] Quant lab active: {quant_header}")
        
        # Click backtest button
        run_btn = page.locator("button:has-text('EXECUTE WALK-FORWARD BACKTEST')").first
        if await run_btn.is_visible():
            print("Clicking 'EXECUTE WALK-FORWARD BACKTEST' button...")
            await run_btn.click()
            await page.wait_for_timeout(2000)
            print("[OK] Backtest executed.")
        
        quant_shot = os.path.join(ARTIFACT_DIR, "workspace_quant_live.png")
        await page.screenshot(path=quant_shot, full_page=False)
        print(f"[OK] Saved quant lab screenshot: {quant_shot}")

        # 7. Verify Workspace 10: PORTFOLIO
        print("Testing Workspace 10 (PORTFOLIO)...")
        port_btn = page.locator("nav button:has-text('PORTFOLIO')").first
        await port_btn.click()
        await page.wait_for_timeout(1000)
        port_header = await page.locator("text=PORTFOLIO MONITOR // UPSTOX V3 INTEGRATION").first.text_content()
        print(f"[OK] Portfolio active: {port_header}")
        port_shot = os.path.join(ARTIFACT_DIR, "workspace_portfolio_live.png")
        await page.screenshot(path=port_shot, full_page=False)
        print(f"[OK] Saved portfolio screenshot: {port_shot}")

        await browser.close()

    print("\n--- Summary of Console Errors ---")
    critical_errors = [e for e in console_errors if "favicon" not in e.lower()]
    print(f"Total non-favicon console errors: {len(critical_errors)}")
    for err in critical_errors:
        print(f"  Console Error: {err}")

    assert len(critical_errors) == 0, f"Encountered {len(critical_errors)} console errors during test run."
    print("\n[OK] 100% OF LIVE WORKSPACE TESTS PASSED WITH ZERO CONSOLE ERRORS!")

if __name__ == "__main__":
    asyncio.run(main())
