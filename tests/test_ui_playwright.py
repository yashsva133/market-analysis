"""Playwright automated headless UI verification for India Market AI Research Terminal."""
import pytest
import os
from playwright.async_api import async_playwright


@pytest.mark.asyncio
async def test_terminal_ui_playwright():
    """Verify terminal UI renders properly, navigation works across all 18 workspaces, and zero console errors occur."""
    console_errors = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        # Listen for console errors
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: console_errors.append(str(err)))

        # Navigate to local web app using domcontentloaded to accommodate live polling
        response = await page.goto("http://localhost:3000", wait_until="domcontentloaded", timeout=15000)
        assert response is not None
        assert response.status == 200

        # Verify Header Title
        title_elem = page.locator("text=INDIA TERMINAL")
        await title_elem.wait_for(state="visible", timeout=8000)

        # All 18 Workspaces across Intelligence Desks, Quant & Portfolio, and System & Audit
        workspaces = [
            "MARKET [1]",
            "UNIVERSE [2]",
            "COMPANY [3]",
            "EVENTS [4]",
            "NEWS [5]",
            "SCREENER [6]",
            "RESEARCH [7]",
            "SCENARIO [8]",
            "WATCHLIST [9]",
            "PORTFOLIO",
            "TECHNICALS",
            "CALENDAR",
            "COMPARE",
            "MODEL LAB",
            "QUANT LAB",
            "DATA EXPLORER",
            "SOURCE HEALTH",
            "ALERTS & TELEGRAM",
        ]

        for ws in workspaces:
            button = page.locator(f"nav button:has-text('{ws}')").first
            await button.scroll_into_view_if_needed()
            await button.click()
            await page.wait_for_timeout(200)

        # Specifically verify SCENARIO [8] workspace components
        scenario_btn = page.locator("nav button:has-text('SCENARIO [8]')").first
        await scenario_btn.scroll_into_view_if_needed()
        await scenario_btn.click()
        await page.wait_for_timeout(1000)

        # Verify Scenario UI elements and execute scenario run
        await page.wait_for_selector("text=AI CAPITAL ANALYST", timeout=5000)
        run_btn = page.locator("button:has-text('RUN SCENARIO')").first
        await run_btn.click()
        await page.wait_for_timeout(2000)

        # 1. Verify Google TimesFM 3.0 and Chronos-2 Comparison Panel
        await page.wait_for_selector("text=GOOGLE TIMESFM 3.0", timeout=8000)
        await page.wait_for_selector("text=AMAZON CHRONOS-2", timeout=8000)
        await page.wait_for_selector("text=FOUNDATION TIME-SERIES COMPARISON", timeout=8000)

        # 2. Verify Multi-Agent Decision Council Deliberation Section
        await page.wait_for_selector("text=INSTITUTIONAL MULTI-AGENT DECISION COUNCIL", timeout=8000)
        await page.wait_for_selector("text=COUNCIL VERDICT", timeout=8000)
        await page.wait_for_selector("text=Alpha Forecaster", timeout=8000)
        await page.wait_for_selector("text=Graham-Bachelier Analyst", timeout=8000)
        await page.wait_for_selector("text=SEBI LODR Auditor", timeout=8000)
        await page.wait_for_selector("text=Capital Preservation Officer", timeout=8000)
        await page.wait_for_selector("text=OBJECTIVE INVALIDATION TRIGGERS", timeout=8000)

        # 3. Verify Model Lab has Google TimesFM 3.0 registered
        models_btn = page.locator("nav button:has-text('MODEL LAB')").first
        await models_btn.scroll_into_view_if_needed()
        await models_btn.click()
        await page.wait_for_timeout(500)
        await page.wait_for_selector("text=google-timesfm-3.0", timeout=5000)

        # Return to Scenario tab for final screenshot
        await scenario_btn.click()
        await page.wait_for_timeout(500)

        # Capture artifact screenshot in docs and IDE brain directory
        artifact_dir = os.path.join(os.getcwd(), "docs")
        os.makedirs(artifact_dir, exist_ok=True)
        screenshot_path = os.path.join(artifact_dir, "terminal_verified.png")
        await page.screenshot(path=screenshot_path, full_page=True)

        ide_brain_dir = r"C:\Users\yashs\.gemini\antigravity-ide\brain\71cc7b57-7cdb-47b3-af7e-ae25dfa44612"
        if os.path.isdir(ide_brain_dir):
            await page.screenshot(path=os.path.join(ide_brain_dir, "terminal_verified.png"), full_page=True)

        await browser.close()

    # Filter benign external network issues or favicon warnings
    fatal_errors = [
        e for e in console_errors
        if "favicon" not in e.lower()
        and "failed to load resource" not in e.lower()
    ]
    assert len(fatal_errors) == 0, f"Encountered page/console errors: {fatal_errors}"

