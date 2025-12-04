#!/usr/bin/env python3
"""
MyAnonamouse eBook Scraper - Production CLI
Scrapes MyAnonamouse for eBook torrents with specified tags and formats.
"""
import asyncio
import argparse
import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

import config
from utils import setup_logging
from playwright.async_api import async_playwright
from auth import create_browser_context, ensure_logged_in
from crawler import crawl_all_searches
from db import init_db, get_stats


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="MyAnonamouse eBook Scraper - Scrape eBook torrents by tags and formats",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape up to 500 video game epubs
  %(prog)s --tags "Video Game" --formats epub --max-torrents 500

  # Scrape video game books in multiple formats (unlimited pages)
  %(prog)s --tags "Video Game" --formats epub pdf mobi --max-torrents 10000

  # Use plural tags
  %(prog)s --tags "video games" --formats epub --max-torrents 1000

  # Multiple tags (searches will be combined)
  %(prog)s --tags "Video Game" "Gaming" --formats epub --max-torrents 500

  # Custom database and output
  %(prog)s --tags "SciFi" --formats epub --max-torrents 300 --db scifi.db

  # Export only (no scraping)
  %(prog)s --export-only --db mam.db
        """
    )

    # Core options
    parser.add_argument(
        '--tags',
        nargs='+',
        help='Tags to search for (e.g., "Video Game" "SciFi" "Fantasy")'
    )

    parser.add_argument(
        '--formats',
        nargs='+',
        default=['epub'],
        choices=['epub', 'pdf', 'mobi', 'azw3'],
        help='File formats to search for (default: epub)'
    )

    parser.add_argument(
        '--max-torrents',
        type=int,
        default=1000,
        help='Maximum number of torrents to scrape (default: 1000, use 10000 for unlimited)'
    )

    parser.add_argument(
        '--max-pages',
        type=int,
        default=999,
        help='Maximum pages to scrape per search (default: 999 for unlimited)'
    )

    # Database and output
    parser.add_argument(
        '--db',
        default='mam.db',
        help='Database file path (default: mam.db)'
    )

    parser.add_argument(
        '--export',
        action='store_true',
        help='Export to CSV after scraping'
    )

    parser.add_argument(
        '--export-only',
        action='store_true',
        help='Only export existing database to CSV, do not scrape'
    )

    # Crawling behavior
    parser.add_argument(
        '--min-delay',
        type=float,
        default=3.0,
        help='Minimum delay between requests in seconds (default: 3.0)'
    )

    parser.add_argument(
        '--max-delay',
        type=float,
        default=7.0,
        help='Maximum delay between requests in seconds (default: 7.0)'
    )

    parser.add_argument(
        '--long-pause',
        type=int,
        default=20,
        help='Long pause duration in seconds every N pages (default: 20)'
    )

    parser.add_argument(
        '--pages-before-pause',
        type=int,
        default=10,
        help='Number of pages before long pause (default: 10)'
    )

    # Other options
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be scraped without actually scraping'
    )

    return parser.parse_args()


async def main():
    """Main entry point for CLI."""
    args = parse_args()

    # Export-only mode
    if args.export_only:
        print("=" * 70)
        print("EXPORT MODE")
        print("=" * 70)

        if not os.path.exists(args.db):
            print(f"❌ Database not found: {args.db}")
            return 1

        # Export to CSV
        from datetime import datetime
        from export_to_csv import export_to_csv
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        csv_file = args.db.replace('.db', f'_export_{timestamp}.csv')
        export_to_csv(args.db, csv_file)
        return 0

    # Validate required arguments for scraping
    if not args.tags:
        print("❌ Error: --tags is required for scraping")
        print("   Use --export-only if you just want to export existing data")
        print("   Run with --help for usage examples")
        return 1

    # Print configuration
    print("=" * 70)
    print("MYANONAMOUSE EBOOK SCRAPER")
    print("=" * 70)
    print(f"\nConfiguration:")
    print(f"  Tags: {', '.join(args.tags)}")
    print(f"  Formats: {', '.join(args.formats)}")
    print(f"  Max torrents: {args.max_torrents}")
    print(f"  Max pages: {args.max_pages}")
    print(f"  Database: {args.db}")
    print(f"  Delays: {args.min_delay}-{args.max_delay}s (long pause: {args.long_pause}s every {args.pages_before_pause} pages)")
    print(f"  Log level: {args.log_level}")

    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No actual scraping will occur")

    print()

    # Validate config
    try:
        config.validate_config()
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        print("\nPlease ensure .env is properly configured")
        return 1

    # Dry run mode - just show search config and exit
    if args.dry_run:
        print("Search configurations that would be created:")
        for tag in args.tags:
            label = f"{tag} + {'+'.join(args.formats)}"
            print(f"\n  Search: {label}")
            print(f"    Tag: {tag}")
            print(f"    Formats: {', '.join(args.formats)}")
            print(f"    Category: eBooks")
            print(f"    Language: English")
        print("\n✓ Dry run complete - no scraping performed")
        return 0

    # Set up logging
    os.makedirs("logs", exist_ok=True)
    setup_logging(config.LOG_FILE, args.log_level)

    # Update safe crawl settings
    config.SAFE_CRAWL.update({
        "max_pages_per_search": args.max_pages,
        "max_torrents_total": args.max_torrents,
        "min_delay_seconds": args.min_delay,
        "max_delay_seconds": args.max_delay,
        "pages_before_long_pause": args.pages_before_pause,
        "long_pause_seconds": args.long_pause,
    })

    # Initialize database
    print(f"📊 Initializing database: {args.db}...")
    db_conn = init_db(args.db)

    # Show initial stats
    stats = get_stats(db_conn)
    print(f"   Existing torrents in DB: {stats['total_torrents']}")
    print()

    # Create search configurations
    searches = []
    for tag in args.tags:
        search_config = {
            "label": f"{tag} + {'+'.join(args.formats)}",
            "category": "eBooks",
            "language": "English",
            "tags": [tag],
            "filetypes": args.formats,
        }
        searches.append(search_config)

    # Start scraping
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

        # Run searches
        print(f"🚀 Starting scrape with {len(searches)} search(es)...")
        for search in searches:
            print(f"   - {search['label']}")
        print()

        try:
            # Temporarily set searches in config
            original_searches = config.SEARCHES
            config.SEARCHES = searches

            results = await crawl_all_searches(
                page,
                db_conn,
                selected_labels=[s['label'] for s in searches],
                max_torrents=args.max_torrents
            )

            # Restore original searches
            config.SEARCHES = original_searches

            print("\n" + "=" * 70)
            print("✅ SCRAPE COMPLETE")
            print("=" * 70)
            print("\nResults:")
            total_scraped = 0
            for label, count in results.items():
                print(f"  {label}: {count} torrents")
                total_scraped += count

            # Final stats
            final_stats = get_stats(db_conn)
            print(f"\nDatabase Stats:")
            print(f"  Total torrents in DB: {final_stats['total_torrents']}")
            print(f"  New this run: {final_stats['total_torrents'] - stats['total_torrents']}")

            print(f"\n💾 Data saved to: {args.db}")
            print(f"📋 Logs saved to: {config.LOG_FILE}")

            # Export if requested
            if args.export:
                print("\n📤 Exporting to CSV...")
                from datetime import datetime
                from export_to_csv import export_to_csv
                timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                csv_file = args.db.replace('.db', f'_export_{timestamp}.csv')
                export_to_csv(args.db, csv_file)

        except KeyboardInterrupt:
            print("\n\n⚠️  Scrape interrupted by user")
            print("   Data has been saved up to this point")
            return 130

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
    print("Done!")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)
