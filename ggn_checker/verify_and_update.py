#!/usr/bin/env python3
"""
Direct MAM DB to GGn verification with incremental master DB updates.

This script:
1. Reads directly from MAM database
2. Identifies books that need GGn verification
3. Verifies against GGn API
4. Updates master database incrementally
"""

import sqlite3
import pandas as pd
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple
import sys

from ggn_api import GGNClient
from matcher import is_strong_match
from config import TITLE_PREFIX_WORDS

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('verify_and_update.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def init_master_db(master_db_path: str) -> sqlite3.Connection:
    """
    Initialize master database with schema if it doesn't exist.

    Args:
        master_db_path: Path to master database

    Returns:
        Database connection
    """
    conn = sqlite3.connect(master_db_path)
    cursor = conn.cursor()

    # Create master_books table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS master_books (
            -- MAM fields
            id INTEGER,
            detail_url TEXT UNIQUE NOT NULL,
            title TEXT,
            author TEXT,
            co_author TEXT,
            series_name TEXT,
            series_id INTEGER,
            size TEXT,
            tags TEXT,
            files_number INTEGER,
            filetypes TEXT,
            added_time TEXT,
            description_html TEXT,
            cover_image_url TEXT,
            torrent_url TEXT,
            search_label TEXT,
            search_position INTEGER,
            search_url TEXT,
            scraped_at TEXT,

            -- GGn verification fields
            ggn_match_status TEXT,
            ggn_group_id TEXT,
            ggn_group_name TEXT,
            ggn_formats TEXT,
            ggn_seeders_total INTEGER,
            ggn_snatched_total INTEGER,
            ggn_verified_at TEXT,

            PRIMARY KEY (detail_url)
        )
    """)

    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ggn_status ON master_books(ggn_match_status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_series ON master_books(series_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_title ON master_books(title)")

    conn.commit()
    logger.info(f"Master database initialized: {master_db_path}")

    return conn


def get_books_to_verify(mam_db_path: str, master_db_path: str, force_reverify: bool = False) -> List[Dict[str, Any]]:
    """
    Get books from MAM that need GGn verification.

    Args:
        mam_db_path: Path to MAM database
        master_db_path: Path to master database
        force_reverify: If True, reverify all books (default: False)

    Returns:
        List of book dictionaries to verify
    """
    mam_conn = sqlite3.connect(mam_db_path)
    master_conn = sqlite3.connect(master_db_path)

    # Check if master_books table exists and has rows
    cursor = master_conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM master_books")
        master_count = cursor.fetchone()[0]
    except sqlite3.OperationalError:
        master_count = 0

    if force_reverify or master_count == 0:
        # Get all books from MAM
        if force_reverify:
            logger.info("Force reverify enabled - checking all books")
        else:
            logger.info("First run - verifying all books from MAM database")
        books_df = pd.read_sql_query("SELECT * FROM mam_torrents", mam_conn)
    else:
        # Get books already verified in master
        logger.info("Getting unverified books from MAM database")
        master_urls_df = pd.read_sql_query("SELECT detail_url FROM master_books", master_conn)
        master_urls = set(master_urls_df['detail_url'].tolist())

        # Get all MAM books
        all_books_df = pd.read_sql_query("SELECT * FROM mam_torrents", mam_conn)

        # Filter to only books not in master
        books_df = all_books_df[~all_books_df['detail_url'].isin(master_urls)]

    mam_conn.close()
    master_conn.close()

    logger.info(f"Found {len(books_df)} books to verify")

    return books_df.to_dict('records')


def verify_book(client: GGNClient, title: str, author: str, title_prefix_words: int) -> Dict[str, Any]:
    """
    Verify a single book against GGn.

    Args:
        client: GGn API client
        title: Book title
        author: Book author
        title_prefix_words: Number of title words to use for matching

    Returns:
        Dictionary with verification results
    """
    # Search GGn
    groups = client.search_ebook(title)

    if groups is None:
        return {
            'ggn_match_status': 'error',
            'ggn_group_id': None,
            'ggn_group_name': None,
            'ggn_formats': None,
            'ggn_seeders_total': None,
            'ggn_snatched_total': None,
        }

    # Find strong matches
    strong_matches = []
    for group in groups:
        if is_strong_match(title, author, group, title_prefix_words):
            details = client.get_group_details(group)
            strong_matches.append(details)

    # Determine match status
    if len(strong_matches) == 0:
        return {
            'ggn_match_status': 'no_match',
            'ggn_group_id': None,
            'ggn_group_name': None,
            'ggn_formats': None,
            'ggn_seeders_total': None,
            'ggn_snatched_total': None,
        }

    elif len(strong_matches) == 1:
        match = strong_matches[0]
        return {
            'ggn_match_status': 'match',
            'ggn_group_id': str(match.get('group_id', '')),
            'ggn_group_name': match.get('group_name', ''),
            'ggn_formats': match.get('formats', ''),
            'ggn_seeders_total': match.get('seeders_total', 0),
            'ggn_snatched_total': match.get('snatched_total', 0),
        }

    else:
        # Ambiguous - multiple matches
        group_ids = ';'.join(str(m.get('group_id', '')) for m in strong_matches)
        all_formats = set()
        total_seeders = 0
        total_snatched = 0

        for match in strong_matches:
            formats = match.get('formats', '')
            if formats:
                # Handle formats whether it's a string or list
                if isinstance(formats, list):
                    all_formats.update(formats)
                else:
                    all_formats.update(formats.split(';'))
            total_seeders += match.get('seeders_total', 0)
            total_snatched += match.get('snatched_total', 0)

        return {
            'ggn_match_status': 'ambiguous',
            'ggn_group_id': group_ids,
            'ggn_group_name': strong_matches[0].get('group_name', ''),
            'ggn_formats': ';'.join(sorted(all_formats)) if all_formats else '',
            'ggn_seeders_total': total_seeders,
            'ggn_snatched_total': total_snatched,
        }


def update_master_db(master_conn: sqlite3.Connection, book: Dict[str, Any], ggn_result: Dict[str, Any]) -> None:
    """
    Update master database with book and verification results.

    Args:
        master_conn: Master database connection
        book: Book data from MAM
        ggn_result: GGn verification results
    """
    from datetime import datetime

    cursor = master_conn.cursor()

    # Merge book data with GGn results
    data = {
        **book,
        **ggn_result,
        'ggn_verified_at': datetime.now().isoformat()
    }

    # Convert any list/array types to comma-separated strings (SQLite doesn't support lists)
    for key, value in data.items():
        if isinstance(value, list):
            data[key] = ', '.join(str(v) for v in value) if value else ''

    # Insert or replace
    cursor.execute("""
        INSERT OR REPLACE INTO master_books (
            id, detail_url, title, author, co_author, series_name, series_id,
            size, tags, files_number, filetypes, added_time, description_html,
            cover_image_url, torrent_url, search_label, search_position,
            search_url, scraped_at,
            ggn_match_status, ggn_group_id, ggn_group_name, ggn_formats,
            ggn_seeders_total, ggn_snatched_total, ggn_verified_at
        ) VALUES (
            :id, :detail_url, :title, :author, :co_author, :series_name, :series_id,
            :size, :tags, :files_number, :filetypes, :added_time, :description_html,
            :cover_image_url, :torrent_url, :search_label, :search_position,
            :search_url, :scraped_at,
            :ggn_match_status, :ggn_group_id, :ggn_group_name, :ggn_formats,
            :ggn_seeders_total, :ggn_snatched_total, :ggn_verified_at
        )
    """, data)

    master_conn.commit()


def main():
    parser = argparse.ArgumentParser(
        description='Verify MAM books against GGn and update master database'
    )
    parser.add_argument(
        '--mam-db',
        default='../mam_scraper/mam.db',
        help='Path to MAM database (default: ../mam_scraper/mam.db)'
    )
    parser.add_argument(
        '--master-db',
        default='master_books.db',
        help='Path to master database (default: master_books.db)'
    )
    parser.add_argument(
        '--title-words',
        type=int,
        default=TITLE_PREFIX_WORDS,
        help=f'Number of title words to use for matching (default: {TITLE_PREFIX_WORDS})'
    )
    parser.add_argument(
        '--force-reverify',
        action='store_true',
        help='Force reverification of all books (default: only verify new/unverified)'
    )
    parser.add_argument(
        '--max-books',
        type=int,
        help='Maximum number of books to verify in this run (for testing)'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )

    args = parser.parse_args()

    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    logger.info("="*70)
    logger.info("MAM → GGn Verification with Master DB Update")
    logger.info("="*70)
    logger.info(f"MAM database: {args.mam_db}")
    logger.info(f"Master database: {args.master_db}")
    logger.info(f"Title prefix words: {args.title_words}")
    logger.info(f"Force reverify: {args.force_reverify}")

    # Check MAM database exists
    if not Path(args.mam_db).exists():
        logger.error(f"MAM database not found: {args.mam_db}")
        sys.exit(1)

    # Initialize master database
    master_conn = init_master_db(args.master_db)

    # Get books to verify
    books = get_books_to_verify(args.mam_db, args.master_db, args.force_reverify)

    if not books:
        logger.info("No books to verify. All books are up to date!")
        master_conn.close()
        return

    # Limit books if specified
    if args.max_books:
        books = books[:args.max_books]
        logger.info(f"Limited to {args.max_books} books for this run")

    # Initialize GGn client
    logger.info("Initializing GGn API client")
    client = GGNClient()

    # Process books
    logger.info(f"Starting verification of {len(books)} books...")
    logger.info("")

    stats = {
        'match': 0,
        'no_match': 0,
        'ambiguous': 0,
        'error': 0
    }

    for i, book in enumerate(books, 1):
        title = book.get('title', '')
        author = book.get('author', '')

        # Handle NaN values
        if pd.isna(title):
            title = ''
        if pd.isna(author):
            author = ''

        logger.info(f"[{i}/{len(books)}] Verifying: {title}")

        # Verify against GGn
        ggn_result = verify_book(client, title, author, args.title_words)

        # Update master database
        update_master_db(master_conn, book, ggn_result)

        # Update stats
        status = ggn_result['ggn_match_status']
        stats[status] += 1

        # Log result
        if status == 'match':
            logger.info(f"  ✓ MATCH: {ggn_result['ggn_group_name']}")
        elif status == 'no_match':
            logger.info(f"  ✗ NO MATCH (upload candidate)")
        elif status == 'ambiguous':
            logger.info(f"  ~ AMBIGUOUS: {ggn_result['ggn_group_id']}")
        else:
            logger.info(f"  ! ERROR during verification")

        # Progress update every 25 books
        if i % 25 == 0:
            logger.info(f"Progress: {i}/{len(books)} books ({i*100//len(books)}%)")
            logger.info(f"  Matches: {stats['match']}, No match: {stats['no_match']}, Ambiguous: {stats['ambiguous']}, Errors: {stats['error']}")
            logger.info("")

    master_conn.close()

    # Final statistics
    logger.info("")
    logger.info("="*70)
    logger.info("VERIFICATION COMPLETE")
    logger.info("="*70)
    logger.info(f"Total books verified:     {len(books)}")
    logger.info(f"  Match:                  {stats['match']} ({stats['match']*100//len(books)}%)")
    logger.info(f"  No match:               {stats['no_match']} ({stats['no_match']*100//len(books)}%)")
    logger.info(f"  Ambiguous:              {stats['ambiguous']} ({stats['ambiguous']*100//len(books)}%)")
    logger.info(f"  Errors:                 {stats['error']} ({stats['error']*100//len(books)}%)")
    logger.info("")
    logger.info(f"Master database updated: {args.master_db}")
    logger.info("="*70)
    logger.info("")
    logger.info("Query upload candidates:")
    logger.info(f"  sqlite3 {args.master_db} \"SELECT title, author FROM master_books WHERE ggn_match_status = 'no_match'\"")


if __name__ == '__main__':
    main()
