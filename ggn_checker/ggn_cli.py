#!/usr/bin/env python3
"""
GGn Checker CLI - Command-line interface for MAM to GGn verification

Commands:
  check     - Run verification against GGn API
  list      - List upload candidates
  export    - Export results to CSV
  stats     - Show verification statistics
  series    - Show series information
"""

import argparse
import sqlite3
import csv
import sys
from pathlib import Path
from datetime import datetime
import subprocess


def get_db_connection(db_path='master_books.db'):
    """Get database connection."""
    if not Path(db_path).exists():
        print(f"Error: Master database not found at {db_path}")
        print("Run 'ggn_cli.py check' first to create the database")
        sys.exit(1)
    return sqlite3.connect(db_path)


def cmd_check(args):
    """Run verification against GGn API."""
    print("="*70)
    print("Starting GGn Verification")
    print("="*70)

    # Build command
    cmd = ['python3', 'verify_and_update.py']

    if args.mam_db:
        cmd.extend(['--mam-db', args.mam_db])
    if args.master_db:
        cmd.extend(['--master-db', args.master_db])
    if args.max_books:
        cmd.extend(['--max-books', str(args.max_books)])
    if args.force_reverify:
        cmd.append('--force-reverify')
    if args.log_level:
        cmd.extend(['--log-level', args.log_level])

    # Run verification
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\nError: Verification failed with exit code {e.returncode}")
        sys.exit(1)
    except FileNotFoundError:
        print("\nError: verify_and_update.py not found")
        sys.exit(1)


def cmd_list(args):
    """List upload candidates."""
    conn = get_db_connection(args.db)
    cursor = conn.cursor()

    # Build query
    query = """
        SELECT title, author, filetypes, size, series_name, tags
        FROM master_books
        WHERE ggn_match_status = 'no_match'
    """

    # Add filters
    filters = []
    params = []

    if args.series:
        filters.append("series_name = ?")
        params.append(args.series)

    if args.format:
        filters.append("filetypes LIKE ?")
        params.append(f"%{args.format}%")

    if args.search:
        filters.append("(title LIKE ? OR author LIKE ?)")
        params.extend([f"%{args.search}%", f"%{args.search}%"])

    if filters:
        query += " AND " + " AND ".join(filters)

    query += " ORDER BY series_name, title"

    if args.limit:
        query += f" LIMIT {args.limit}"

    # Execute query
    cursor.execute(query, params)
    results = cursor.fetchall()

    if not results:
        print("No upload candidates found matching your criteria.")
        conn.close()
        return

    # Display results
    print(f"\n{'='*100}")
    print(f"Upload Candidates: {len(results)} books")
    print(f"{'='*100}\n")

    for i, (title, author, filetypes, size, series_name, tags) in enumerate(results, 1):
        print(f"{i}. {title}")
        print(f"   Author: {author}")
        print(f"   Formats: {filetypes} ({size})")
        if series_name:
            print(f"   Series: {series_name}")
        if args.show_tags and tags:
            print(f"   Tags: {tags}")
        print()

    conn.close()


def cmd_export(args):
    """Export results to CSV."""
    conn = get_db_connection(args.db)
    cursor = conn.cursor()

    # Determine what to export
    if args.type == 'candidates':
        query = """
            SELECT title, author, filetypes, size, series_name, tags,
                   detail_url, torrent_url
            FROM master_books
            WHERE ggn_match_status = 'no_match'
            ORDER BY series_name, title
        """
        default_filename = f"upload_candidates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    elif args.type == 'matches':
        query = """
            SELECT title, author, ggn_group_name, ggn_formats,
                   ggn_seeders_total, ggn_snatched_total
            FROM master_books
            WHERE ggn_match_status = 'match'
            ORDER BY title
        """
        default_filename = f"ggn_matches_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    elif args.type == 'ambiguous':
        query = """
            SELECT title, author, ggn_group_id, ggn_group_name
            FROM master_books
            WHERE ggn_match_status = 'ambiguous'
            ORDER BY title
        """
        default_filename = f"ambiguous_matches_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    else:  # all
        query = """
            SELECT title, author, filetypes, size, series_name,
                   ggn_match_status, ggn_group_name, ggn_formats
            FROM master_books
            ORDER BY ggn_match_status, series_name, title
        """
        default_filename = f"all_books_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    # Execute query
    cursor.execute(query)
    results = cursor.fetchall()

    if not results:
        print(f"No results found for export type: {args.type}")
        conn.close()
        return

    # Get column names
    column_names = [description[0] for description in cursor.description]

    # Determine output file
    output_file = args.output or default_filename

    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(column_names)
        writer.writerows(results)

    print(f"\n✓ Exported {len(results)} rows to: {output_file}")

    conn.close()


def cmd_stats(args):
    """Show verification statistics."""
    conn = get_db_connection(args.db)
    cursor = conn.cursor()

    # Overall stats
    cursor.execute("SELECT COUNT(*) FROM master_books")
    total = cursor.fetchone()[0]

    cursor.execute("""
        SELECT ggn_match_status, COUNT(*) as count
        FROM master_books
        GROUP BY ggn_match_status
    """)
    status_counts = dict(cursor.fetchall())

    # Display overall stats
    print("\n" + "="*70)
    print("GGn Verification Statistics")
    print("="*70)
    print(f"\nTotal books in database: {total}")
    print(f"\nBreakdown by status:")

    for status in ['match', 'no_match', 'ambiguous', 'error']:
        count = status_counts.get(status, 0)
        percentage = (count / total * 100) if total > 0 else 0

        if status == 'match':
            label = "Already on GGn"
            icon = "✓"
        elif status == 'no_match':
            label = "Upload candidates"
            icon = "⬆"
        elif status == 'ambiguous':
            label = "Need manual review"
            icon = "~"
        else:
            label = "Errors"
            icon = "✗"

        print(f"  {icon} {label:20s}: {count:5d} ({percentage:5.1f}%)")

    # Series stats if requested
    if args.series_stats:
        print(f"\n{'='*70}")
        print("Series Statistics (with upload candidates)")
        print("="*70)

        cursor.execute("""
            SELECT series_name,
                   COUNT(*) as total,
                   SUM(CASE WHEN ggn_match_status = 'no_match' THEN 1 ELSE 0 END) as candidates
            FROM master_books
            WHERE series_name IS NOT NULL AND series_name != ''
            GROUP BY series_name
            HAVING candidates > 0
            ORDER BY total DESC
            LIMIT 20
        """)

        series_results = cursor.fetchall()

        if series_results:
            print(f"\n{'Series Name':<40s} {'Total':<8s} {'Candidates':<12s}")
            print("-" * 70)
            for series, total, candidates in series_results:
                print(f"{series:<40s} {total:<8d} {candidates:<12d}")
        else:
            print("\nNo series with upload candidates found.")

    # Format stats if requested
    if args.format_stats:
        print(f"\n{'='*70}")
        print("Format Statistics (upload candidates only)")
        print("="*70)

        cursor.execute("""
            SELECT filetypes, COUNT(*) as count
            FROM master_books
            WHERE ggn_match_status = 'no_match'
            GROUP BY filetypes
            ORDER BY count DESC
            LIMIT 15
        """)

        format_results = cursor.fetchall()

        if format_results:
            print(f"\n{'Format(s)':<30s} {'Count':<10s}")
            print("-" * 70)
            for fmt, count in format_results:
                print(f"{fmt:<30s} {count:<10d}")

    print("\n" + "="*70 + "\n")

    conn.close()


def cmd_series(args):
    """Show series information."""
    conn = get_db_connection(args.db)
    cursor = conn.cursor()

    if args.name:
        # Show specific series
        cursor.execute("""
            SELECT title, author, ggn_match_status, filetypes, size
            FROM master_books
            WHERE series_name = ?
            ORDER BY title
        """, (args.name,))

        results = cursor.fetchall()

        if not results:
            print(f"\nNo books found for series: {args.name}")
            conn.close()
            return

        print(f"\n{'='*100}")
        print(f"Series: {args.name}")
        print(f"Total books: {len(results)}")
        print(f"{'='*100}\n")

        for i, (title, author, status, filetypes, size) in enumerate(results, 1):
            status_icon = "✓" if status == "match" else "⬆" if status == "no_match" else "~"
            status_label = "on GGn" if status == "match" else "CANDIDATE" if status == "no_match" else "AMBIGUOUS"

            print(f"{i}. {title}")
            print(f"   Author: {author}")
            print(f"   Status: {status_icon} {status_label}")
            print(f"   Formats: {filetypes} ({size})")
            print()

    else:
        # List all series with candidates
        cursor.execute("""
            SELECT series_name,
                   COUNT(*) as total,
                   SUM(CASE WHEN ggn_match_status = 'no_match' THEN 1 ELSE 0 END) as candidates,
                   SUM(CASE WHEN ggn_match_status = 'match' THEN 1 ELSE 0 END) as on_ggn
            FROM master_books
            WHERE series_name IS NOT NULL AND series_name != ''
            GROUP BY series_name
            HAVING candidates > 0
            ORDER BY total DESC
        """)

        results = cursor.fetchall()

        if not results:
            print("\nNo series with upload candidates found.")
            conn.close()
            return

        print(f"\n{'='*100}")
        print(f"Series with Upload Candidates: {len(results)}")
        print(f"{'='*100}\n")
        print(f"{'Series Name':<50s} {'Total':<8s} {'Candidates':<12s} {'On GGn':<10s}")
        print("-" * 100)

        for series, total, candidates, on_ggn in results:
            print(f"{series:<50s} {total:<8d} {candidates:<12d} {on_ggn:<10d}")

        print(f"\nUse 'ggn_cli.py series --name \"SERIES_NAME\"' to see details")

    print()
    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='GGn Checker CLI - MAM to GGn verification tool',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # CHECK command
    check_parser = subparsers.add_parser('check', help='Run verification against GGn API')
    check_parser.add_argument('--mam-db', help='Path to MAM database')
    check_parser.add_argument('--master-db', help='Path to master database')
    check_parser.add_argument('--max-books', type=int, help='Maximum books to verify')
    check_parser.add_argument('--force-reverify', action='store_true', help='Re-verify all books')
    check_parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                            help='Logging level')

    # LIST command
    list_parser = subparsers.add_parser('list', help='List upload candidates')
    list_parser.add_argument('--db', default='master_books.db', help='Master database path')
    list_parser.add_argument('--series', help='Filter by series name')
    list_parser.add_argument('--format', help='Filter by file format (e.g., epub, pdf)')
    list_parser.add_argument('--search', help='Search in title or author')
    list_parser.add_argument('--limit', type=int, help='Limit number of results')
    list_parser.add_argument('--show-tags', action='store_true', help='Show tags')

    # EXPORT command
    export_parser = subparsers.add_parser('export', help='Export results to CSV')
    export_parser.add_argument('--db', default='master_books.db', help='Master database path')
    export_parser.add_argument('--type', choices=['candidates', 'matches', 'ambiguous', 'all'],
                              default='candidates', help='What to export')
    export_parser.add_argument('--output', '-o', help='Output CSV file')

    # STATS command
    stats_parser = subparsers.add_parser('stats', help='Show verification statistics')
    stats_parser.add_argument('--db', default='master_books.db', help='Master database path')
    stats_parser.add_argument('--series-stats', action='store_true',
                            help='Show series statistics')
    stats_parser.add_argument('--format-stats', action='store_true',
                            help='Show format statistics')

    # SERIES command
    series_parser = subparsers.add_parser('series', help='Show series information')
    series_parser.add_argument('--db', default='master_books.db', help='Master database path')
    series_parser.add_argument('--name', help='Show specific series details')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    if args.command == 'check':
        cmd_check(args)
    elif args.command == 'list':
        cmd_list(args)
    elif args.command == 'export':
        cmd_export(args)
    elif args.command == 'stats':
        cmd_stats(args)
    elif args.command == 'series':
        cmd_series(args)


if __name__ == '__main__':
    main()
