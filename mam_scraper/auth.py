"""
Authentication module for MyAnonamouse login.
Supports two modes: reusing existing Firefox cookies or scripted form login.
"""
import logging
from typing import Optional
from playwright.async_api import Page, BrowserContext, Browser, async_playwright
import config

logger = logging.getLogger(__name__)


async def create_browser_context(playwright_instance):
    """
    Create a browser context based on the configured login mode.

    Args:
        playwright_instance: Playwright instance

    Returns:
        Tuple of (browser, context) objects
    """
    if config.LOGIN_MODE == "cookies" and config.FIREFOX_PROFILE_PATH:
        logger.info(f"Using existing Firefox profile: {config.FIREFOX_PROFILE_PATH}")

        # Launch browser with existing profile
        browser = await playwright_instance.firefox.launch_persistent_context(
            user_data_dir=config.FIREFOX_PROFILE_PATH,
            headless=config.BROWSER_HEADLESS,
            # Accept downloads if needed
            accept_downloads=True,
        )
        # In persistent context mode, browser IS the context
        return browser, browser

    else:
        logger.info("Using fresh browser context (form login mode)")

        # Launch regular browser
        if config.BROWSER_TYPE == "firefox":
            browser = await playwright_instance.firefox.launch(
                headless=config.BROWSER_HEADLESS
            )
        else:
            browser = await playwright_instance.chromium.launch(
                headless=config.BROWSER_HEADLESS
            )

        context = await browser.new_context(
            # Set a realistic user agent
            user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
            accept_downloads=True,
        )

        return browser, context


async def is_logged_in(page: Page) -> bool:
    """
    Check if the current page indicates the user is logged in.

    Args:
        page: Playwright page object

    Returns:
        True if logged in, False otherwise
    """
    try:
        # IMPORTANT: These selectors need to be verified by inspecting the actual site
        # Look for elements that only appear when logged in

        # Option 1: Check for logout link
        logout_link = await page.query_selector('a[href*="logout"]')
        if logout_link:
            logger.debug("Found logout link - user is logged in")
            return True

        # Option 2: Check for user menu/profile link
        user_menu = await page.query_selector('.user-menu, .username, #userMenu')
        if user_menu:
            logger.debug("Found user menu - user is logged in")
            return True

        # Option 3: Check if we're NOT on the login page
        current_url = page.url
        if "login" not in current_url.lower():
            # Try to find any element that indicates logged-in state
            # This is a fallback - should be replaced with actual selector
            nav_element = await page.query_selector('nav, .navbar, #mainNav')
            if nav_element:
                logger.debug("Not on login page and found navigation - assuming logged in")
                return True

        logger.debug("No logged-in indicators found")
        return False

    except Exception as e:
        logger.warning(f"Error checking login status: {e}")
        return False


async def perform_login(page: Page, username: str, password: str) -> bool:
    """
    Perform form-based login to MyAnonamouse.

    Args:
        page: Playwright page object
        username: MyAnonamouse username
        password: MyAnonamouse password

    Returns:
        True if login successful, False otherwise
    """
    try:
        login_url = f"{config.MAM_BASE_URL}/login.php"
        logger.info(f"Navigating to login page: {login_url}")

        await page.goto(login_url, wait_until="networkidle")

        # IMPORTANT: These selectors need to be verified by inspecting the actual login page
        # Common selector patterns for login forms:
        # - input[name="username"], input[name="email"], #username, #email
        # - input[name="password"], input[type="password"], #password
        # - button[type="submit"], input[type="submit"], button:has-text("Login")

        # Wait for login form to be visible
        logger.debug("Waiting for login form...")
        await page.wait_for_selector('form', timeout=10000)

        # Fill username field (try multiple possible selectors)
        username_selectors = [
            'input[name="username"]',
            'input[name="email"]',
            '#username',
            '#email',
            'input[type="text"]',
        ]

        username_filled = False
        for selector in username_selectors:
            try:
                if await page.query_selector(selector):
                    logger.debug(f"Filling username with selector: {selector}")
                    await page.fill(selector, username)
                    username_filled = True
                    break
            except Exception:
                continue

        if not username_filled:
            logger.error("Could not find username field. Selectors need to be updated.")
            return False

        # Fill password field
        password_selectors = [
            'input[name="password"]',
            'input[type="password"]',
            '#password',
        ]

        password_filled = False
        for selector in password_selectors:
            try:
                if await page.query_selector(selector):
                    logger.debug(f"Filling password with selector: {selector}")
                    await page.fill(selector, password)
                    password_filled = True
                    break
            except Exception:
                continue

        if not password_filled:
            logger.error("Could not find password field. Selectors need to be updated.")
            return False

        # Submit the form
        submit_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Login")',
            'button:has-text("Sign in")',
            'input[value*="Login"]',
        ]

        submit_clicked = False
        for selector in submit_selectors:
            try:
                if await page.query_selector(selector):
                    logger.debug(f"Clicking submit button with selector: {selector}")
                    await page.click(selector)
                    submit_clicked = True
                    break
            except Exception:
                continue

        if not submit_clicked:
            logger.error("Could not find submit button. Selectors need to be updated.")
            return False

        # Wait for navigation after login
        logger.debug("Waiting for navigation after login...")
        await page.wait_for_load_state("networkidle", timeout=15000)

        # Verify login was successful
        if await is_logged_in(page):
            logger.info("Login successful!")
            return True
        else:
            logger.error("Login form submitted but still not logged in")
            return False

    except Exception as e:
        logger.error(f"Error during login: {e}")
        return False


async def ensure_logged_in(page: Page) -> bool:
    """
    Ensure the user is logged in, performing login if necessary.

    Args:
        page: Playwright page object

    Returns:
        True if logged in (or login successful), False otherwise
    """
    # First check if already logged in
    logger.info("Checking if already logged in...")

    # Navigate to a known page to check login status
    try:
        await page.goto(f"{config.MAM_BASE_URL}/", wait_until="networkidle", timeout=15000)
    except Exception as e:
        logger.warning(f"Error navigating to homepage: {e}")

    if await is_logged_in(page):
        logger.info("Already logged in - no authentication needed")
        return True

    # Not logged in - attempt login if in form mode
    if config.LOGIN_MODE == "form":
        if not config.MAM_USERNAME or not config.MAM_PASSWORD:
            logger.error("Form login mode but credentials not configured")
            return False

        logger.info("Not logged in - attempting form login...")
        return await perform_login(page, config.MAM_USERNAME, config.MAM_PASSWORD)

    elif config.LOGIN_MODE == "cookies":
        logger.error("Cookie mode but not logged in - please log in manually in Firefox")
        return False

    else:
        logger.error(f"Unknown login mode: {config.LOGIN_MODE}")
        return False


if __name__ == "__main__":
    # Test authentication
    import asyncio

    async def test_auth():
        """Test the authentication module."""
        print("Testing authentication module...")

        # Validate config first
        try:
            config.validate_config()
        except ValueError as e:
            print(f"Configuration error: {e}")
            print("\nPlease create a .env file based on .env.example")
            return

        async with async_playwright() as p:
            browser, context = await create_browser_context(p)

            # Create a new page
            if config.LOGIN_MODE == "cookies":
                page = await context.new_page()
            else:
                page = await context.new_page()

            # Test login
            success = await ensure_logged_in(page)

            if success:
                print("\n✓ Authentication successful!")
                print(f"Current URL: {page.url}")

                # Try to get username or some logged-in indicator
                try:
                    # This selector needs to be verified
                    username_element = await page.query_selector('.username, .user-menu')
                    if username_element:
                        username = await username_element.inner_text()
                        print(f"Logged in as: {username}")
                except Exception:
                    pass
            else:
                print("\n✗ Authentication failed")
                print("Please check your credentials and selectors")

            await browser.close()

    asyncio.run(test_auth())
