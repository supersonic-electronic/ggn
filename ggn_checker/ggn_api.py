"""
GGn (GazelleGames) API client with rate limiting.
Implements compliant API access following GGn's 5 requests per 10 seconds rule.
"""
import time
import requests
from collections import deque
from typing import List, Dict, Optional
import logging

import config

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter implementing GGn's API limits:
    Maximum 5 requests per 10 seconds.
    """

    def __init__(self, max_requests: int = 5, window_seconds: int = 10):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_times = deque()

    def wait_if_needed(self):
        """
        Wait if necessary to comply with rate limits.
        Removes timestamps older than the window and sleeps if at limit.
        """
        current_time = time.time()

        # Remove timestamps outside the current window
        while self.request_times and self.request_times[0] < current_time - self.window_seconds:
            self.request_times.popleft()

        # If at limit, wait until oldest request falls out of window
        if len(self.request_times) >= self.max_requests:
            sleep_time = self.request_times[0] + self.window_seconds - current_time
            if sleep_time > 0:
                logger.debug(f"Rate limit reached. Sleeping for {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
                # Clean up again after sleep
                while self.request_times and self.request_times[0] < time.time() - self.window_seconds:
                    self.request_times.popleft()

        # Record this request
        self.request_times.append(time.time())


class GGNClient:
    """
    Client for GGn (GazelleGames) JSON API v3.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize GGn API client.

        Args:
            api_key: GGn API key (defaults to config.GGN_API_KEY)
        """
        self.api_key = api_key or config.GGN_API_KEY
        self.base_url = config.GGN_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-Key': self.api_key,
            'User-Agent': 'MAM-GGn-Checker/1.0'
        })

        # Rate limiter
        self.rate_limiter = RateLimiter(
            max_requests=config.MAX_REQUESTS_PER_WINDOW,
            window_seconds=config.RATE_LIMIT_WINDOW_SECONDS
        )

        logger.info("GGNClient initialized")

    def search_ebook(self, search_string: str) -> List[Dict]:
        """
        Search for e-books on GGn.

        Args:
            search_string: Book title to search for

        Returns:
            List of group dictionaries from API response
        """
        # Apply rate limiting
        self.rate_limiter.wait_if_needed()

        params = {
            'request': 'search',
            'search_type': 'torrents',
            'searchstr': search_string,
            'filter_cat[3]': '1',  # E-Books category
        }

        try:
            logger.debug(f"Searching GGn for: {search_string}")
            response = self.session.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Check for API errors
            if data.get('status') != 'success':
                error_msg = data.get('error', 'Unknown error')
                logger.error(f"API error: {error_msg}")
                return []

            # Extract groups from response
            # GGn API returns groups as dict with group IDs as keys when there are results
            # Or as empty list [] when there are no results
            response_data = data.get('response', {})

            # Handle empty result case
            if isinstance(response_data, list):
                logger.debug(f"Found 0 groups for '{search_string}' (empty response)")
                return []

            # Convert dict of groups to list
            results = []
            for group_id, group_data in response_data.items():
                # Add group ID to the data
                group_data['groupId'] = int(group_id)

                # Ensure required fields exist
                if 'CategoryID' in group_data:
                    group_data['categoryId'] = int(group_data['CategoryID'])
                if 'Name' in group_data:
                    group_data['groupName'] = group_data['Name']

                # Convert Torrents dict to list if needed
                if 'Torrents' in group_data and isinstance(group_data['Torrents'], dict):
                    group_data['torrents'] = list(group_data['Torrents'].values())

                results.append(group_data)

            logger.debug(f"Found {len(results)} groups for '{search_string}'")
            return results

        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error searching for '{search_string}': {e}")
            return []
        except ValueError as e:
            logger.error(f"JSON parse error for '{search_string}': {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error searching for '{search_string}': {e}")
            return []

    def get_group_details(self, group: Dict) -> Dict:
        """
        Extract relevant details from a GGn group result.

        Args:
            group: Group dict from API response

        Returns:
            Dict with extracted details
        """
        group_id = group.get('groupId')
        group_name = group.get('groupName', '')
        category_id = group.get('categoryId')

        # Extract torrent details
        torrents = group.get('torrents', [])

        # Collect unique formats
        formats = set()
        total_seeders = 0
        total_snatched = 0

        for torrent in torrents:
            # Format from GGn API Format field
            fmt = torrent.get('Format', '')
            if fmt:
                formats.add(fmt.upper())

            # Also check torrent names for additional formats
            torrent_name = torrent.get('ReleaseTitle', torrent.get('torrentName', ''))
            for fmt in ['EPUB', 'PDF', 'MOBI', 'AZW3', 'CBR', 'CBZ']:
                if fmt.lower() in torrent_name.lower():
                    formats.add(fmt)

            # Aggregate stats
            total_seeders += int(torrent.get('Seeders', torrent.get('seeders', 0)))
            total_snatched += int(torrent.get('Snatched', torrent.get('snatched', 0)))

        return {
            'group_id': group_id,
            'group_name': group_name,
            'category_id': category_id,
            'formats': sorted(list(formats)),
            'seeders': total_seeders,
            'snatched': total_snatched,
        }


if __name__ == "__main__":
    # Test the client
    import sys

    logging.basicConfig(level=logging.DEBUG)

    # Validate config
    try:
        config.validate_config()
    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)

    print("=" * 70)
    print("GGN API CLIENT TEST")
    print("=" * 70)

    client = GGNClient()

    # Test searches
    test_queries = [
        "Starcraft",
        "Video Game Design",
        "Fantasy",
    ]

    for query in test_queries:
        print(f"\nSearching for: '{query}'")
        results = client.search_ebook(query)
        print(f"  Found {len(results)} groups")

        for i, group in enumerate(results[:3], 1):  # Show first 3
            details = client.get_group_details(group)
            print(f"\n  Group {i}:")
            print(f"    ID: {details['group_id']}")
            print(f"    Name: {details['group_name']}")
            print(f"    Category: {details['category_id']}")
            print(f"    Formats: {', '.join(details['formats'])}")
            print(f"    Seeders: {details['seeders']}")
            print(f"    Snatched: {details['snatched']}")

        # Don't hammer API in test
        if query != test_queries[-1]:
            print("\n  (Waiting 2 seconds before next search...)")
            time.sleep(2)

    print("\n" + "=" * 70)
