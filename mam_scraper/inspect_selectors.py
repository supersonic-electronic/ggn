#!/usr/bin/env python
"""
Inspect actual torrent page to find working selectors.
This will try common selectors and show what data they extract.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import config
from playwright.async_api import async_playwright
from auth import create_browser_context, ensure_logged_in
from filters import apply_filters


async def main():
    print("=" * 70)
    print("Selector Inspector for MyAnonamouse")
    print("=" * 70)

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
        print("🔐 Logging in...")
        if not await ensure_logged_in(page):
            print("   ❌ Login failed")
            await browser.close()
            return 1
        print("   ✓ Logged in")

        # Do a search
        print("\n🔍 Performing search for 'Video Game'...")
        test_search = config.SEARCHES[0]
        result_url = await apply_filters(page, test_search)
        print(f"   ✓ Search complete")
        print(f"   URL: {result_url}")

        # Find torrent links
        print("\n📋 Finding torrent links...")
        elements = await page.query_selector_all('a[href*="/t/"]')
        torrent_links = []

        for element in elements[:30]:
            href = await element.get_attribute("href")
            if href and "/t/" in href:
                # Skip forum links (/f/t/)
                if "/f/t/" in href:
                    continue
                # Make absolute URL
                if href.startswith("/"):
                    full_url = config.MAM_BASE_URL + href
                else:
                    full_url = href
                # Remove query parameters for clean URL
                if "?" in full_url:
                    full_url = full_url.split("?")[0]
                # Avoid duplicates
                if full_url not in torrent_links:
                    torrent_links.append(full_url)
                if len(torrent_links) >= 5:
                    break

        if not torrent_links:
            print("   ❌ No torrent links found!")
            await browser.close()
            return 1

        print(f"   Found {len(torrent_links)} torrent links:")
        for i, link in enumerate(torrent_links, 1):
            print(f"   {i}. {link}")

        # Inspect first torrent
        detail_url = torrent_links[0]
        print(f"\n📖 Inspecting: {detail_url}")
        await page.goto(detail_url, wait_until="networkidle", timeout=30000)

        print("\n" + "=" * 70)
        print("TESTING SELECTORS")
        print("=" * 70)

        # Test various selectors
        selectors_to_test = {
            "Title": [
                "h1",
                "h1.TorrentTitle",
                ".torrent-title",
                "#torrent-title",
                "div.torrent-details h1",
            ],
            "Author": [
                "a[href*='/tor/author']",
                ".author",
                "span.author",
                "#author",
                "a:has-text('Author')",
            ],
            "Size": [
                "span:has-text('MiB')",
                "span:has-text('GiB')",
                ".torrent-size",
                "td:has-text('Size')",
            ],
            "Tags": [
                ".tags",
                "#tags",
                "span.tag",
                "a.tag",
                "a[href*='/tor/browse.php?tag']",
            ],
            "Files": [
                "span:has-text('file')",
                "span:has-text('File')",
                ".file-count",
                "#file-count",
            ],
            "Description": [
                ".description",
                "#description",
                ".torrent-description",
                "div.torrent-details",
            ],
            "Cover Image": [
                "img.cover",
                "#cover",
                "img[alt*='cover']",
                "img[alt*='Cover']",
            ],
            "Download Link": [
                "a[href*='/tor/download.php']",
                "a:has-text('Download')",
                "#download",
                ".download-link",
            ],
        }

        for field_name, selectors in selectors_to_test.items():
            print(f"\n{field_name}:")
            print("-" * 40)
            found = False
            for selector in selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        # Try to get text
                        text = await element.inner_text()
                        text = text.strip()[:100]  # Limit to 100 chars
                        if text:
                            print(f"  ✓ {selector}")
                            print(f"    → {text}")
                            found = True
                            break
                        else:
                            # Try href for links
                            href = await element.get_attribute("href")
                            if href:
                                print(f"  ✓ {selector}")
                                print(f"    → href: {href}")
                                found = True
                                break
                            # Try src for images
                            src = await element.get_attribute("src")
                            if src:
                                print(f"  ✓ {selector}")
                                print(f"    → src: {src}")
                                found = True
                                break
                except Exception as e:
                    continue

            if not found:
                print(f"  ✗ No working selector found")

        # Try to get ALL text on page to understand structure
        print("\n" + "=" * 70)
        print("PAGE STRUCTURE SAMPLE")
        print("=" * 70)
        body_text = await page.inner_text("body")
        lines = body_text.split("\n")[:50]  # First 50 lines
        for i, line in enumerate(lines, 1):
            if line.strip():
                print(f"{i:3}. {line.strip()[:70]}")

        print("\n" + "=" * 70)
        print("Inspection Complete!")
        print("=" * 70)
        print("\nKeeping browser open for 10 seconds for manual inspection...")
        await asyncio.sleep(10)

        await browser.close()

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
