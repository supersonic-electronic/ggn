#!/usr/bin/env python
"""
Interactive HTML Inspection Script for MyAnonamouse
Opens browser and waits for you to press Enter before continuing.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import config
from playwright.async_api import async_playwright
from auth import create_browser_context, ensure_logged_in


def wait_for_enter(message):
    """Wait for user to press Enter."""
    input(f"\n{message}\nPress Enter when ready to continue...")


async def main():
    print("=" * 70)
    print("MyAnonamouse HTML Inspection Tool (Interactive)")
    print("=" * 70)
    print("\nThis script will open pages and wait for you to inspect them.")
    print("Take your time - press Enter only when you're ready to continue.")
    print("=" * 70)
    input("\nPress Enter to start...")

    # Validate config
    try:
        config.validate_config()
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        return 1

    async with async_playwright() as p:
        print("\n🌐 Starting browser...")
        browser, context = await create_browser_context(p)
        page = await context.new_page()

        # Login
        print("🔐 Logging in to MyAnonamouse...")
        if not await ensure_logged_in(page):
            print("   ❌ Login failed")
            await browser.close()
            return 1
        print("   ✓ Successfully logged in")

        # Step 1: Browse Page
        print("\n" + "=" * 70)
        print("STEP 1: BROWSE PAGE INSPECTION")
        print("=" * 70)

        browse_url = f"{config.MAM_BASE_URL}/tor/browse.php"
        print(f"\nNavigating to: {browse_url}")
        await page.goto(browse_url, wait_until="networkidle", timeout=30000)

        print("\n📋 INSPECT THE BROWSE PAGE:")
        print("\n   Things to find:")
        print("   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("   1. Category dropdown")
        print("      - Right-click → Inspect")
        print("      - Look for: <select name='...'> or <select id='...'")
        print("      - Note the name or id attribute")
        print()
        print("   2. Language dropdown")
        print("      - Similar to category")
        print()
        print("   3. Tags section")
        print("      - Find the toggle/enable button or checkbox")
        print("      - Find the text input for tag names")
        print()
        print("   4. Filetype checkboxes")
        print("      - Find checkboxes for epub, pdf, mobi")
        print("      - Note their name or id attributes")
        print()
        print("   5. Search/Submit button")
        print("      - Usually <button> or <input type='submit'>")
        print("   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        wait_for_enter("\n⏸️  Press F12 to open DevTools and inspect elements.")

        # Step 2: Search with Video Game tag (manual)
        print("\n" + "=" * 70)
        print("STEP 2: MANUAL SEARCH TEST")
        print("=" * 70)
        print("\n📝 Now let's manually search for 'Video Game' eBooks:")
        print("\n   1. In the browser, manually:")
        print("      - Select 'eBooks' from category dropdown")
        print("      - Select 'English' from language (if available)")
        print("      - Enable Tags filter")
        print("      - Type 'Video Game' in tags field")
        print("      - Check 'epub' filetype")
        print("      - Click Search/Submit")
        print("\n   2. Once you see the results, look at the URL")
        print("      - This shows us what parameters are used")

        wait_for_enter("\n⏸️  Perform the search, then continue...")

        # Get current URL after manual search
        current_url = page.url
        print(f"\n   Current URL after search: {current_url}")
        print("\n   💡 This URL shows the correct query parameters!")

        # Step 3: Find a torrent
        print("\n" + "=" * 70)
        print("STEP 3: FINDING A TORRENT LINK")
        print("=" * 70)
        print("\n   In the search results:")
        print("   - Find a Video Game eBook torrent")
        print("   - Right-click the title → Inspect")
        print("   - Look at the <a href='...'> link")
        print("   - Note the pattern (e.g., /t/123456)")

        wait_for_enter("\n⏸️  Inspect a torrent link, then continue...")

        # Try to get a torrent link
        print("\n   Looking for torrent links in current page...")
        elements = await page.query_selector_all('a[href*="/t/"]')
        torrent_links = []

        for element in elements[:20]:
            href = await element.get_attribute("href")
            if href and "/t/" in href and "/f/t/" not in href:
                if href.startswith("/"):
                    full_url = config.MAM_BASE_URL + href
                else:
                    full_url = href
                if "?" not in full_url:  # Clean URL only
                    torrent_links.append(full_url)
                    if len(torrent_links) >= 5:
                        break

        if torrent_links:
            print(f"\n   Found {len(torrent_links)} torrent links:")
            for i, link in enumerate(torrent_links[:5], 1):
                print(f"   {i}. {link}")
            detail_url = torrent_links[0]
        else:
            print("\n   ⚠️  Could not auto-detect links")
            detail_url = input("\n   Enter a torrent URL to inspect: ").strip()
            if not detail_url:
                detail_url = f"{config.MAM_BASE_URL}/t/1202959"
                print(f"   Using default: {detail_url}")

        # Step 4: Detail Page
        print("\n" + "=" * 70)
        print("STEP 4: TORRENT DETAIL PAGE INSPECTION")
        print("=" * 70)

        print(f"\nNavigating to: {detail_url}")
        await page.goto(detail_url, wait_until="networkidle", timeout=30000)

        print("\n📋 INSPECT THE DETAIL PAGE:")
        print("\n   Elements to find (use Element Picker in DevTools):")
        print("   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("   1. Title - Usually in <h1> or prominent heading")
        print("   2. Author - Often near title, might be a link")
        print("   3. Size - Look for text like 'XX.XX MiB'")
        print("   4. Tags - Usually clickable badges or links")
        print("   5. File count - Text like '2 files'")
        print("   6. Filetypes - Text like 'epub, pdf'")
        print("   7. Upload date/time - When torrent was added")
        print("   8. Description - Main content area")
        print("   9. Cover image - Book cover <img> tag")
        print("   10. Download link - Button or link with 'Download'")
        print("   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("\n   For each element:")
        print("   - Right-click → Inspect")
        print("   - Note the CSS selector:")
        print("     • Class: .class-name")
        print("     • ID: #element-id")
        print("     • Tag: h1, span, div, etc.")
        print("     • Attribute: [name='value']")

        wait_for_enter("\n⏸️  Inspect all elements on the detail page...")

        # Final summary
        print("\n" + "=" * 70)
        print("INSPECTION COMPLETE!")
        print("=" * 70)
        print("\n📝 You should now have:")
        print("   1. CSS selectors for browse page filters")
        print("   2. Search URL pattern with correct parameters")
        print("   3. CSS selectors for all detail page fields")
        print("\nNext steps:")
        print("   1. Share the selectors you found")
        print("   2. I'll update filters.py and scraper.py")
        print("   3. Re-test the crawler")

        wait_for_enter("\n⏸️  Press Enter to close browser and exit...")

        await browser.close()

    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInspection interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
