"""
Filter application module for MyAnonamouse search/browse pages.
SIMPLIFIED: Uses the search box since default filters are already set on MyM account.
"""
import logging
from typing import Dict, Any
from playwright.async_api import Page
import config
from utils import safe_sleep

logger = logging.getLogger(__name__)


async def apply_filters(page: Page, search: Dict[str, Any]) -> str:
    """
    Apply search by typing in the search box.

    NOTE: This assumes you've already set your default filters on MyAnonamouse:
    - Category: eBooks
    - Language: English
    - Tags: Enabled
    - Filetype: Enabled

    We just need to type the search query and submit.

    Args:
        page: Playwright page object
        search: Search configuration dictionary containing:
            - label: Search label for tracking
            - tags: List of tags to search for (e.g., ["Video Game"])
            - filetypes: List of filetypes (e.g., ["epub", "pdf"])

    Returns:
        The resulting search URL after search is submitted
    """
    logger.info(f"Applying search for: {search['label']}")

    # Navigate to browse page
    browse_url = f"{config.MAM_BASE_URL}/tor/browse.php"
    logger.debug(f"Navigating to: {browse_url}")

    try:
        await page.goto(browse_url, wait_until="networkidle", timeout=30000)
        await safe_sleep(config.SAFE_CRAWL, is_long=False)

        # Build search query from tags and filetypes
        search_terms = []

        # Add tags to search query
        if search.get("tags"):
            search_terms.extend(search["tags"])
            logger.debug(f"Search tags: {search['tags']}")

        # Add filetypes to search query (optional - may not be needed if filetype filter is set)
        # if search.get("filetypes"):
        #     search_terms.extend(search["filetypes"])
        #     logger.debug(f"Search filetypes: {search['filetypes']}")

        # Combine into single search string
        search_query = " ".join(search_terms)
        logger.info(f"Search query: '{search_query}'")

        # Find the search box using the selector you provided
        # Selector: input#torTitle or input[name="tor[text]"]
        search_box_selector = '#torTitle'

        logger.debug(f"Looking for search box: {search_box_selector}")
        search_box = await page.query_selector(search_box_selector)

        if not search_box:
            # Try alternative selector
            search_box_selector = 'input[name="tor[text]"]'
            logger.debug(f"Trying alternative selector: {search_box_selector}")
            search_box = await page.query_selector(search_box_selector)

        if not search_box:
            raise Exception("Could not find search box with selector #torTitle or input[name='tor[text]']")

        logger.debug(f"Found search box, typing query: {search_query}")
        await search_box.fill(search_query)

        # Simply press Enter in the search box (most reliable method)
        logger.debug("Pressing Enter to submit search")
        await search_box.press('Enter')

        # Wait for results to load
        logger.debug("Waiting for search results to load...")
        await page.wait_for_load_state("networkidle", timeout=30000)
        await safe_sleep(config.SAFE_CRAWL, is_long=False)

        # Get the resulting URL
        result_url = page.url
        logger.info(f"Search complete. Result URL: {result_url}")

        return result_url

    except Exception as e:
        logger.error(f"Error applying search: {e}")
        raise


async def get_results_count(page: Page) -> int:
    """
    Get the total number of search results from the page.

    Args:
        page: Playwright page object

    Returns:
        Number of results, or -1 if couldn't determine
    """
    try:
        # Common patterns for results count display:
        # "Showing 1-50 of 234 results"
        # "234 torrents found"
        # "Results: 234"

        count_selectors = [
            '.results-count',
            '.search-results-count',
            '#results-count',
            'span:has-text("results")',
            'div:has-text("torrents")',
            'div:has-text("found")',
        ]

        for selector in count_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    # Extract number from text
                    import re
                    match = re.search(r'(\d+)\s*(results|torrents|found)', text, re.IGNORECASE)
                    if match:
                        count = int(match.group(1))
                        logger.debug(f"Found {count} results")
                        return count
            except Exception:
                continue

        logger.debug("Could not determine results count")
        return -1

    except Exception as e:
        logger.warning(f"Error getting results count: {e}")
        return -1


if __name__ == "__main__":
    # Test filters
    import asyncio
    from playwright.async_api import async_playwright
    from auth import create_browser_context, ensure_logged_in

    async def test_filters():
        """Test the filters module."""
        print("Testing simplified search (using default MyM filters)...")

        # Validate config first
        try:
            config.validate_config()
        except ValueError as e:
            print(f"Configuration error: {e}")
            print("\nPlease create a .env file based on .env.example")
            return

        # Set up logging
        from utils import setup_logging
        setup_logging(config.LOG_FILE, "DEBUG")

        async with async_playwright() as p:
            browser, context = await create_browser_context(p)
            page = await context.new_page()

            # Ensure logged in
            if not await ensure_logged_in(page):
                print("Failed to log in")
                await browser.close()
                return

            # Test first search configuration
            test_search = config.SEARCHES[0]
            print(f"\nTesting search: {test_search['label']}")
            print(f"Search query: {' '.join(test_search.get('tags', []))}")

            try:
                result_url = await apply_filters(page, test_search)
                print(f"\n✓ Search completed successfully")
                print(f"Result URL: {result_url}")

                # Get results count
                count = await get_results_count(page)
                if count >= 0:
                    print(f"Found {count} results")

                # Wait a bit so you can see the results
                print("\nWaiting 5 seconds so you can see the results...")
                await asyncio.sleep(5)

            except Exception as e:
                print(f"✗ Error testing search: {e}")
                import traceback
                traceback.print_exc()

            await browser.close()

    asyncio.run(test_filters())
