"""
Configuration for MyAnonamouse eBook crawler.
Defines search parameters and safe crawling settings.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MyAnonamouse credentials and settings
MAM_USERNAME = os.getenv("MAM_USERNAME", "")
MAM_PASSWORD = os.getenv("MAM_PASSWORD", "")
MAM_BASE_URL = os.getenv("MAM_BASE_URL", "https://www.myanonamouse.net")

# Authentication mode: "cookies" or "form"
LOGIN_MODE = os.getenv("LOGIN_MODE", "form")
FIREFOX_PROFILE_PATH = os.getenv("FIREFOX_PROFILE_PATH", "")

# VPN Bypass: Use firejail to bypass VPN (requires firefox-no-vpn-wrapper.sh)
USE_VPN_BYPASS = os.getenv("USE_VPN_BYPASS", "True").lower() in ("true", "1", "yes")

# Search definitions
# Each search targets specific combinations of tags and filetypes
SEARCHES = [
    {
        "label": "Video Game + epub",
        "category": "eBooks",
        "language": "English",
        "tags": ["Video Game"],
        "filetypes": ["epub"],
    },
    {
        "label": "Video Game + pdf",
        "category": "eBooks",
        "language": "English",
        "tags": ["Video Game"],
        "filetypes": ["pdf"],
    },
    {
        "label": "Video Game + mobi",
        "category": "eBooks",
        "language": "English",
        "tags": ["Video Game"],
        "filetypes": ["mobi"],
    },
    {
        "label": "Video Game + all formats",
        "category": "eBooks",
        "language": "English",
        "tags": ["Video Game"],
        "filetypes": ["epub", "pdf", "mobi"],
    },
]

# Safe crawling parameters
# These are designed to be polite to the MyAnonamouse servers
SAFE_CRAWL = {
    # Minimum wait time after each page action (seconds)
    "min_delay_seconds": float(os.getenv("MIN_DELAY_SECONDS", "3")),

    # Maximum wait time for random sleep range (seconds)
    "max_delay_seconds": float(os.getenv("MAX_DELAY_SECONDS", "7")),

    # Number of pages to crawl before taking a long pause
    "pages_before_long_pause": int(os.getenv("PAGES_BEFORE_LONG_PAUSE", "15")),

    # Duration of long pause (seconds)
    "long_pause_seconds": int(os.getenv("LONG_PAUSE_SECONDS", "20")),

    # Maximum pages to crawl per search (safety limit)
    "max_pages_per_search": int(os.getenv("MAX_PAGES_PER_SEARCH", "50")),

    # Maximum total torrents to scrape per run (safety limit)
    "max_torrents_total": int(os.getenv("MAX_TORRENTS_TOTAL", "1000")),

    # Maximum retry attempts for transient errors
    "max_retries": int(os.getenv("MAX_RETRIES", "3")),
}

# Database settings
DB_PATH = os.getenv("DB_PATH", "mam.db")

# Logging settings
LOG_FILE = os.getenv("LOG_FILE", "logs/mam_errors.log")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Browser settings
BROWSER_HEADLESS = os.getenv("BROWSER_HEADLESS", "False").lower() in ("true", "1", "yes")
BROWSER_TYPE = os.getenv("BROWSER_TYPE", "firefox")  # firefox or chromium


def validate_config():
    """Validate required configuration values."""
    errors = []

    if LOGIN_MODE == "form":
        if not MAM_USERNAME:
            errors.append("MAM_USERNAME is required when LOGIN_MODE=form")
        if not MAM_PASSWORD:
            errors.append("MAM_PASSWORD is required when LOGIN_MODE=form")
    elif LOGIN_MODE == "cookies":
        if not FIREFOX_PROFILE_PATH:
            errors.append("FIREFOX_PROFILE_PATH is required when LOGIN_MODE=cookies")
        if not os.path.exists(FIREFOX_PROFILE_PATH):
            errors.append(f"Firefox profile path does not exist: {FIREFOX_PROFILE_PATH}")
    else:
        errors.append(f"Invalid LOGIN_MODE: {LOGIN_MODE}. Must be 'form' or 'cookies'")

    if errors:
        raise ValueError("Configuration errors:\n- " + "\n- ".join(errors))

    return True


if __name__ == "__main__":
    # Test configuration loading
    print("Configuration loaded successfully!")
    print(f"Login mode: {LOGIN_MODE}")
    print(f"Number of searches defined: {len(SEARCHES)}")
    print(f"Safe crawl settings: {SAFE_CRAWL}")

    try:
        validate_config()
        print("\nConfiguration validation passed!")
    except ValueError as e:
        print(f"\nConfiguration validation failed:\n{e}")
