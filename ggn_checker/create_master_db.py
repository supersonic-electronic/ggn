#!/usr/bin/env python3
"""
Create master database combining MAM torrents with GGn verification status.
"""
import sqlite3
import pandas as pd
import sys
from pathlib import Path

# Paths
MAM_DB = "../mam_scraper/mam.db"
GGN_RESULTS = "output_books_ggn.csv"
MASTER_DB = "master_books.db"

def create_master_db():
    """Create master database with MAM + GGn data."""
    
    print("=" * 70)
    print("CREATING MASTER BOOKS DATABASE")
    print("=" * 70)
    print()
    
    # Check if MAM DB exists
    if not Path(MAM_DB).exists():
        print(f"Error: MAM database not found at {MAM_DB}")
        sys.exit(1)
    
    # Check if GGn results exist
    if not Path(GGN_RESULTS).exists():
        print(f"Error: GGn verification results not found at {GGN_RESULTS}")
        sys.exit(1)
    
    # Connect to MAM database and read all torrents
    print(f"Reading MAM database: {MAM_DB}")
    mam_conn = sqlite3.connect(MAM_DB)
    
    # Get MAM torrents as DataFrame
    mam_df = pd.read_sql_query("""
        SELECT 
            detail_url,
            title,
            author,
            co_author,
            size,
            tags,
            files_number,
            filetypes,
            added_time,
            description_html,
            cover_image_url,
            torrent_url,
            search_label,
            search_position,
            search_url,
            scraped_at
        FROM mam_torrents
        ORDER BY title, author
    """, mam_conn)
    
    mam_conn.close()
    print(f"  Loaded {len(mam_df)} torrents from MAM")
    print()
    
    # Read GGn verification results
    print(f"Reading GGn verification results: {GGN_RESULTS}")
    ggn_df = pd.read_csv(GGN_RESULTS)
    print(f"  Loaded {len(ggn_df)} verification results")
    print()
    
    # Merge MAM and GGn data
    print("Merging MAM and GGn data...")
    master_df = mam_df.merge(
        ggn_df,
        on=['title', 'author'],
        how='left'
    )
    
    # Fill NaN for books not in GGn results
    master_df['ggn_match_status'] = master_df['ggn_match_status'].fillna('not_checked')
    
    print(f"  Total records: {len(master_df)}")
    print()
    
    # Create master database
    print(f"Creating master database: {MASTER_DB}")
    if Path(MASTER_DB).exists():
        Path(MASTER_DB).unlink()
    
    master_conn = sqlite3.connect(MASTER_DB)
    
    # Write to database
    master_df.to_sql('master_books', master_conn, index=False, if_exists='replace')
    
    # Create indexes for faster queries
    print("Creating indexes...")
    master_conn.execute("CREATE INDEX idx_ggn_status ON master_books(ggn_match_status)")
    master_conn.execute("CREATE INDEX idx_title ON master_books(title)")
    master_conn.execute("CREATE INDEX idx_author ON master_books(author)")
    master_conn.execute("CREATE INDEX idx_search_label ON master_books(search_label)")
    
    master_conn.commit()
    
    # Statistics
    print()
    print("=" * 70)
    print("STATISTICS")
    print("=" * 70)
    print()
    
    cursor = master_conn.cursor()
    
    # Overall stats
    cursor.execute("SELECT COUNT(*) FROM master_books")
    total = cursor.fetchone()[0]
    print(f"Total books in master database: {total}")
    print()
    
    # GGn status breakdown
    print("GGn Verification Status:")
    cursor.execute("""
        SELECT 
            ggn_match_status,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM master_books), 1) as percentage
        FROM master_books
        GROUP BY ggn_match_status
        ORDER BY count DESC
    """)
    
    for status, count, pct in cursor.fetchall():
        print(f"  {status:15s}: {count:4d} ({pct:5.1f}%)")
    
    print()
    
    # Upload candidates (books on MAM but not on GGn)
    cursor.execute("""
        SELECT COUNT(*) 
        FROM master_books 
        WHERE ggn_match_status = 'no_match'
    """)
    upload_candidates = cursor.fetchone()[0]
    print(f"Upload candidates (no_match): {upload_candidates}")
    
    # Confirmed on both trackers
    cursor.execute("""
        SELECT COUNT(*) 
        FROM master_books 
        WHERE ggn_match_status = 'match'
    """)
    confirmed = cursor.fetchone()[0]
    print(f"Confirmed on both trackers: {confirmed}")
    
    # Ambiguous cases
    cursor.execute("""
        SELECT COUNT(*) 
        FROM master_books 
        WHERE ggn_match_status = 'ambiguous'
    """)
    ambiguous = cursor.fetchone()[0]
    print(f"Ambiguous (need review): {ambiguous}")
    
    print()
    
    # Top formats for upload candidates
    print("Upload candidates by format:")
    cursor.execute("""
        SELECT 
            filetypes,
            COUNT(*) as count
        FROM master_books
        WHERE ggn_match_status = 'no_match'
        GROUP BY filetypes
        ORDER BY count DESC
        LIMIT 10
    """)
    
    for filetype, count in cursor.fetchall():
        filetype_str = filetype if filetype else "(unknown)"
        print(f"  {filetype_str:20s}: {count:4d}")
    
    print()
    
    # Sample queries
    print("=" * 70)
    print("USEFUL QUERIES")
    print("=" * 70)
    print()
    print("-- Get all upload candidates:")
    print("SELECT title, author, size, filetypes FROM master_books")
    print("WHERE ggn_match_status = 'no_match'")
    print("ORDER BY title;")
    print()
    print("-- Get all confirmed matches with GGn details:")
    print("SELECT title, author, ggn_group_name, ggn_formats FROM master_books")
    print("WHERE ggn_match_status = 'match'")
    print("ORDER BY title;")
    print()
    print("-- Get ambiguous cases:")
    print("SELECT title, author, ggn_group_id, ggn_group_name FROM master_books")
    print("WHERE ggn_match_status = 'ambiguous'")
    print("ORDER BY title;")
    print()
    print("-- Get upload candidates for specific format (e.g., epub):")
    print("SELECT title, author, size, detail_url FROM master_books")
    print("WHERE ggn_match_status = 'no_match' AND filetypes LIKE '%epub%'")
    print("ORDER BY title;")
    print()
    
    master_conn.close()
    
    print("=" * 70)
    print(f"Master database created: {MASTER_DB}")
    print("=" * 70)

if __name__ == "__main__":
    create_master_db()
