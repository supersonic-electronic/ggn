"""
Main crawler module for MyAnonamouse eBook scraping.
Handles pagination, torrent discovery, and coordinating the scraping process.
"""
import logging
import asyncio
from typing import Dict, Any, List, Optional
from playwright.async_api import Page
import config
from utils import safe_sleep
from filters import apply_filters
from scraper import scrape_detail_page
from db import save_to_db, url_exists

logger = logging.getLogger(__name__)


async def crawl_single_search(page: Page, db_conn, search: Dict[str, Any],
                              max_torrents_remaining: int) -> int:
    """
    Crawl all results for a single search configuration.

    Args:
        page: Playwright page object
        db_conn: Database connection
        search: Search configuration dictionary
        max_torrents_remaining: Remaining torrent quota for this run

    Returns:
        Number of torrents scraped in this search
    """
    logger.info(f"Starting crawl for search: {search['label']}")

    # Apply filters to get search results
    try:
        search_url = await apply_filters(page, search)
    except Exception as e:
        logger.error(f"Failed to apply filters for {search['label']}: {e}")
        return 0

    position_counter = 0
    pages_seen = 0
    torrents_scraped = 0

    while True:
        pages_seen += 1
        logger.info(f"Processing results page {pages_seen} for search: {search['label']}")

        # Check page limit
        if pages_seen > config.SAFE_CRAWL["max_pages_per_search"]:
            logger.info(f"Reached max pages limit ({config.SAFE_CRAWL['max_pages_per_search']})")
            break

        # Extract all torrent links from current results page
        torrent_links = await extract_torrent_links(page)
        logger.info(f"Found {len(torrent_links)} torrents on page {pages_seen}")

        if not torrent_links:
            logger.info("No torrents found on this page - ending search")
            break

        # Process each torrent on this page
        for link in torrent_links:
            position_counter += 1

            # Check torrent quota
            if torrents_scraped >= max_torrents_remaining:
                logger.info(f"Reached max torrents limit for this run")
                return torrents_scraped

            # Check if we've already scraped this URL
            if url_exists(db_conn, link):
                logger.debug(f"URL already in database, skipping: {link}")
                continue

            try:
                # Scrape the detail page
                logger.info(f"Scraping torrent {position_counter}: {link}")
                data = await scrape_detail_page(page, link)

                # Add search metadata
                data["search_label"] = search["label"]
                data["search_position"] = position_counter
                data["search_url"] = search_url

                # Save to database
                if save_to_db(db_conn, data):
                    torrents_scraped += 1
                    logger.info(f"Saved torrent {torrents_scraped}/{max_torrents_remaining}: "
                              f"{data.get('title', 'Unknown')}")
                else:
                    logger.warning(f"Failed to save torrent: {link}")

                # Be polite - wait after each detail page visit
                await safe_sleep(config.SAFE_CRAWL, is_long=False)

                # Navigate back to search results
                await page.goto(search_url, wait_until="networkidle", timeout=30000)
                await safe_sleep(config.SAFE_CRAWL, is_long=False)

            except Exception as e:
                logger.error(f"Error scraping torrent {link}: {e}")
                # Try to navigate back to results on error
                try:
                    await page.goto(search_url, wait_until="networkidle", timeout=30000)
                    await safe_sleep(config.SAFE_CRAWL, is_long=False)
                except Exception as e2:
                    logger.error(f"Failed to navigate back to search results: {e2}")
                    return torrents_scraped

        # Look for next page link
        has_next = await go_to_next_page(page)

        if not has_next:
            logger.info("No more pages available")
            break

        # Wait after pagination
        await safe_sleep(config.SAFE_CRAWL, is_long=False)

        # Take long pause every N pages
        if pages_seen % config.SAFE_CRAWL["pages_before_long_pause"] == 0:
            logger.info(f"Taking long pause after {pages_seen} pages")
            await safe_sleep(config.SAFE_CRAWL, is_long=True)

    logger.info(f"Completed search '{search['label']}': {torrents_scraped} torrents scraped")
    return torrents_scraped


async def extract_torrent_links(page: Page) -> List[str]:
    """
    Extract all torrent detail page links from the current results page.

    Returns clean URLs in format: https://www.myanonamouse.net/t/1234567
    Filters out:
    - Forum post links (/f/t/)
    - Duplicate torrents with different URL parameters
    - Non-torrent links

    Args:
        page: Playwright page object

    Returns:
        List of clean torrent detail URLs
    """
    import re

    links = []
    seen_torrent_ids = set()

    try:
        # Get all links that contain /t/
        elements = await page.query_selector_all('a[href*="/t/"]')
        logger.debug(f"Found {len(elements)} links containing /t/")

        for element in elements:
            href = await element.get_attribute("href")
            if not href:
                continue

            # Skip forum post links (they have /f/t/ instead of just /t/)
            if "/f/t/" in href:
                logger.debug(f"Skipping forum link: {href}")
                continue

            # Extract torrent ID using regex
            # Match pattern like /t/1234567 (with or without query params)
            match = re.search(r'/t/(\d+)', href)
            if not match:
                continue

            torrent_id = match.group(1)

            # Skip if we've already seen this torrent ID
            if torrent_id in seen_torrent_ids:
                logger.debug(f"Skipping duplicate torrent ID: {torrent_id}")
                continue

            # Build clean URL with just the torrent ID
            clean_url = f"{config.MAM_BASE_URL}/t/{torrent_id}"

            links.append(clean_url)
            seen_torrent_ids.add(torrent_id)
            logger.debug(f"Added torrent: {clean_url}")

        logger.info(f"Extracted {len(links)} unique, clean torrent links")
        return links

    except Exception as e:
        logger.error(f"Error extracting torrent links: {e}")
        return []


async def go_to_next_page(page: Page) -> bool:
    """
    Navigate to the next page of search results if available.

    Uses MyAnonamouse-specific pagination button:
    <input type="button" data-newstartlocation="100" class="nextPage" value="next page">

    Args:
        page: Playwright page object

    Returns:
        True if successfully navigated to next page, False if no next page
    """
    try:
        # MyAnonamouse-specific next page button selector
        next_button = await page.query_selector('input.nextPage[type="button"]')

        if not next_button:
            logger.debug("No next page button found")
            return False

        # Check if button is visible and enabled
        is_visible = await next_button.is_visible()
        is_enabled = await next_button.is_enabled()

        if not is_visible or not is_enabled:
            logger.debug("Next page button exists but is not clickable")
            return False

        # Get the data-newstartlocation to log where we're going
        new_start = await next_button.get_attribute("data-newstartlocation")
        logger.info(f"Clicking next page button (start location: {new_start})")

        # Click the button
        await next_button.click()

        # Wait for navigation to complete
        await page.wait_for_load_state("networkidle", timeout=30000)
        logger.info("Successfully navigated to next page")
        return True

    except Exception as e:
        logger.error(f"Error navigating to next page: {e}")
        return False


async def crawl_all_searches(page: Page, db_conn,
                            selected_labels: Optional[List[str]] = None,
                            max_torrents: Optional[int] = None) -> Dict[str, int]:
    """
    Crawl all configured searches (or a subset).

    Args:
        page: Playwright page object
        db_conn: Database connection
        selected_labels: Optional list of search labels to run (None = all)
        max_torrents: Optional override for max_torrents_total

    Returns:
        Dictionary mapping search labels to number of torrents scraped
    """
    if max_torrents is None:
        max_torrents = config.SAFE_CRAWL["max_torrents_total"]

    # Filter searches if specific labels provided
    searches = config.SEARCHES
    if selected_labels:
        searches = [s for s in searches if s["label"] in selected_labels]
        logger.info(f"Running {len(searches)} selected searches: {selected_labels}")
    else:
        logger.info(f"Running all {len(searches)} configured searches")

    results = {}
    total_scraped = 0

    for search in searches:
        remaining = max_torrents - total_scraped

        if remaining <= 0:
            logger.info(f"Reached global max torrents limit ({max_torrents})")
            break

        logger.info(f"\n{'='*60}")
        logger.info(f"Starting search: {search['label']}")
        logger.info(f"Remaining quota: {remaining} torrents")
        logger.info(f"{'='*60}\n")

        try:
            scraped = await crawl_single_search(page, db_conn, search, remaining)
            results[search["label"]] = scraped
            total_scraped += scraped

            logger.info(f"Search '{search['label']}' complete: {scraped} torrents")

        except Exception as e:
            logger.error(f"Error in search '{search['label']}': {e}")
            results[search["label"]] = 0

        # Long pause between different searches
        if search != searches[-1]:  # Not the last search
            logger.info("Taking break between searches...")
            await safe_sleep(config.SAFE_CRAWL, is_long=True)

    logger.info(f"\n{'='*60}")
    logger.info(f"All searches complete!")
    logger.info(f"Total torrents scraped: {total_scraped}")
    logger.info(f"Results by search:")
    for label, count in results.items():
        logger.info(f"  {label}: {count}")
    logger.info(f"{'='*60}\n")

    return results


if __name__ == "__main__":
    # Test crawler
    import sys
    from playwright.async_api import async_playwright
    from auth import create_browser_context, ensure_logged_in
    from db import init_db, get_stats

    async def test_crawler():
        """Test the crawler module with a small test run."""
        print("Testing crawler module...")

        # Validate config first
        try:
            config.validate_config()
        except ValueError as e:
            print(f"Configuration error: {e}")
            print("\nPlease create a .env file based on .env.example")
            return

        # Set up logging
        from utils import setup_logging
        setup_logging(config.LOG_FILE, config.LOG_LEVEL)

        # Test mode: only 1 page, 5 torrents max
        test_limits = {
            **config.SAFE_CRAWL,
            "max_pages_per_search": 1,
            "max_torrents_total": 5,
        }
        config.SAFE_CRAWL.update(test_limits)

        print(f"\nTest mode: Limited to {test_limits['max_pages_per_search']} page(s), "
              f"{test_limits['max_torrents_total']} torrents max\n")

        # Initialize database
        db_conn = init_db(config.DB_PATH)

        async with async_playwright() as p:
            browser, context = await create_browser_context(p)

            # Create a new page
            if config.LOGIN_MODE == "cookies":
                page = await context.new_page()
            else:
                page = await context.new_page()

            # Ensure logged in
            if not await ensure_logged_in(page):
                print("Failed to log in")
                await browser.close()
                db_conn.close()
                return

            # Run crawler on first search only (test mode)
            print(f"Testing with first search: {config.SEARCHES[0]['label']}")

            try:
                results = await crawl_all_searches(
                    page, db_conn,
                    selected_labels=[config.SEARCHES[0]['label']],
                    max_torrents=test_limits['max_torrents_total']
                )

                print("\n=== Crawl Results ===")
                for label, count in results.items():
                    print(f"{label}: {count} torrents")

                # Show database stats
                print("\n=== Database Stats ===")
                stats = get_stats(db_conn)
                print(f"Total torrents in DB: {stats['total_torrents']}")

            except Exception as e:
                print(f"✗ Error testing crawler: {e}")
                import traceback
                traceback.print_exc()

            await browser.close()

        db_conn.close()

    asyncio.run(test_crawler())
