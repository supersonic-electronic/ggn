"""
Detail page scraper for MyAnonamouse torrent pages.
Extracts all relevant metadata from individual torrent detail pages.
UPDATED: Based on actual MyAnonamouse page structure inspection.
"""
import logging
import re
from typing import Dict, Any, Optional
from playwright.async_api import Page
import config
from utils import safe_sleep

logger = logging.getLogger(__name__)


async def scrape_detail_page(page: Page, url: str) -> Dict[str, Any]:
    """
    Scrape all metadata from a MyAnonamouse torrent detail page.

    Args:
        page: Playwright page object
        url: URL of the detail page (/t/ID)

    Returns:
        Dictionary containing all scraped fields
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
            "co_author": None,
            "size": None,
            "tags": None,
            "files_number": 0,
            "filetypes": None,
            "added_time": None,
            "description_html": None,
            "cover_image_url": None,
            "torrent_url": None,
        }

        # Get all text from the page for pattern matching
        body_text = await page.inner_text("body")
        lines = body_text.split("\n")

        # Strategy: Find label lines and extract the next line as value
        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # Title - line that says "Title" followed by the actual title
            if line_stripped == "Title" and i + 1 < len(lines):
                result["title"] = lines[i + 1].strip()
                logger.debug(f"Found title: {result['title']}")

            # Author extraction is now done via HTML selector (see below)
            # Tags extraction is now done via HTML selector (see below)
            # This text-based approach is kept for other fields

            # Size - line with "KiB", "MiB" or "GiB"
            elif ("KiB" in line_stripped or "MiB" in line_stripped or "GiB" in line_stripped) and result["size"] is None:
                # Extract size value
                size_match = re.search(r'([\d.]+\s+[KMG]iB)', line_stripped)
                if size_match:
                    result["size"] = size_match.group(1)
                    logger.debug(f"Found size: {result['size']}")

            # Files number - line that says "Files" followed by number
            elif line_stripped == "Files" and i + 1 < len(lines):
                try:
                    files_str = lines[i + 1].strip()
                    result["files_number"] = int(files_str)
                    logger.debug(f"Found files: {result['files_number']}")
                except ValueError:
                    pass

            # Filetypes - line that says "Filetypes" followed by types
            elif line_stripped == "Filetypes" and i + 1 < len(lines):
                filetypes_line = lines[i + 1].strip()
                result["filetypes"] = filetypes_line
                logger.debug(f"Found filetypes: {result['filetypes']}")

        # Author extraction - using HTML selector to get multiple authors
        try:
            # Find all author links: <a class="altColor" href="/tor/browse.php?author=...">
            author_links = await page.query_selector_all('a.altColor[href*="/tor/browse.php?author="]')

            if author_links:
                # Extract up to 2 authors
                authors = []
                for link in author_links[:2]:  # Limit to first 2 authors
                    author_text = await link.inner_text()
                    # Clean up the author name (remove &nbsp; and extra whitespace)
                    author_name = author_text.strip().replace('\xa0', ' ').strip()
                    if author_name:
                        authors.append(author_name)

                # Assign primary and co-author
                if len(authors) >= 1:
                    result["author"] = authors[0]
                    logger.debug(f"Found primary author: {result['author']}")
                if len(authors) >= 2:
                    result["co_author"] = authors[1]
                    logger.debug(f"Found co-author: {result['co_author']}")
        except Exception as e:
            logger.warning(f"Could not extract authors: {e}")

        # Tags extraction - using HTML selector for cleaner data
        try:
            # Find tags in: <span class="flex">Video Game, Fantasy, Art Book</span>
            # There are multiple span.flex elements, tags are usually the one with most commas
            flex_spans = await page.query_selector_all('span.flex')

            if flex_spans:
                # Find the span with the most commas (tags are comma-separated)
                max_commas = 0
                best_tags = None

                for span in flex_spans:
                    text = await span.inner_text()
                    comma_count = text.count(',')
                    if comma_count > max_commas:
                        max_commas = comma_count
                        best_tags = text.strip()

                if best_tags and max_commas >= 1:  # At least 1 comma for valid tags
                    result["tags"] = best_tags
                    logger.debug(f"Found tags: {result['tags'][:100]}")
        except Exception as e:
            logger.warning(f"Could not extract tags: {e}")

        # Download link - use selector since this is a link
        try:
            download_element = await page.query_selector('a[href*="/tor/download.php"]')
            if download_element:
                result["torrent_url"] = await download_element.get_attribute("href")
                if result["torrent_url"] and result["torrent_url"].startswith("/"):
                    result["torrent_url"] = config.MAM_BASE_URL + result["torrent_url"]
                logger.debug(f"Found download link: {result['torrent_url'][:50]}...")
        except Exception as e:
            logger.warning(f"Could not extract download link: {e}")

        # Cover image - using specific MyAnonamouse selector
        try:
            # Primary selector: #torDetPoster (the main cover image on MyM)
            cover_selectors = [
                '#torDetPoster',
                'img.torDetPoster',
                'img[id="torDetPoster"]',
            ]
            for selector in cover_selectors:
                img = await page.query_selector(selector)
                if img:
                    src = await img.get_attribute("src")
                    if src:
                        # MyM cover images are already full URLs
                        result["cover_image_url"] = src
                        logger.debug(f"Found cover image: {result['cover_image_url'][:50]}...")
                        break
        except Exception as e:
            logger.warning(f"Could not extract cover image: {e}")

        # Description - using specific MyAnonamouse selector
        try:
            # Primary selector: #torDesc (the main description on MyM)
            desc_selectors = [
                '#torDesc',
                'div#torDesc',
                'div.torDesc',
            ]
            for selector in desc_selectors:
                desc = await page.query_selector(selector)
                if desc:
                    # Get the text content of the description (br tags become line breaks)
                    result["description_html"] = await desc.inner_text()
                    logger.debug(f"Found description: {len(result['description_html'])} chars")
                    break

            if not result["description_html"]:
                logger.debug("No description found with standard selectors")
        except Exception as e:
            logger.warning(f"Could not extract description: {e}")

        # Added time - look for torrent ID or date patterns
        try:
            # Try to find upload date
            for i, line in enumerate(lines):
                # Look for date patterns like "2024-08-08" or "Added:"
                date_match = re.search(r'(\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}:\d{2})?)', line)
                if date_match:
                    result["added_time"] = date_match.group(1)
                    logger.debug(f"Found added time: {result['added_time']}")
                    break
        except Exception as e:
            logger.warning(f"Could not extract added time: {e}")

        # Log what we extracted
        logger.info(f"Successfully scraped: {result['title'] or 'Unknown'}")
        logger.debug(f"Author: {result['author']}, Size: {result['size']}, "
                    f"Files: {result['files_number']}, Filetypes: {result['filetypes']}")

        return result

    except Exception as e:
        logger.error(f"Error scraping detail page {url}: {e}")
        raise


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
        setup_logging(config.LOG_FILE, "DEBUG")

        # Test URL - use a known torrent
        test_url = "https://www.myanonamouse.net/t/1134304"

        async with async_playwright() as p:
            browser, context = await create_browser_context(p)
            page = await context.new_page()

            # Ensure logged in
            if not await ensure_logged_in(page):
                print("Failed to log in")
                await browser.close()
                return

            print(f"\nTesting scraper on: {test_url}")

            try:
                data = await scrape_detail_page(page, test_url)

                print("\n=== Scraped Data ===")
                print(f"Title: {data['title']}")
                print(f"Author: {data['author']}")
                print(f"Co-Author: {data.get('co_author', 'N/A')}")
                print(f"Size: {data['size']}")
                print(f"Tags: {data['tags'][:100] if data['tags'] else None}")
                print(f"Files: {data['files_number']}")
                print(f"Filetypes: {data['filetypes']}")
                print(f"Added: {data['added_time']}")
                print(f"Cover: {data['cover_image_url'][:50] if data['cover_image_url'] else None}")
                print(f"Download: {data['torrent_url'][:50] if data['torrent_url'] else None}")
                print(f"Description length: {len(data['description_html']) if data['description_html'] else 0} chars")

            except Exception as e:
                print(f"✗ Error testing scraper: {e}")
                import traceback
                traceback.print_exc()

            await browser.close()

    asyncio.run(test_scraper())
