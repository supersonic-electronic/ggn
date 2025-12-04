#!/usr/bin/env python
"""
Simple test to see where the hang occurs.
"""
import asyncio
import sys
import os

print("1. Starting script", flush=True)

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

print("2. Importing modules", flush=True)

import config
import auth

print(f"3. Config loaded: VPN={config.USE_VPN_BYPASS}, Profile={config.FIREFOX_PROFILE_PATH}", flush=True)

async def main():
    print("4. Entering async main", flush=True)

    from playwright.async_api import async_playwright
    print("5. Playwright imported", flush=True)

    async with async_playwright() as p:
        print("6. Playwright context created", flush=True)

        print("7. About to create browser context...", flush=True)
        browser, context = await auth.create_browser_context(p)
        print("8. Browser context created!", flush=True)

        print("9. Creating page...", flush=True)
        page = await context.new_page()
        print("10. Page created!", flush=True)

        print("11. Closing...", flush=True)
        await browser.close()
        print("12. Done!", flush=True)

if __name__ == "__main__":
    print("Starting asyncio.run...", flush=True)
    asyncio.run(main())
    print("Script complete!", flush=True)
