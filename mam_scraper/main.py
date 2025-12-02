#!/usr/bin/env python3
"""
Main entry point for MyAnonamouse eBook crawler.
Run with: python main.py [options]
"""
import asyncio
import argparse
import sys
import logging
from playwright.async_api import async_playwright

import config
from utils import setup_logging
from auth import create_browser_context, ensure_logged_in
from db import init_db, get_stats
from crawler import crawl_all_searches

logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="MyAnonamouse eBook crawler for video game books",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                          # Run all searches with default limits
  python main.py --search "Video Game + epub"  # Run only one search
  python main.py --max-torrents 100       # Limit to 100 torrents
  python main.py --dry-run                # Test mode (no scraping, just list URLs)
  python main.py --test-mode              # Test mode with minimal limits (1 page, 5 torrents)
        """
    )

    parser.add_argument(
        "--search",
        "--search-label",
        dest="search_label",
        type=str,
        help="Only run a specific search by label (e.g., 'Video Game + epub')"
    )

    parser.add_argument(
        "--max-torrents",
        type=int,
        help=f"Override max torrents per run (default: {config.SAFE_CRAWL['max_torrents_total']})"
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        help=f"Override max pages per search (default: {config.SAFE_CRAWL['max_pages_per_search']})"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run mode: list URLs but don't scrape or save"
    )

    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Test mode: limit to 1 page and 5 torrents for quick testing"
    )

    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show database statistics and exit"
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (no GUI)"
    )

    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=config.LOG_LEVEL,
        help=f"Set logging level (default: {config.LOG_LEVEL})"
    )

    return parser.parse_args()


async def main_async(args):
    """Main async function."""
    # Set up logging
    setup_logging(config.LOG_FILE, args.log_level)

    logger.info("="*60)
    logger.info("MyAnonamouse eBook Crawler Starting")
    logger.info("="*60)

    # Validate configuration
    try:
        config.validate_config()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("\nPlease create a .env file based on .env.example")
        return 1

    # Apply command line overrides
    if args.max_torrents:
        config.SAFE_CRAWL["max_torrents_total"] = args.max_torrents
        logger.info(f"Override: max_torrents_total = {args.max_torrents}")

    if args.max_pages:
        config.SAFE_CRAWL["max_pages_per_search"] = args.max_pages
        logger.info(f"Override: max_pages_per_search = {args.max_pages}")

    if args.test_mode:
        config.SAFE_CRAWL["max_pages_per_search"] = 1
        config.SAFE_CRAWL["max_torrents_total"] = 5
        logger.info("Test mode: Limited to 1 page, 5 torrents")

    if args.headless:
        config.BROWSER_HEADLESS = True
        logger.info("Running in headless mode")

    # Initialize database
    db_conn = init_db(config.DB_PATH)
    logger.info(f"Database initialized: {config.DB_PATH}")

    # Show stats if requested
    if args.stats:
        stats = get_stats(db_conn)
        print("\n" + "="*60)
        print("DATABASE STATISTICS")
        print("="*60)
        print(f"Total torrents: {stats['total_torrents']}")
        print(f"\nBy search label:")
        for label, count in sorted(stats['by_search_label'].items()):
            print(f"  {label}: {count}")
        print(f"\nBy filetype:")
        for filetype, count in sorted(stats['by_filetype'].items()):
            print(f"  {filetype}: {count}")
        print(f"\nLatest scrape: {stats['latest_scrape']}")
        print("="*60)
        db_conn.close()
        return 0

    # Determine which searches to run
    selected_labels = None
    if args.search_label:
        # Validate the search label exists
        valid_labels = [s["label"] for s in config.SEARCHES]
        if args.search_label not in valid_labels:
            logger.error(f"Invalid search label: {args.search_label}")
            logger.error(f"Available labels: {', '.join(valid_labels)}")
            db_conn.close()
            return 1
        selected_labels = [args.search_label]

    if args.dry_run:
        logger.warning("DRY RUN MODE - No actual scraping will be performed")
        # TODO: Implement dry-run mode if needed
        logger.error("Dry-run mode not yet implemented")
        db_conn.close()
        return 1

    # Launch browser and start crawling
    logger.info("Launching browser...")

    try:
        async with async_playwright() as p:
            browser, context = await create_browser_context(p)
            logger.info("Browser launched successfully")

            # Create a new page
            if config.LOGIN_MODE == "cookies":
                page = await context.new_page()
            else:
                page = await context.new_page()

            # Ensure we're logged in
            logger.info("Verifying authentication...")
            if not await ensure_logged_in(page):
                logger.error("Authentication failed - cannot proceed")
                await browser.close()
                db_conn.close()
                return 1

            logger.info("Authentication successful!")

            # Start crawling
            logger.info("\nStarting crawl process...")
            results = await crawl_all_searches(
                page,
                db_conn,
                selected_labels=selected_labels,
                max_torrents=config.SAFE_CRAWL["max_torrents_total"]
            )

            # Show final summary
            print("\n" + "="*60)
            print("CRAWL COMPLETE - SUMMARY")
            print("="*60)
            total_scraped = sum(results.values())
            print(f"Total torrents scraped: {total_scraped}")
            print(f"\nResults by search:")
            for label, count in results.items():
                print(f"  {label}: {count}")

            # Show updated database stats
            stats = get_stats(db_conn)
            print(f"\nTotal torrents in database: {stats['total_torrents']}")
            print("="*60)

            await browser.close()

    except KeyboardInterrupt:
        logger.warning("\n\nCrawl interrupted by user (Ctrl+C)")
        print("\nCrawl interrupted. Data saved up to this point is in the database.")
        db_conn.close()
        return 130  # Standard exit code for SIGINT

    except Exception as e:
        logger.error(f"Fatal error during crawl: {e}")
        import traceback
        logger.error(traceback.format_exc())
        db_conn.close()
        return 1

    db_conn.close()
    logger.info("Database connection closed")
    logger.info("Crawler finished successfully")

    return 0


def main():
    """Main entry point."""
    args = parse_arguments()

    try:
        exit_code = asyncio.run(main_async(args))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)


if __name__ == "__main__":
    main()
