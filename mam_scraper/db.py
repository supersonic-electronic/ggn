"""
Database operations for storing MyAnonamouse torrent metadata.
Uses SQLite for local storage with deduplication via unique detail_url.
"""
import sqlite3
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from utils import format_timestamp

logger = logging.getLogger(__name__)


def init_db(db_path: str = "mam.db") -> sqlite3.Connection:
    """
    Initialize the database and create tables if they don't exist.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        SQLite connection object
    """
    logger.info(f"Initializing database at: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create the main torrents table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mam_torrents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            scraped_at TEXT NOT NULL,
            UNIQUE(detail_url)
        )
    """)

    # Migration: Add co_author column if it doesn't exist (for existing databases)
    try:
        cursor.execute("SELECT co_author FROM mam_torrents LIMIT 1")
    except sqlite3.OperationalError:
        logger.info("Adding co_author column to existing database")
        cursor.execute("ALTER TABLE mam_torrents ADD COLUMN co_author TEXT")
        conn.commit()

    # Migration: Add series_name and series_id columns if they don't exist
    try:
        cursor.execute("SELECT series_name FROM mam_torrents LIMIT 1")
    except sqlite3.OperationalError:
        logger.info("Adding series_name and series_id columns to existing database")
        cursor.execute("ALTER TABLE mam_torrents ADD COLUMN series_name TEXT")
        cursor.execute("ALTER TABLE mam_torrents ADD COLUMN series_id INTEGER")
        conn.commit()

    # Create index on detail_url for faster lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_detail_url
        ON mam_torrents(detail_url)
    """)

    # Create index on search_label for filtering
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_search_label
        ON mam_torrents(search_label)
    """)

    # Create index on scraped_at for date filtering
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_scraped_at
        ON mam_torrents(scraped_at)
    """)

    conn.commit()
    logger.info("Database initialized successfully")

    return conn


def save_to_db(conn: sqlite3.Connection, record: Dict[str, Any]) -> bool:
    """
    Save a torrent record to the database.
    Uses INSERT OR REPLACE to handle duplicates based on detail_url.

    Args:
        conn: SQLite connection object
        record: Dictionary containing torrent metadata

    Returns:
        True if saved successfully, False otherwise
    """
    cursor = conn.cursor()

    # Add timestamp if not present
    if "scraped_at" not in record:
        record["scraped_at"] = format_timestamp()

    try:
        cursor.execute("""
            INSERT OR REPLACE INTO mam_torrents (
                detail_url, title, author, co_author, series_name, series_id, size, tags, files_number,
                filetypes, added_time, description_html, cover_image_url,
                torrent_url, search_label, search_position, search_url, scraped_at
            ) VALUES (
                :detail_url, :title, :author, :co_author, :series_name, :series_id, :size, :tags, :files_number,
                :filetypes, :added_time, :description_html, :cover_image_url,
                :torrent_url, :search_label, :search_position, :search_url, :scraped_at
            )
        """, record)

        conn.commit()
        logger.debug(f"Saved torrent: {record.get('title', 'Unknown')}")
        return True

    except sqlite3.Error as e:
        logger.error(f"Database error while saving record: {e}")
        logger.error(f"Record: {record.get('detail_url', 'Unknown URL')}")
        return False


def get_torrent_by_url(conn: sqlite3.Connection, detail_url: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a torrent record by its detail URL.

    Args:
        conn: SQLite connection object
        detail_url: The detail page URL to look up

    Returns:
        Dictionary containing the torrent record, or None if not found
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM mam_torrents WHERE detail_url = ?
    """, (detail_url,))

    row = cursor.fetchone()
    if row:
        columns = [description[0] for description in cursor.description]
        return dict(zip(columns, row))

    return None


def get_all_torrents(conn: sqlite3.Connection,
                     search_label: Optional[str] = None,
                     limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Retrieve all torrent records, optionally filtered by search label.

    Args:
        conn: SQLite connection object
        search_label: Optional filter by search label
        limit: Optional limit on number of results

    Returns:
        List of dictionaries containing torrent records
    """
    cursor = conn.cursor()

    query = "SELECT * FROM mam_torrents"
    params = []

    if search_label:
        query += " WHERE search_label = ?"
        params.append(search_label)

    query += " ORDER BY scraped_at DESC"

    if limit:
        query += " LIMIT ?"
        params.append(limit)

    cursor.execute(query, params)

    columns = [description[0] for description in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_stats(conn: sqlite3.Connection) -> Dict[str, Any]:
    """
    Get statistics about the database.

    Args:
        conn: SQLite connection object

    Returns:
        Dictionary containing database statistics
    """
    cursor = conn.cursor()

    # Total count
    cursor.execute("SELECT COUNT(*) FROM mam_torrents")
    total = cursor.fetchone()[0]

    # Count by search label
    cursor.execute("""
        SELECT search_label, COUNT(*) as count
        FROM mam_torrents
        GROUP BY search_label
    """)
    by_label = {row[0]: row[1] for row in cursor.fetchall()}

    # Count by filetype
    cursor.execute("""
        SELECT filetypes, COUNT(*) as count
        FROM mam_torrents
        GROUP BY filetypes
    """)
    by_filetype = {row[0]: row[1] for row in cursor.fetchall()}

    # Latest scrape time
    cursor.execute("SELECT MAX(scraped_at) FROM mam_torrents")
    latest_scrape = cursor.fetchone()[0]

    return {
        "total_torrents": total,
        "by_search_label": by_label,
        "by_filetype": by_filetype,
        "latest_scrape": latest_scrape
    }


def url_exists(conn: sqlite3.Connection, detail_url: str) -> bool:
    """
    Check if a detail URL already exists in the database.

    Args:
        conn: SQLite connection object
        detail_url: The detail page URL to check

    Returns:
        True if URL exists, False otherwise
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 1 FROM mam_torrents WHERE detail_url = ? LIMIT 1
    """, (detail_url,))

    return cursor.fetchone() is not None


if __name__ == "__main__":
    # Test database operations
    print("Testing database operations...")

    # Initialize test database
    conn = init_db("test_mam.db")

    # Test record
    test_record = {
        "detail_url": "https://www.myanonamouse.net/t/12345",
        "title": "Test Video Game Book",
        "author": "Test Author",
        "size": "10.5 MiB",
        "tags": "Video Game, Game Design",
        "files_number": 2,
        "filetypes": "epub, pdf",
        "added_time": "2024-01-01 00:00:00",
        "description_html": "<p>Test description</p>",
        "cover_image_url": "https://example.com/cover.jpg",
        "torrent_url": "https://www.myanonamouse.net/tor/download.php?tid=12345",
        "search_label": "Video Game + epub",
        "search_position": 1,
        "search_url": "https://www.myanonamouse.net/tor/browse.php?search=test"
    }

    # Save test record
    print("\nSaving test record...")
    success = save_to_db(conn, test_record)
    print(f"Save successful: {success}")

    # Retrieve record
    print("\nRetrieving test record...")
    retrieved = get_torrent_by_url(conn, test_record["detail_url"])
    if retrieved:
        print(f"Title: {retrieved['title']}")
        print(f"Author: {retrieved['author']}")

    # Check if URL exists
    print("\nChecking if URL exists...")
    exists = url_exists(conn, test_record["detail_url"])
    print(f"URL exists: {exists}")

    # Get stats
    print("\nDatabase statistics:")
    stats = get_stats(conn)
    print(f"Total torrents: {stats['total_torrents']}")
    print(f"By search label: {stats['by_search_label']}")

    # Get all torrents
    print("\nAll torrents:")
    all_torrents = get_all_torrents(conn, limit=5)
    for torrent in all_torrents:
        print(f"  - {torrent['title']}")

    conn.close()
    print("\nDatabase test completed!")

    # Clean up test database
    import os
    if os.path.exists("test_mam.db"):
        os.remove("test_mam.db")
        print("Test database removed.")
