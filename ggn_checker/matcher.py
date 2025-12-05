"""
Matching logic for comparing MAM books against GGn results.
Implements normalization and matching rules.
"""
import re
from typing import Optional


def normalize(s: str) -> str:
    """
    Normalize a string for matching.

    Steps:
    1. Convert to lowercase
    2. Replace all non-alphanumeric characters with spaces
    3. Collapse multiple spaces into one
    4. Strip leading/trailing whitespace

    Args:
        s: Input string

    Returns:
        Normalized string
    """
    if not s:
        return ""

    # Convert to lowercase
    s = s.lower()

    # Replace non-alphanumeric with spaces
    s = re.sub(r'[^a-z0-9]', ' ', s)

    # Collapse multiple spaces
    s = re.sub(r'\s+', ' ', s)

    # Strip whitespace
    s = s.strip()

    return s


def get_title_prefix(title: str, num_words: int = 5) -> str:
    """
    Extract the first N normalized words from a title.

    Args:
        title: Book title
        num_words: Number of words to extract (default: 5)

    Returns:
        Space-separated prefix of first N words
    """
    normalized = normalize(title)
    words = normalized.split()
    prefix_words = words[:num_words]
    return ' '.join(prefix_words)


def get_author_last_name(author: str) -> str:
    """
    Extract and normalize the author's last name.

    Takes the final token after splitting on whitespace.

    Args:
        author: Author name (e.g., "John Smith" or "Smith, John")

    Returns:
        Normalized last name
    """
    if not author:
        return ""

    # Split on whitespace and take last token
    tokens = author.strip().split()
    if not tokens:
        return ""

    last_name = tokens[-1]

    # Remove common punctuation from last name (e.g., "Smith," -> "Smith")
    last_name = last_name.rstrip(',.')

    # Normalize
    return normalize(last_name)


def match_title_prefix(title_prefix: str, ggn_group_name: str) -> bool:
    """
    Check if title prefix appears in GGn group name.

    Args:
        title_prefix: Normalized title prefix (first 5 words)
        ggn_group_name: GGn group name to check

    Returns:
        True if prefix appears in normalized group name
    """
    if not title_prefix or not ggn_group_name:
        return False

    normalized_group_name = normalize(ggn_group_name)

    # Check if prefix phrase appears anywhere in group name
    return title_prefix in normalized_group_name


def match_author_last_name(author_last_name: str, ggn_group_name: str, ggn_artists: list = None) -> bool:
    """
    Check if author's last name appears in GGn group name or Artists field.

    Args:
        author_last_name: Normalized author last name
        ggn_group_name: GGn group name to check
        ggn_artists: GGn Artists array (optional)

    Returns:
        True if author's last name appears in group name or Artists list
    """
    if not author_last_name:
        # If no author provided, skip author matching
        return True

    # Check in group name first
    if ggn_group_name:
        normalized_group_name = normalize(ggn_group_name)
        if author_last_name in normalized_group_name:
            return True

    # Check in Artists array
    if ggn_artists and isinstance(ggn_artists, list):
        for artist in ggn_artists:
            # Artists can be strings or dicts - handle both
            if isinstance(artist, str):
                artist_normalized = normalize(artist)
                if author_last_name in artist_normalized:
                    return True
            elif isinstance(artist, dict):
                # Try common artist name fields
                for field in ['name', 'Name', 'artist', 'Artist']:
                    if field in artist:
                        artist_name = normalize(str(artist[field]))
                        if author_last_name in artist_name:
                            return True

    # If we have no author info from GGn at all, be lenient
    # (no group name match AND no artists data)
    if not ggn_artists or len(ggn_artists) == 0:
        # No author info on GGn side - accept based on title match only
        return True

    return False


def is_strong_match(
    mam_title: str,
    mam_author: Optional[str],
    ggn_group: dict,
    title_prefix_words: int = 5
) -> bool:
    """
    Determine if a GGn group is a strong match for a MAM book.

    A strong match requires:
    1. CategoryID is exactly 3 (E-Books)
    2. First N words of title match as prefix in group name
    3. Author's last name appears in group name (if author provided)

    Args:
        mam_title: MAM book title
        mam_author: MAM book author (optional)
        ggn_group: GGn group dict with 'categoryId' and 'groupName'
        title_prefix_words: Number of title words to use (default: 5)

    Returns:
        True if all matching criteria are met
    """
    # Check category
    if ggn_group.get('categoryId') != 3:
        return False

    ggn_group_name = ggn_group.get('groupName', '')

    # Check title prefix
    title_prefix = get_title_prefix(mam_title, title_prefix_words)
    if not match_title_prefix(title_prefix, ggn_group_name):
        return False

    # Check author last name (if provided)
    if mam_author:
        author_last_name = get_author_last_name(mam_author)
        ggn_artists = ggn_group.get('Artists', [])
        if not match_author_last_name(author_last_name, ggn_group_name, ggn_artists):
            return False

    return True


if __name__ == "__main__":
    # Test normalization
    print("=" * 70)
    print("MATCHER MODULE TESTS")
    print("=" * 70)

    # Test normalize
    print("\nTest normalize():")
    test_cases = [
        "Video Game Design for Dummies",
        "StarCraft: Ghost--Spectres",
        "The Lord of the Rings: The Fellowship",
    ]
    for test in test_cases:
        print(f"  '{test}' -> '{normalize(test)}'")

    # Test title prefix
    print("\nTest get_title_prefix():")
    for test in test_cases:
        prefix = get_title_prefix(test, 5)
        print(f"  '{test}' -> '{prefix}'")

    # Test author last name
    print("\nTest get_author_last_name():")
    author_cases = [
        "Nate Kenyon",
        "J.R.R. Tolkien",
        "Smith, John",
        "Michael",
    ]
    for author in author_cases:
        last_name = get_author_last_name(author)
        print(f"  '{author}' -> '{last_name}'")

    # Test matching
    print("\nTest matching:")
    mam_title = "StarCraft: Ghost--Spectres"
    ggn_name = "Starcraft Ghost Spectres by Nate Kenyon EPUB"
    print(f"  MAM: '{mam_title}'")
    print(f"  GGn: '{ggn_name}'")
    prefix = get_title_prefix(mam_title, 5)
    print(f"  Prefix: '{prefix}'")
    print(f"  Title match: {match_title_prefix(prefix, ggn_name)}")
    print(f"  Author match (Kenyon): {match_author_last_name('kenyon', ggn_name)}")

    print("\n" + "=" * 70)
