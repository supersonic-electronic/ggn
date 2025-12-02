"""
Filter application module for MyAnonamouse search/browse pages.
Applies category, language, tags, and filetype filters.
"""
import logging
from typing import Dict, Any
from playwright.async_api import Page
import config
from utils import safe_sleep

logger = logging.getLogger(__name__)


async def apply_filters(page: Page, search: Dict[str, Any]) -> str:
    """
    Apply search filters for category, language, tags, and filetypes.

    Args:
        page: Playwright page object
        search: Search configuration dictionary containing:
            - label: Search label for tracking
            - category: Category filter (e.g., "eBooks")
            - language: Language filter (e.g., "English")
            - tags: List of tags to filter by (e.g., ["Video Game"])
            - filetypes: List of filetypes (e.g., ["epub", "pdf"])

    Returns:
        The resulting search URL after filters are applied
    """
    logger.info(f"Applying filters for search: {search['label']}")

    # Navigate to browse page
    browse_url = f"{config.MAM_BASE_URL}/tor/browse.php"
    logger.debug(f"Navigating to: {browse_url}")

    try:
        await page.goto(browse_url, wait_until="networkidle", timeout=30000)
        await safe_sleep(config.SAFE_CRAWL, is_long=False)

        # IMPORTANT: All these selectors need to be verified by inspecting the actual site
        # The following are common patterns but may need adjustment

        # 1. Set Category filter
        if search.get("category"):
            category = search["category"]
            logger.debug(f"Setting category: {category}")

            # Try multiple possible selector patterns for category dropdown
            category_selectors = [
                'select[name="cat"]',
                'select[name="category"]',
                'select#cat',
                'select#category',
            ]

            category_set = False
            for selector in category_selectors:
                try:
                    if await page.query_selector(selector):
                        await page.select_option(selector, label=category)
                        category_set = True
                        logger.debug(f"Category set using selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue

            if not category_set:
                logger.warning(f"Could not set category filter. Selector needs verification.")

        # 2. Set Language filter
        if search.get("language"):
            language = search["language"]
            logger.debug(f"Setting language: {language}")

            language_selectors = [
                'select[name="lang"]',
                'select[name="language"]',
                'select#lang',
                'select#language',
            ]

            language_set = False
            for selector in language_selectors:
                try:
                    if await page.query_selector(selector):
                        await page.select_option(selector, label=language)
                        language_set = True
                        logger.debug(f"Language set using selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue

            if not language_set:
                logger.warning(f"Could not set language filter. Selector needs verification.")

        # 3. Enable Tags filter toggle (if needed)
        logger.debug("Enabling tags filter...")
        tag_toggle_selectors = [
            'input[name="tags"]',
            'input#tags',
            '#tag_toggle',
            'input[type="checkbox"][name*="tag"]',
        ]

        for selector in tag_toggle_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    is_checked = await element.is_checked()
                    if not is_checked:
                        await element.check()
                        logger.debug(f"Tags toggle enabled using: {selector}")
                    break
            except Exception:
                continue

        # 4. Set Tags
        if search.get("tags"):
            tags = search["tags"]
            logger.debug(f"Setting tags: {tags}")

            # Tags might be:
            # - A text input where you type tag names
            # - Checkboxes for each tag
            # - A multi-select dropdown

            # Option A: Text input for tags
            tag_input_selectors = [
                'input[name="tags"]',
                'input[name="tag"]',
                'input#tags',
                'input.tag-input',
            ]

            tag_input_found = False
            for selector in tag_input_selectors:
                try:
                    if await page.query_selector(selector):
                        # Type all tags separated by comma or space
                        tag_string = ", ".join(tags)
                        await page.fill(selector, tag_string)
                        tag_input_found = True
                        logger.debug(f"Tags filled using selector: {selector}")
                        break
                except Exception:
                    continue

            # Option B: Individual checkboxes (if text input didn't work)
            if not tag_input_found:
                for tag in tags:
                    checkbox_selectors = [
                        f'input[type="checkbox"][value*="{tag}"]',
                        f'input[type="checkbox"][name*="tag"][value*="{tag}"]',
                        f'label:has-text("{tag}") input[type="checkbox"]',
                    ]

                    for selector in checkbox_selectors:
                        try:
                            element = await page.query_selector(selector)
                            if element:
                                await element.check()
                                logger.debug(f"Tag checkbox '{tag}' checked")
                                break
                        except Exception:
                            continue

        # 5. Enable FileType filter toggle (if needed)
        logger.debug("Enabling filetype filter...")
        filetype_toggle_selectors = [
            'input[name="filetype"]',
            'input#filetype',
            '#filetype_toggle',
            'input[type="checkbox"][name*="filetype"]',
        ]

        for selector in filetype_toggle_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    is_checked = await element.is_checked()
                    if not is_checked:
                        await element.check()
                        logger.debug(f"Filetype toggle enabled using: {selector}")
                    break
            except Exception:
                continue

        # 6. Set FileTypes
        if search.get("filetypes"):
            filetypes = search["filetypes"]
            logger.debug(f"Setting filetypes: {filetypes}")

            # Filetypes are likely checkboxes
            for filetype in filetypes:
                checkbox_selectors = [
                    f'input[type="checkbox"][value="{filetype.lower()}"]',
                    f'input[type="checkbox"][value="{filetype.upper()}"]',
                    f'input[type="checkbox"][name*="filetype"][value*="{filetype}"]',
                    f'label:has-text("{filetype}") input[type="checkbox"]',
                ]

                filetype_set = False
                for selector in checkbox_selectors:
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            await element.check()
                            filetype_set = True
                            logger.debug(f"Filetype '{filetype}' checked")
                            break
                    except Exception:
                        continue

                if not filetype_set:
                    logger.warning(f"Could not check filetype: {filetype}")

        # 7. Submit the search/filter form
        logger.debug("Submitting search form...")
        submit_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Search")',
            'button:has-text("Apply")',
            'button:has-text("Filter")',
            'input[value="Search"]',
        ]

        submit_clicked = False
        for selector in submit_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    await element.click()
                    submit_clicked = True
                    logger.debug(f"Submit button clicked using: {selector}")
                    break
            except Exception:
                continue

        if not submit_clicked:
            logger.warning("Could not find submit button - filters may not be applied")
            # Some sites auto-submit on filter change, so this might be okay

        # Wait for results to load
        logger.debug("Waiting for search results to load...")
        await page.wait_for_load_state("networkidle", timeout=30000)
        await safe_sleep(config.SAFE_CRAWL, is_long=False)

        # Get the resulting URL
        result_url = page.url
        logger.info(f"Filters applied. Result URL: {result_url}")

        return result_url

    except Exception as e:
        logger.error(f"Error applying filters: {e}")
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
        print("Testing filters module...")

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
                return

            # Test first search configuration
            test_search = config.SEARCHES[0]
            print(f"\nTesting search: {test_search['label']}")

            try:
                result_url = await apply_filters(page, test_search)
                print(f"✓ Filters applied successfully")
                print(f"Result URL: {result_url}")

                # Get results count
                count = await get_results_count(page)
                if count >= 0:
                    print(f"Found {count} results")

                # Take a screenshot for verification
                screenshot_path = "test_filters_result.png"
                await page.screenshot(path=screenshot_path)
                print(f"\nScreenshot saved to: {screenshot_path}")

            except Exception as e:
                print(f"✗ Error testing filters: {e}")

            await browser.close()

    asyncio.run(test_filters())
