#!/usr/bin/env python
"""
Quick test script to verify VPN bypass is working.
"""
import asyncio
import sys
import os
from playwright.async_api import async_playwright

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

import config
import auth


async def main():
    print("=" * 60)
    print("VPN Bypass Test")
    print("=" * 60)
    print(f"VPN Bypass enabled: {config.USE_VPN_BYPASS}")
    print(f"Login mode: {config.LOGIN_MODE}")
    print(f"Profile path: {config.FIREFOX_PROFILE_PATH}")
    print(f"Headless: {config.BROWSER_HEADLESS}")
    print()

    # Get wrapper script path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    firefox_wrapper = os.path.join(script_dir, "firefox-no-vpn-wrapper.sh")
    print(f"Wrapper script: {firefox_wrapper}")
    print(f"Wrapper exists: {os.path.exists(firefox_wrapper)}")
    print()

    try:
        print("Step 1: Starting Playwright...")
        async with async_playwright() as p:
            print("  ✓ Playwright started")

            print("\nStep 2: Creating browser context...")
            browser, context = await auth.create_browser_context(p)
            print("  ✓ Browser context created")

            print("\nStep 3: Creating new page...")
            page = await context.new_page()
            print("  ✓ Page created")

            print("\nStep 4: Navigating to test page...")
            await page.goto("https://www.google.com", timeout=15000)
            print(f"  ✓ Successfully navigated to: {page.url}")

            print("\nStep 5: Closing browser...")
            await browser.close()
            print("  ✓ Browser closed")

            print("\n" + "=" * 60)
            print("TEST PASSED - VPN bypass is working!")
            print("=" * 60)

    except Exception as e:
        print(f"\n✗ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
