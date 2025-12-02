"""
Detail page scraper for MyAnonamouse torrent pages.
Extracts all relevant metadata from individual torrent detail pages.
"""
import logging
from typing import Dict, Any, Optional
from playwright.async_api import Page
import config
from utils import safe_sleep, normalize_tags, normalize_filetypes, parse_files_number

logger = logging.getLogger(__name__)


async def scrape_detail_page(page: Page, url: str) -> Dict[str, Any]:
    """
    Scrape all metadata from a MyAnonamouse torrent detail page.

    Args:
        page: Playwright page object
        url: URL of the detail page (/t/ID)

    Returns:
        Dictionary containing all scraped fields:
        - detail_url: URL of the detail page
        - title: Book title
        - author: Book author(s)
        - size: Torrent size (e.g., "40.83 MiB")
        - tags: Comma-separated tags
        - files_number: Number of files
        - filetypes: Comma-separated filetypes
        - added_time: When torrent was added
        - description_html: Full HTML description
        - cover_image_url: URL to cover image
        - torrent_url: Download URL for the torrent
    """
    logger.info(f"Scraping detail page: {url}")

    try:
        # Navigate to detail page
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await safe_sleep(config.SAFE_CRAWL, is_long=False)

        # Initialize result dictionary
        result = {
            "detail_url": url,
            "title": None,
            "author": None,
            "size": None,
            "tags": None,
            "files_number": 0,
            "filetypes": None,
            "added_time": None,
            "description_html": None,
            "cover_image_url": None,
            "torrent_url": None,
        }

        # IMPORTANT: All these selectors need to be verified by inspecting actual detail pages
        # Based on your example URL: /t/1060422

        # 1. Extract Title
        title_selectors = [
            'h1.torrent-title',
            'h1#torrent-title',
            '.torrent-header h1',
            'h1',  # Fallback to first h1
        ]
        result["title"] = await _extract_text(page, title_selectors, "title")

        # 2. Extract Author
        author_selectors = [
            '.author',
            '.torrent-author',
            'span:has-text("Author:") + span',
            'dt:has-text("Author") + dd',
            'div:has-text("Author:") span',
        ]
        result["author"] = await _extract_text(page, author_selectors, "author")

        # 3. Extract Size
        size_selectors = [
            '.size',
            '.torrent-size',
            'span:has-text("Size:") + span',
            'dt:has-text("Size") + dd',
            'div:has-text("Size:") span',
        ]
        result["size"] = await _extract_text(page, size_selectors, "size")

        # 4. Extract Tags
        tags_selectors = [
            '.tags',
            '.torrent-tags',
            'span:has-text("Tags:") + span',
            'dt:has-text("Tags") + dd',
            'div.tags span',
        ]
        tags_text = await _extract_text(page, tags_selectors, "tags")
        if tags_text:
            result["tags"] = normalize_tags(tags_text)

        # 5. Extract Files Number
        files_selectors = [
            '.files-count',
            'span:has-text("Files:") + span',
            'dt:has-text("Files") + dd',
            'span:has-text("file")',
        ]
        files_text = await _extract_text(page, files_selectors, "files_number")
        if files_text:
            result["files_number"] = parse_files_number(files_text)

        # 6. Extract Filetypes
        filetype_selectors = [
            '.filetypes',
            '.file-types',
            'span:has-text("Format:") + span',
            'dt:has-text("Format") + dd',
            'dt:has-text("Type") + dd',
        ]
        filetype_text = await _extract_text(page, filetype_selectors, "filetypes")
        if filetype_text:
            result["filetypes"] = normalize_filetypes(filetype_text)

        # 7. Extract Added Time
        added_time_selectors = [
            '.added-time',
            '.upload-time',
            'span:has-text("Added:") + span',
            'dt:has-text("Added") + dd',
            'time[datetime]',
        ]
        result["added_time"] = await _extract_text(page, added_time_selectors, "added_time")

        # 8. Extract Description (HTML)
        description_selectors = [
            '.description',
            '.torrent-description',
            '#description',
            'div.description',
            '.torrent-details .description',
        ]
        result["description_html"] = await _extract_html(page, description_selectors, "description")

        # 9. Extract Cover Image URL
        cover_selectors = [
            'img.cover',
            'img.torrent-cover',
            'img[alt*="cover"]',
            '.cover-image img',
            '.torrent-image img',
        ]
        result["cover_image_url"] = await _extract_image_url(page, cover_selectors, "cover_image")

        # 10. Extract Torrent Download URL
        download_selectors = [
            'a[href*="/tor/download.php"]',
            'a[href*="download"]',
            'a.download-link',
            'a:has-text("Download")',
        ]
        result["torrent_url"] = await _extract_link_url(page, download_selectors, "torrent_url")

        # Log what we found
        logger.info(f"Successfully scraped: {result['title']}")
        logger.debug(f"Author: {result['author']}, Size: {result['size']}, "
                    f"Files: {result['files_number']}, Filetypes: {result['filetypes']}")

        return result

    except Exception as e:
        logger.error(f"Error scraping detail page {url}: {e}")
        # Return partial result with at least the URL
        result["detail_url"] = url
        return result


async def _extract_text(page: Page, selectors: list, field_name: str) -> Optional[str]:
    """
    Extract text content using multiple selector attempts.

    Args:
        page: Playwright page object
        selectors: List of CSS selectors to try
        field_name: Name of field (for logging)

    Returns:
        Extracted text or None
    """
    for selector in selectors:
        try:
            element = await page.query_selector(selector)
            if element:
                text = await element.inner_text()
                text = text.strip()
                if text:
                    logger.debug(f"Extracted {field_name} using selector: {selector}")
                    return text
        except Exception as e:
            logger.debug(f"Selector {selector} failed for {field_name}: {e}")
            continue

    logger.warning(f"Could not extract {field_name} - selectors need verification")
    return None


async def _extract_html(page: Page, selectors: list, field_name: str) -> Optional[str]:
    """
    Extract HTML content using multiple selector attempts.

    Args:
        page: Playwright page object
        selectors: List of CSS selectors to try
        field_name: Name of field (for logging)

    Returns:
        Extracted HTML or None
    """
    for selector in selectors:
        try:
            element = await page.query_selector(selector)
            if element:
                html = await element.inner_html()
                html = html.strip()
                if html:
                    logger.debug(f"Extracted {field_name} HTML using selector: {selector}")
                    return html
        except Exception as e:
            logger.debug(f"Selector {selector} failed for {field_name}: {e}")
            continue

    logger.warning(f"Could not extract {field_name} HTML - selectors need verification")
    return None


async def _extract_image_url(page: Page, selectors: list, field_name: str) -> Optional[str]:
    """
    Extract image URL from img src attribute.

    Args:
        page: Playwright page object
        selectors: List of CSS selectors to try
        field_name: Name of field (for logging)

    Returns:
        Image URL or None
    """
    for selector in selectors:
        try:
            element = await page.query_selector(selector)
            if element:
                src = await element.get_attribute("src")
                if src:
                    # Make absolute URL if relative
                    if src.startswith("//"):
                        src = "https:" + src
                    elif src.startswith("/"):
                        src = config.MAM_BASE_URL + src
                    logger.debug(f"Extracted {field_name} using selector: {selector}")
                    return src
        except Exception as e:
            logger.debug(f"Selector {selector} failed for {field_name}: {e}")
            continue

    logger.warning(f"Could not extract {field_name} - selectors need verification")
    return None


async def _extract_link_url(page: Page, selectors: list, field_name: str) -> Optional[str]:
    """
    Extract URL from anchor href attribute.

    Args:
        page: Playwright page object
        selectors: List of CSS selectors to try
        field_name: Name of field (for logging)

    Returns:
        Link URL or None
    """
    for selector in selectors:
        try:
            element = await page.query_selector(selector)
            if element:
                href = await element.get_attribute("href")
                if href:
                    # Make absolute URL if relative
                    if href.startswith("/"):
                        href = config.MAM_BASE_URL + href
                    logger.debug(f"Extracted {field_name} using selector: {selector}")
                    return href
        except Exception as e:
            logger.debug(f"Selector {selector} failed for {field_name}: {e}")
            continue

    logger.warning(f"Could not extract {field_name} - selectors need verification")
    return None


if __name__ == "__main__":
    # Test scraper
    import asyncio
    from playwright.async_api import async_playwright
    from auth import create_browser_context, ensure_logged_in

    async def test_scraper():
        """Test the scraper module."""
        print("Testing scraper module...")

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

        # Ask for a test URL
        test_url = input("\nEnter a MyAnonamouse torrent detail URL (e.g., /t/1060422): ").strip()
        if not test_url:
            test_url = "https://www.myanonamouse.net/t/1060422"
            print(f"Using example URL: {test_url}")
        elif not test_url.startswith("http"):
            test_url = config.MAM_BASE_URL + test_url

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

            # Test scraping
            print(f"\nScraping: {test_url}")
            try:
                result = await scrape_detail_page(page, test_url)

                print("\n=== Scrape Results ===")
                for key, value in result.items():
                    if key == "description_html" and value:
                        print(f"{key}: {value[:100]}..." if len(value) > 100 else f"{key}: {value}")
                    else:
                        print(f"{key}: {value}")

                # Take a screenshot for verification
                screenshot_path = "test_scraper_result.png"
                await page.screenshot(path=screenshot_path)
                print(f"\nScreenshot saved to: {screenshot_path}")

            except Exception as e:
                print(f"✗ Error testing scraper: {e}")
                import traceback
                traceback.print_exc()

            await browser.close()

    asyncio.run(test_scraper())
