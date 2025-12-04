#!/usr/bin/env python
"""
Test script to verify we can access MyAnonamouse with VPN bypass and login.
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
    print("MyAnonamouse Login Test")
    print("=" * 60)
    print(f"VPN Bypass enabled: {config.USE_VPN_BYPASS}")
    print(f"Login mode: {config.LOGIN_MODE}")
    print(f"Profile path: {config.FIREFOX_PROFILE_PATH}")
    print(f"MAM Base URL: {config.MAM_BASE_URL}")
    print()

    try:
        print("Step 1: Starting Playwright...")
        async with async_playwright() as p:
            print("  ✓ Playwright started")

            print("\nStep 2: Creating browser context with VPN bypass...")
            browser, context = await auth.create_browser_context(p)
            print("  ✓ Browser context created")

            print("\nStep 3: Creating new page...")
            page = await context.new_page()
            print("  ✓ Page created")

            print("\nStep 4: Attempting to log in to MyAnonamouse...")
            success = await auth.ensure_logged_in(page)

            if success:
                print(f"  ✓ Successfully logged in!")
                print(f"  Current URL: {page.url}")

                # Try to get some info from the page
                title = await page.title()
                print(f"  Page title: {title}")

                # Wait a bit so you can see the result
                print("\nWaiting 5 seconds before closing (check the browser)...")
                await asyncio.sleep(5)
            else:
                print("  ✗ Login failed")
                print(f"  Current URL: {page.url}")

                # Take a screenshot for debugging
                screenshot_path = "/home/jin23/Code/eBookGGn/mam_scraper/login_failed.png"
                await page.screenshot(path=screenshot_path)
                print(f"  Screenshot saved to: {screenshot_path}")

            print("\nStep 5: Closing browser...")
            await browser.close()
            print("  ✓ Browser closed")

            if success:
                print("\n" + "=" * 60)
                print("TEST PASSED - Login successful!")
                print("=" * 60)
            else:
                print("\n" + "=" * 60)
                print("TEST FAILED - See error messages above")
                print("=" * 60)
                sys.exit(1)

    except Exception as e:
        print(f"\n✗ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
