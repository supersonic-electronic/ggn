#!/usr/bin/env python
"""
Full scrape test - scrape ALL pages for "video games" (plural) + epub.
This will continue until there are no more pages.
Uses separate database: mam_video_games_plural.db
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
    print("MYANONAMOUSE CRAWLER - FULL SCRAPE (ALL PAGES)")
    print("Search: 'video games' (PLURAL) + epub")
    print("=" * 70)
    print("\nTest Configuration:")
    print("  - Max pages per search: 999 (scrape until no more pages)")
    print("  - Max torrents total: 10000")
    print("  - Search: video games (plural) + epub")
    print("  - Delays: 3-7 seconds between requests")
    print("  - Database: mam_video_games_plural.db")
    print("\nWARNING: This may take several hours depending on total results!")
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
    setup_logging(config.LOG_FILE, "INFO")

    # Override with unlimited limits
    config.SAFE_CRAWL.update({
        "max_pages_per_search": 999,  # Very high limit
        "max_torrents_total": 10000,  # Very high limit
        "min_delay_seconds": 3,
        "max_delay_seconds": 7,
        "pages_before_long_pause": 10,  # Long pause every 10 pages
        "long_pause_seconds": 20,
    })

    # Use separate database for plural search
    db_path = "mam_video_games_plural.db"

    # Initialize database
    print(f"📊 Initializing database: {db_path}...")
    db_conn = init_db(db_path)

    # Show initial stats
    stats = get_stats(db_conn)
    print(f"   Database: {db_path}")
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

        # Create custom search config for "video games" (plural)
        custom_search = {
            "label": "video games + epub",  # lowercase, plural
            "category": "eBooks",
            "language": "English",
            "tags": ["video games"],  # plural
            "filetypes": ["epub"],
        }

        print(f"🚀 Starting FULL crawl: {custom_search['label']}")
        print(f"   This will scrape ALL pages until no more results")
        print()

        try:
            # Temporarily add our custom search to config
            original_searches = config.SEARCHES
            config.SEARCHES = [custom_search]

            results = await crawl_all_searches(
                page,
                db_conn,
                selected_labels=[custom_search['label']],
                max_torrents=10000  # Very high limit
            )

            # Restore original searches
            config.SEARCHES = original_searches

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

            print(f"\n💾 Data saved to: {db_path}")
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
    print("Full scrape complete!")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
