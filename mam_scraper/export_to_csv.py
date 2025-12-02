#!/usr/bin/env python3
"""
Export MyAnonamouse torrent data from SQLite database to CSV format.
Run with: python export_to_csv.py [options]
"""
import csv
import argparse
import sys
from datetime import datetime
from pathlib import Path

import config
from db import init_db, get_all_torrents, get_stats


def export_to_csv(db_path: str, output_file: str, search_label: str = None,
                  limit: int = None):
    """
    Export torrent data from database to CSV file.

    Args:
        db_path: Path to SQLite database
        output_file: Path to output CSV file
        search_label: Optional filter by search label
        limit: Optional limit on number of rows
    """
    print(f"Connecting to database: {db_path}")
    conn = init_db(db_path)

    print("Fetching data from database...")
    torrents = get_all_torrents(conn, search_label=search_label, limit=limit)

    if not torrents:
        print("No data to export!")
        conn.close()
        return

    print(f"Exporting {len(torrents)} torrents to CSV...")

    # Define field order for CSV
    fieldnames = [
        "id",
        "detail_url",
        "title",
        "author",
        "size",
        "tags",
        "files_number",
        "filetypes",
        "added_time",
        "description_html",
        "cover_image_url",
        "torrent_url",
        "search_label",
        "search_position",
        "search_url",
        "scraped_at",
    ]

    # Write to CSV
    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for torrent in torrents:
            # Ensure all fields are present
            row = {field: torrent.get(field, "") for field in fieldnames}
            writer.writerow(row)

    print(f"✓ Export complete: {output_file}")
    print(f"  Rows exported: {len(torrents)}")

    conn.close()


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Export MyAnonamouse torrent data to CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python export_to_csv.py                    # Export all data with timestamped filename
  python export_to_csv.py -o output.csv      # Export to specific file
  python export_to_csv.py --search "Video Game + epub"  # Export only one search
  python export_to_csv.py --limit 100        # Export only first 100 rows
        """
    )

    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Output CSV filename (default: mam_export_YYYYMMDD_HHMM.csv)"
    )

    parser.add_argument(
        "--db",
        type=str,
        default=config.DB_PATH,
        help=f"Path to database file (default: {config.DB_PATH})"
    )

    parser.add_argument(
        "--search",
        "--search-label",
        dest="search_label",
        type=str,
        help="Filter by search label (e.g., 'Video Game + epub')"
    )

    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of rows to export"
    )

    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show database statistics and exit"
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_arguments()

    # Check if database exists
    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Error: Database not found: {args.db}")
        print("Run the crawler first to populate the database.")
        sys.exit(1)

    # Show stats if requested
    if args.stats:
        conn = init_db(args.db)
        stats = get_stats(conn)

        print("\n" + "="*60)
        print("DATABASE STATISTICS")
        print("="*60)
        print(f"Total torrents: {stats['total_torrents']}")
        print(f"\nBy search label:")
        for label, count in sorted(stats['by_search_label'].items()):
            print(f"  {label}: {count}")
        print(f"\nBy filetype:")
        for filetype, count in sorted(stats['by_filetype'].items()):
            print(f"  {filetype}: {count}")
        print(f"\nLatest scrape: {stats['latest_scrape']}")
        print("="*60)

        conn.close()
        sys.exit(0)

    # Generate output filename if not provided
    if args.output:
        output_file = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        output_file = f"mam_export_{timestamp}.csv"

    # Perform export
    try:
        export_to_csv(
            db_path=args.db,
            output_file=output_file,
            search_label=args.search_label,
            limit=args.limit
        )
        sys.exit(0)
    except Exception as e:
        print(f"Error during export: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
