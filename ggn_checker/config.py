"""
Configuration for GGn (GazelleGames) API checker.
Reads API key from environment and defines constants.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# GGn API Configuration
GGN_API_KEY = os.getenv("GGN_API_KEY", "")
GGN_BASE_URL = "https://gazellegames.net/api.php"

# GGn E-Books Category ID
EBOOKS_CATEGORY_ID = 3

# API Rate Limiting
# GGn allows maximum 5 requests per 10 seconds
MAX_REQUESTS_PER_WINDOW = 5
RATE_LIMIT_WINDOW_SECONDS = 10

# Matching Configuration
# Number of words from title to use for matching
TITLE_PREFIX_WORDS = 5

# Progress Reporting
PROGRESS_INTERVAL = 25  # Print progress every N rows


def validate_config():
    """Validate required configuration values."""
    errors = []

    if not GGN_API_KEY:
        errors.append("GGN_API_KEY is required. Set it in .env file.")

    if errors:
        raise ValueError("Configuration errors:\n- " + "\n- ".join(errors))

    return True


if __name__ == "__main__":
    # Test configuration loading
    print("Configuration loaded successfully!")
    print(f"API Base URL: {GGN_BASE_URL}")
    print(f"E-Books Category ID: {EBOOKS_CATEGORY_ID}")
    print(f"Rate Limit: {MAX_REQUESTS_PER_WINDOW} requests per {RATE_LIMIT_WINDOW_SECONDS} seconds")

    try:
        validate_config()
        print("\n✓ Configuration validation passed!")
        print(f"✓ GGN_API_KEY found: {GGN_API_KEY[:10]}..." if GGN_API_KEY else "✗ GGN_API_KEY not set")
    except ValueError as e:
        print(f"\n✗ Configuration validation failed:\n{e}")
