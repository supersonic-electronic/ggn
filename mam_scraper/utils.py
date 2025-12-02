"""
Utility functions for safe crawling and timing.
Implements polite delays between requests to avoid overloading the server.
"""
import asyncio
import random
import time
import logging
from datetime import datetime
from typing import Dict, Any

# Configure logging
logger = logging.getLogger(__name__)


async def safe_sleep(config: Dict[str, Any], is_long: bool = False):
    """
    Sleep for a randomized duration to be polite to the server.

    Args:
        config: SAFE_CRAWL configuration dictionary
        is_long: If True, use the long pause duration; otherwise use random short delay
    """
    if is_long:
        delay = config["long_pause_seconds"]
        logger.info(f"Taking a long pause: {delay} seconds")
    else:
        delay = random.uniform(
            config["min_delay_seconds"],
            config["max_delay_seconds"]
        )
        logger.debug(f"Sleeping for {delay:.2f} seconds to be polite")

    await asyncio.sleep(delay)


def format_timestamp(dt: datetime = None) -> str:
    """
    Format a datetime object as an ISO 8601 timestamp string.

    Args:
        dt: datetime object (defaults to current time if None)

    Returns:
        ISO 8601 formatted timestamp string
    """
    if dt is None:
        dt = datetime.now()
    return dt.isoformat()


def normalize_tags(tags_string: str) -> str:
    """
    Normalize a comma-separated tags string.

    Args:
        tags_string: Raw tags string from the page

    Returns:
        Cleaned, normalized tags string
    """
    if not tags_string:
        return ""

    # Split by comma, strip whitespace, remove empty strings
    tags = [tag.strip() for tag in tags_string.split(",") if tag.strip()]

    # Join back with comma and space
    return ", ".join(tags)


def normalize_filetypes(filetypes_string: str) -> str:
    """
    Normalize a comma-separated filetypes string.

    Args:
        filetypes_string: Raw filetypes string from the page

    Returns:
        Cleaned, normalized filetypes string (lowercase)
    """
    if not filetypes_string:
        return ""

    # Split by comma, strip whitespace, lowercase, remove empty strings
    filetypes = [ft.strip().lower() for ft in filetypes_string.split(",") if ft.strip()]

    # Join back with comma and space
    return ", ".join(filetypes)


def parse_files_number(files_string: str) -> int:
    """
    Parse the number of files from a string like "2 files" or "1 file".

    Args:
        files_string: String containing file count

    Returns:
        Number of files as integer, or 0 if parsing fails
    """
    if not files_string:
        return 0

    try:
        # Extract first number from string
        import re
        match = re.search(r'\d+', files_string)
        if match:
            return int(match.group())
    except (ValueError, AttributeError):
        pass

    return 0


class RetryHandler:
    """
    Helper class for handling retries with exponential backoff.
    """

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        """
        Initialize retry handler.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds (will be multiplied exponentially)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.attempt = 0

    def should_retry(self) -> bool:
        """Check if we should retry based on current attempt count."""
        return self.attempt < self.max_retries

    async def wait_before_retry(self):
        """Wait with exponential backoff before the next retry."""
        if self.attempt > 0:
            # Exponential backoff: base_delay * 2^attempt
            delay = self.base_delay * (2 ** (self.attempt - 1))
            logger.warning(f"Retry attempt {self.attempt}/{self.max_retries}. "
                          f"Waiting {delay:.1f}s before retry...")
            await asyncio.sleep(delay)

        self.attempt += 1

    def reset(self):
        """Reset the retry counter."""
        self.attempt = 0


def setup_logging(log_file: str, log_level: str = "INFO"):
    """
    Set up logging configuration for the application.

    Args:
        log_file: Path to the log file
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    import os

    # Create log directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # Configure logging
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(file_formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(console_formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logger.info(f"Logging initialized. Log file: {log_file}, Level: {log_level}")


if __name__ == "__main__":
    # Test utilities
    import asyncio

    async def test():
        from config import SAFE_CRAWL

        print("Testing safe_sleep with short delay...")
        await safe_sleep(SAFE_CRAWL, is_long=False)

        print("Testing safe_sleep with long delay...")
        await safe_sleep(SAFE_CRAWL, is_long=True)

        print("\nTesting normalization functions...")
        print(f"Tags: {normalize_tags('Video Game Studies, Cultural Studies,  Media Studies  ')}")
        print(f"Filetypes: {normalize_filetypes('EPUB, PDF,  MOBI  ')}")
        print(f"Files number: {parse_files_number('2 files')}")

        print("\nTesting retry handler...")
        retry = RetryHandler(max_retries=3)
        while retry.should_retry():
            print(f"Attempt {retry.attempt + 1}")
            await retry.wait_before_retry()

    asyncio.run(test())
