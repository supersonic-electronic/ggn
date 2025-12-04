#!/usr/bin/env python
"""
Test multi-page pagination scraping.
Tests 3 pages (up to 300 torrents) with pagination.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import config
from utils import setup_logging
from playwright.async_api import async_playwright
from auth import create_browser_context, ensure_logged_in
from crawler import crawl_all_searches
from db import init_db, get_stats


async def main():
    print("=" * 70)
    print("MYANONAMOUSE CRAWLER - PAGINATION TEST (3 PAGES)")
    print("=" * 70)
    print("\nTest Configuration:")
    print("  - Max pages per search: 3")
    print("  - Max torrents total: 300")
    print("  - Search: Video Game + epub (first search only)")
    print("  - Delays: 3-7 seconds between requests")
    print()

    # Validate config
    try:
        config.validate_config()
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("\nPlease ensure .env is properly configured")
        return 1

    # Set up logging
    os.makedirs("logs", exist_ok=True)
    setup_logging(config.LOG_FILE, "INFO")  # INFO level to reduce log size

    # Override with test limits - TEST 3 PAGES
    config.SAFE_CRAWL.update({
        "max_pages_per_search": 3,  # Test 3 pages
        "max_torrents_total": 300,  # Up to 300 torrents
        "min_delay_seconds": 3,
        "max_delay_seconds": 7,
    })

    # Initialize database
    print("📊 Initializing database...")
    db_conn = init_db(config.DB_PATH)

    # Show initial stats
    stats = get_stats(db_conn)
    print(f"   Database: {config.DB_PATH}")
    print(f"   Existing torrents in DB: {stats['total_torrents']}")
    print()

    async with async_playwright() as p:
        print("🌐 Starting browser with VPN bypass...")
        browser, context = await create_browser_context(p)

        print("   ✓ Browser launched")

        page = await context.new_page()
        print("   ✓ Page created")
        print()

        # Login
        print("🔐 Logging in to MyAnonamouse...")
        if not await ensure_logged_in(page):
            print("   ❌ Login failed")
            await browser.close()
            db_conn.close()
            return 1

        print("   ✓ Successfully logged in")
        print()

        # Run crawler - just first search
        first_search_label = config.SEARCHES[0]['label']
        print(f"🚀 Starting multi-page crawl: {first_search_label}")
        print(f"   This will scrape up to 3 pages (up to 300 torrents)")
        print()

        try:
            results = await crawl_all_searches(
                page,
                db_conn,
                selected_labels=[first_search_label],
                max_torrents=300
            )

            print("\n" + "=" * 70)
            print("✅ CRAWL COMPLETE")
            print("=" * 70)
            print("\nResults:")
            for label, count in results.items():
                print(f"  {label}: {count} torrents scraped")

            # Final stats
            final_stats = get_stats(db_conn)
            print(f"\nDatabase Stats:")
            print(f"  Total torrents: {final_stats['total_torrents']}")
            print(f"  New this run: {final_stats['total_torrents'] - stats['total_torrents']}")

            print(f"\n💾 Data saved to: {config.DB_PATH}")
            print(f"📋 Logs saved to: {config.LOG_FILE}")

        except Exception as e:
            print(f"\n❌ Error during crawl: {e}")
            import traceback
            traceback.print_exc()
            return 1

        finally:
            print("\n🔒 Closing browser...")
            await browser.close()
            db_conn.close()

    print("\n" + "=" * 70)
    print("Pagination test complete!")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
