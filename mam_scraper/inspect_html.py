#!/usr/bin/env python
"""
HTML Inspection Script for MyAnonamouse
Opens browser and pauses at key pages for manual HTML inspection.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import config
from playwright.async_api import async_playwright
from auth import create_browser_context, ensure_logged_in


async def main():
    print("=" * 70)
    print("MyAnonamouse HTML Inspection Tool")
    print("=" * 70)
    print("\nThis script will:")
    print("  1. Log in to MyAnonamouse")
    print("  2. Open the browse page - PAUSE for inspection")
    print("  3. Open a torrent detail page - PAUSE for inspection")
    print("\nYou can use browser DevTools (F12) to inspect elements")
    print("=" * 70)
    print()

    # Validate config
    try:
        config.validate_config()
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        return 1

    async with async_playwright() as p:
        print("🌐 Starting browser...")
        browser, context = await create_browser_context(p)
        page = await context.new_page()

        # Login
        print("🔐 Logging in to MyAnonamouse...")
        if not await ensure_logged_in(page):
            print("   ❌ Login failed")
            await browser.close()
            return 1
        print("   ✓ Successfully logged in")
        print()

        # Step 1: Browse Page
        print("=" * 70)
        print("STEP 1: BROWSE PAGE INSPECTION")
        print("=" * 70)

        browse_url = f"{config.MAM_BASE_URL}/tor/browse.php"
        print(f"\nNavigating to: {browse_url}")
        await page.goto(browse_url, wait_until="networkidle", timeout=30000)

        print("\n📋 INSPECT THE BROWSE PAGE:")
        print("   1. Press F12 to open DevTools")
        print("   2. Use the element picker (top-left icon in DevTools)")
        print("   3. Find these elements:")
        print("      - Category dropdown (e.g., 'All Categories')")
        print("      - Language dropdown")
        print("      - Tags toggle/enable checkbox or button")
        print("      - Tags text input field")
        print("      - Filetype checkboxes (epub, pdf, mobi)")
        print("      - Search/Submit button")
        print("\n⏸️  Browser will stay open for 2 minutes...")
        print("   (Press Ctrl+C to skip waiting)")

        try:
            await asyncio.sleep(120)  # 2 minutes
        except KeyboardInterrupt:
            print("\n   Skipped by user")

        print()

        # Step 2: Get a torrent link from results
        print("=" * 70)
        print("STEP 2: FINDING A TORRENT DETAIL PAGE")
        print("=" * 70)

        # Try to find any torrent link
        print("\nLooking for torrent links on current page...")
        torrent_links = []

        # Try to find links with /t/ pattern
        elements = await page.query_selector_all('a[href*="/t/"]')
        for element in elements[:20]:  # Check first 20 links
            href = await element.get_attribute("href")
            if href and "/t/" in href and "/f/t/" not in href:  # Avoid forum links
                if href.startswith("/"):
                    full_url = config.MAM_BASE_URL + href
                else:
                    full_url = href
                # Make sure it's a clean torrent URL
                if "/t/" in full_url and "?" not in full_url:
                    torrent_links.append(full_url)
                    if len(torrent_links) >= 3:
                        break

        if not torrent_links:
            print("⚠️  Could not find torrent links automatically")
            print("   Trying to go to a known torrent...")
            # Try a known torrent ID from previous test
            detail_url = f"{config.MAM_BASE_URL}/t/1202959"
        else:
            detail_url = torrent_links[0]
            print(f"   Found {len(torrent_links)} torrent links")
            print(f"   Will inspect: {detail_url}")

        print()

        # Step 3: Detail Page
        print("=" * 70)
        print("STEP 3: TORRENT DETAIL PAGE INSPECTION")
        print("=" * 70)

        print(f"\nNavigating to: {detail_url}")
        await page.goto(detail_url, wait_until="networkidle", timeout=30000)

        print("\n📋 INSPECT THE DETAIL PAGE:")
        print("   1. Keep DevTools open (F12)")
        print("   2. Find these elements:")
        print("      - Title (book name)")
        print("      - Author name")
        print("      - Size (e.g., '40.83 MiB')")
        print("      - Tags (e.g., 'Video Game Studies', etc.)")
        print("      - File count (e.g., '2 files')")
        print("      - Filetypes (e.g., 'epub, pdf')")
        print("      - Added/Upload time")
        print("      - Description (main content area)")
        print("      - Cover image")
        print("      - Download button/link")
        print("\n⏸️  Browser will stay open for 3 minutes...")
        print("   (Press Ctrl+C when done inspecting)")

        try:
            await asyncio.sleep(180)  # 3 minutes
        except KeyboardInterrupt:
            print("\n   Inspection complete")

        print()
        print("=" * 70)
        print("Inspection session complete!")
        print("=" * 70)
        print("\nNext steps:")
        print("  1. Use the CSS selectors you found to update:")
        print("     - filters.py (browse page filters)")
        print("     - scraper.py (detail page data)")
        print("  2. Re-run test: ./run-with-vpn-bypass.sh python test_crawler.py")
        print()
        print("Closing browser in 5 seconds...")
        await asyncio.sleep(5)
        await browser.close()

    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInspection interrupted by user")
        sys.exit(0)
