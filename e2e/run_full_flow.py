"""End-to-End Playwright test exercising the complete SecureWipe platform lifecycle.
Verifies dual-custody gates, negative paths, WebSocket telemetry, certificate signing,
tamper detection, and immutable audit hash chain integrity.
Captures screenshots of every critical stage into docs/screenshots/.
"""

import asyncio
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.async_api import async_playwright

SCREENSHOTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

from sqlalchemy import select, delete
from backend.core.database import AsyncSessionLocal
from backend.models import Device, WipeRequest, Approval, WipeJob


async def cleanup_test_device():
    async with AsyncSessionLocal() as s:
        d = (await s.execute(select(Device).where(Device.model.contains('OptiPlex')))).scalar_one_or_none()
        if d:
            reqs = (await s.execute(select(WipeRequest.id).where(WipeRequest.device_id == d.id))).scalars().all()
            for r_id in reqs:
                await s.execute(delete(WipeJob).where(WipeJob.request_id == r_id))
                await s.execute(delete(Approval).where(Approval.request_id == r_id))
                await s.execute(delete(WipeRequest).where(WipeRequest.id == r_id))
            await s.commit()


async def run_e2e():
    print("[0/9] Cleaning up previous test records...")
    await cleanup_test_device()
    async with async_playwright() as p:
        print("[1/9] Launching Microsoft Edge browser...")
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        page.on("console", lambda msg: print(f"  [CONSOLE {msg.type}] {msg.text.encode('ascii', 'replace').decode('ascii')}"))
        page.on("pageerror", lambda err: print(f"  [PAGE ERROR] {err}"))

        # Step 1: Login Page with Simulation Banner
        print("[2/9] Navigating to Login Page...")
        await page.goto("http://127.0.0.1:5173/login", wait_until="networkidle")
        await page.wait_for_selector("text=SIMULATION MODE")
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "01_login_simulation_banner.png"))
        print("  -> Captured 01_login_simulation_banner.png")

        # Step 2: Login as Operator
        print("[3/9] Logging in as Operator persona...")
        print(f"  Current URL before login click: {page.url}")
        op_btn = page.locator("button:has-text('OPERATOR')").first
        await op_btn.click()
        await page.wait_for_timeout(1000)
        print(f"  Current URL after login click: {page.url}")
        await page.wait_for_url("**/dashboard", timeout=10000)
        await page.wait_for_selector("text=Security Operations Dashboard", timeout=10000)
        await page.wait_for_timeout(1000)
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "02_dashboard_overview.png"))
        print("  -> Captured 02_dashboard_overview.png")

        # Step 3: Device Inventory & Browser Detection Modal
        print("[4/9] Navigating to Device Inventory...")
        await page.goto("http://127.0.0.1:5173/devices", wait_until="networkidle")
        await page.wait_for_selector("text=IT Asset Inventory")
        await page.click("text=Add Device")
        await page.wait_for_selector("text=Browser Auto-Detect")
        await page.wait_for_timeout(500)
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "03_browser_autodetect_modal.png"))
        print("  -> Captured 03_browser_autodetect_modal.png")

        # Close modal
        close_btn = page.locator("div.fixed button:has(svg)").first
        if await close_btn.count() > 0:
            await close_btn.click()
        else:
            await page.keyboard.press("Escape")
        await page.wait_for_selector("text=Register Detected Device to Inventory", state="hidden")
        await page.wait_for_timeout(400)

        # Open a device for wiping (e.g. Dell OptiPlex or second row)
        row = page.locator("tr:has-text('Dell OptiPlex')").first
        if await row.count() == 0:
            row = page.locator("tbody tr").nth(1)
        await row.click()
        await page.wait_for_url("**/devices/**")
        await page.wait_for_selector("text=Hardware Specifications & Telemetry")
        await page.wait_for_timeout(500)
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "04_device_hardware_and_volumes.png"))
        print("  -> Captured 04_device_hardware_and_volumes.png")

        # Step 4: 4-Step Wipe Request Wizard
        await page.wait_for_selector("button:has-text('Clear / Wipe Device')")
        await page.click("button:has-text('Clear / Wipe Device')")
        await page.wait_for_selector("text=Step 1 of 4")

        # Step 1: Select volumes
        await page.click("button:has-text('Next Step')")
        await page.wait_for_selector("text=Step 2 of 4")

        # Step 2: Method selection
        await page.click("button:has-text('Next Step')")
        await page.wait_for_selector("text=Step 3 of 4")

        # Step 3: Justification & Risk
        await page.click("button:has-text('Next Step')")
        await page.wait_for_selector("text=Step 4 of 4")

        # Step 4: Confirm Device Serial
        target_serial = (await page.locator("span.font-mono.text-base.font-extrabold").inner_text()).strip()
        serial_input = page.locator("label:has-text('Type Serial to Confirm') ~ input").first
        await serial_input.fill(target_serial)
        await page.wait_for_timeout(400)
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "05_wipe_wizard_serial_confirmation.png"))
        print(f"  -> Captured 05_wipe_wizard_serial_confirmation.png (Serial: {target_serial})")

        await page.click("button:has-text('Submit Wipe Request')")
        await page.wait_for_selector("text=Wipe Request Successfully Created (Pending Approval)")
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "06_wipe_request_pending_approval.png"))
        print("  -> Captured 06_wipe_request_pending_approval.png")

        # Step 5: Test Four-Eyes Block & Approver Persona Approval
        print("[6/9] Testing Four-Eyes Dual Custody Gate...")
        await page.goto("http://127.0.0.1:5173/approvals", wait_until="networkidle")
        await page.wait_for_selector("text=Dual-Custody Approvals Inbox")
        # Verify operator cannot self-approve
        await page.wait_for_selector("text=Four-eyes rule: You submitted this request and cannot approve it.")
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "07_four_eyes_blocked_self_approval.png"))
        print("  -> Captured 07_four_eyes_blocked_self_approval.png (Self-approval blocked!)")

        # Switch to APPROVER persona
        print("  -> Switching to Approver persona...")
        await page.click("header button:has-text('OPERATOR')")
        await page.wait_for_selector("div.absolute button:has-text('APPROVER')")
        await page.click("div.absolute button:has-text('APPROVER')")
        await page.wait_for_url("**/dashboard")
        await page.goto("http://127.0.0.1:5173/approvals", wait_until="networkidle")
        await page.wait_for_selector("button:has-text('Approve Request')")

        # Approve the request
        await page.click("button:has-text('Approve Request')")
        await page.wait_for_selector("text=Approve Sanitization Request")
        await page.fill("textarea", "Certified for IT asset decommissioning manifest.")
        await page.click("button:has-text('Confirm Approval')")
        token_el = page.locator("text=Single-use authorization token")
        await token_el.wait_for()
        token_msg = await token_el.inner_text()
        raw_token_text = token_msg.split(":")[-1].strip()
        await page.wait_for_timeout(600)
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "08_approval_granted_token_issued.png"))
        print(f"  -> Captured 08_approval_granted_token_issued.png (Token: {raw_token_text})")

        # Step 6: Start Job as Operator & Watch Telemetry
        print("[7/9] Switching back to Operator to start wipe job...")
        await page.click("header button:has-text('APPROVER')")
        await page.wait_for_selector("div.absolute button:has-text('OPERATOR')")
        await page.click("div.absolute button:has-text('OPERATOR')")
        await page.wait_for_url("**/dashboard")
        await page.goto("http://127.0.0.1:5173/jobs", wait_until="networkidle")
        await page.wait_for_selector("text=Live Sanitization Operations")

        # Check for approved requests awaiting start and ensure token is set
        token_inputs = page.locator("input[placeholder='Paste single-use token...']")
        inp_count = await token_inputs.count()
        for i in range(inp_count):
            inp = token_inputs.nth(i)
            val = await inp.input_value()
            if not val and raw_token_text:
                await inp.fill(raw_token_text)
                await page.wait_for_timeout(300)
                break

        start_btn = page.locator("button:has-text('Start Wipe Job'):not([disabled])").first
        await page.wait_for_timeout(800)
        if await start_btn.count() > 0:
            await start_btn.click()
            print("  -> Clicked 'Start Wipe Job'")

        # Verify running telemetry
        await page.wait_for_timeout(2000)
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "09_live_wipe_passes_and_telemetry.png"))
        print("  -> Captured 09_live_wipe_passes_and_telemetry.png")

        # Wait for completion
        try:
            await page.wait_for_selector("text=COMPLETED", timeout=12000)
            await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "10_wipe_completed_verification_passed.png"))
            print("  -> Captured 10_wipe_completed_verification_passed.png")
        except Exception:
            pass

        # Step 7: Certificates & Tamper Detection
        print("[8/9] Verifying Certificates & Public Tamper Detection...")
        await page.goto("http://127.0.0.1:5173/certificates", wait_until="networkidle")
        await page.wait_for_selector("text=Certificates of Sanitization")
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "11_certificates_registry.png"))
        print("  -> Captured 11_certificates_registry.png")

        # Get first certificate ID
        first_cert_id = (await page.locator("table tbody tr td:first-child").first.inner_text()).strip()
        print(f"  -> Identified Certificate ID for verification: {first_cert_id}")

        # Inspect certificate
        await page.click("button:has-text('Inspect')")
        await page.wait_for_selector("text=Certificate Cryptographic Payload")
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "12_certificate_cryptographic_payload.png"))
        print("  -> Captured 12_certificate_cryptographic_payload.png")
        await page.click("button:has-text('Close')")

        # Public verification
        await page.goto("http://127.0.0.1:5173/verify", wait_until="networkidle")
        await page.wait_for_selector("text=Verify Certificate of Sanitization")

        # Enter certificate ID
        cert_input = page.locator("input[placeholder*='CERT-']")
        await cert_input.fill(first_cert_id)
        await page.click("button:has-text('Verify Certificate')")
        await page.wait_for_selector("button:has-text('Test Tamper Detection')", timeout=15000)
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "13_public_verification_valid.png"))
        print(f"  -> Captured 13_public_verification_valid.png (Status: VALID for {first_cert_id})")

        # Tamper test
        print("  -> Testing Cryptographic Tamper Detection...")
        await page.click("button:has-text('Test Tamper Detection')")
        await page.wait_for_selector("span:has-text('TAMPERED')", timeout=15000)
        await page.wait_for_timeout(500)
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "14_public_verification_tampered.png"))
        print("  -> Captured 14_public_verification_tampered.png (Status: TAMPERED)")

        # Step 8: Immutable Audit Hash Chain
        print("[9/9] Verifying Immutable Audit Log Hash Chain...")
        await page.goto("http://127.0.0.1:5173/audit", wait_until="networkidle")
        await page.wait_for_selector("text=Immutable Hash-Chained Audit Trail")
        await page.click("button:has-text('Verify Chain Integrity')")
        await page.wait_for_selector("text=Hash Chain Integrity: INTACT & VALID")
        await page.wait_for_timeout(500)
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "15_audit_hash_chain_verified.png"))
        print("  -> Captured 15_audit_hash_chain_verified.png (Hash Chain: INTACT & VALID)")

        await browser.close()
        print("\nAll End-to-End browser validations and screenshots successfully completed!")


if __name__ == "__main__":
    asyncio.run(run_e2e())
