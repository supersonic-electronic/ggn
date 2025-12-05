#!/usr/bin/env python3
"""
Process spreadsheet of MAM books and check against GGn API.

Reads a CSV/Excel file with book metadata, searches GGn for each book,
applies matching logic, and outputs results with GGn verification status.
"""
import argparse
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd

import config
from ggn_api import GGNClient
from matcher import is_strong_match, get_title_prefix, get_author_last_name


def setup_logging(log_level: str = "INFO"):
    """Set up logging configuration."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('ggn_checker.log')
        ]
    )


logger = logging.getLogger(__name__)


def process_row(
    row: pd.Series,
    client: GGNClient,
    title_prefix_words: int = 5
) -> Dict:
    """
    Process a single spreadsheet row.

    Args:
        row: Pandas Series with at minimum 'title' and 'author' columns
        client: GGNClient instance
        title_prefix_words: Number of title words to use for matching

    Returns:
        Dict with GGn match results
    """
    # Handle NaN values from pandas
    title_raw = row.get('title', '')
    author_raw = row.get('author', '')

    title = str(title_raw).strip() if pd.notna(title_raw) else ''
    author = str(author_raw).strip() if pd.notna(author_raw) else ''

    if not title:
        logger.warning("Row missing title, skipping")
        return {
            'ggn_match_status': 'no_match',
            'ggn_group_id': None,
            'ggn_group_name': None,
            'ggn_formats': None,
            'ggn_seeders_total': None,
            'ggn_snatched_total': None,
        }

    # Search GGn
    try:
        groups = client.search_ebook(title)
    except Exception as e:
        logger.error(f"Error searching GGn for '{title}': {e}")
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
            'ggn_group_id': match['group_id'],
            'ggn_group_name': match['group_name'],
            'ggn_formats': ';'.join(match['formats']) if match['formats'] else None,
            'ggn_seeders_total': match['seeders'],
            'ggn_snatched_total': match['snatched'],
        }
    else:
        # Multiple matches - ambiguous
        # Aggregate data from all matches
        all_group_ids = [str(m['group_id']) for m in strong_matches]
        all_group_names = [m['group_name'] for m in strong_matches]
        all_formats = set()
        total_seeders = 0
        total_snatched = 0

        for match in strong_matches:
            all_formats.update(match['formats'])
            total_seeders += match['seeders']
            total_snatched += match['snatched']

        return {
            'ggn_match_status': 'ambiguous',
            'ggn_group_id': ';'.join(all_group_ids),
            'ggn_group_name': ' | '.join(all_group_names[:3]),  # Limit to first 3
            'ggn_formats': ';'.join(sorted(all_formats)) if all_formats else None,
            'ggn_seeders_total': total_seeders,
            'ggn_snatched_total': total_snatched,
        }


def process_spreadsheet(
    input_file: str,
    output_file: str,
    title_prefix_words: int = 5,
    max_rows: Optional[int] = None
):
    """
    Process entire spreadsheet.

    Args:
        input_file: Input CSV/Excel file path
        output_file: Output CSV file path
        title_prefix_words: Number of title words for matching
        max_rows: Maximum rows to process (for testing)
    """
    logger.info(f"Reading input file: {input_file}")

    # Read input file
    input_path = Path(input_file)
    if input_path.suffix.lower() == '.csv':
        df = pd.read_csv(input_file)
    elif input_path.suffix.lower() in ['.xlsx', '.xls']:
        df = pd.read_excel(input_file)
    else:
        raise ValueError(f"Unsupported file format: {input_path.suffix}")

    logger.info(f"Loaded {len(df)} rows from input file")

    # Limit rows if specified
    if max_rows:
        df = df.head(max_rows)
        logger.info(f"Limited to {max_rows} rows for processing")

    # Validate required columns
    if 'title' not in df.columns:
        raise ValueError("Input file must have 'title' column")

    # Add author column if missing
    if 'author' not in df.columns:
        logger.warning("'author' column not found, adding empty column")
        df['author'] = ''

    # Initialize GGn client
    logger.info("Initializing GGn API client")
    client = GGNClient()

    # Process each row
    results = []
    progress_interval = config.PROGRESS_INTERVAL

    logger.info("Starting to process rows...")
    print("\n" + "=" * 70)
    print(f"Processing {len(df)} books against GGn API")
    print("=" * 70)

    for idx, row in df.iterrows():
        # Progress reporting
        if (idx + 1) % progress_interval == 0:
            logger.info(f"Processed {idx + 1}/{len(df)} rows...")
            print(f"Progress: {idx + 1}/{len(df)} rows ({100 * (idx + 1) / len(df):.1f}%)")

        # Process row
        ggn_result = process_row(row, client, title_prefix_words)
        results.append(ggn_result)

        # Log matches
        if ggn_result['ggn_match_status'] == 'match':
            logger.info(f"MATCH: '{row.get('title')}' -> {ggn_result['ggn_group_name']}")
        elif ggn_result['ggn_match_status'] == 'ambiguous':
            logger.warning(f"AMBIGUOUS: '{row.get('title')}' ({ggn_result['ggn_group_id']})")

    # Create results dataframe
    results_df = pd.DataFrame(results)

    # Combine with original data
    output_df = pd.concat([df, results_df], axis=1)

    # Write output
    logger.info(f"Writing output to: {output_file}")
    output_df.to_csv(output_file, index=False)

    # Print summary
    print("\n" + "=" * 70)
    print("PROCESSING COMPLETE")
    print("=" * 70)
    print(f"\nResults Summary:")
    print(f"  Total rows processed:     {len(df)}")

    match_counts = results_df['ggn_match_status'].value_counts()
    for status, count in match_counts.items():
        print(f"  {status:20} {count:6} ({100 * count / len(df):.1f}%)")

    print(f"\nOutput written to: {output_file}")
    print(f"Log file: ggn_checker.log")
    print("=" * 70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check MAM books against GGn e-book catalog",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process full spreadsheet
  python process_spreadsheet.py input_books.csv

  # Test with first 10 rows
  python process_spreadsheet.py input_books.csv --max-rows 10

  # Custom output file
  python process_spreadsheet.py input_books.csv -o ggn_results.csv

  # Use first 4 words for title matching
  python process_spreadsheet.py input_books.csv --title-words 4
        """
    )

    parser.add_argument(
        'input_file',
        help='Input CSV or Excel file with book metadata'
    )

    parser.add_argument(
        '-o', '--output',
        default='output_books_ggn.csv',
        help='Output CSV file (default: output_books_ggn.csv)'
    )

    parser.add_argument(
        '--title-words',
        type=int,
        default=5,
        help='Number of title words to use for matching (default: 5)'
    )

    parser.add_argument(
        '--max-rows',
        type=int,
        help='Maximum rows to process (for testing)'
    )

    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)

    # Validate config
    try:
        config.validate_config()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        print(f"\nConfiguration error: {e}")
        print("\nPlease set GGN_API_KEY in .env file")
        return 1

    # Check input file exists
    if not Path(args.input_file).exists():
        logger.error(f"Input file not found: {args.input_file}")
        print(f"\nError: Input file not found: {args.input_file}")
        return 1

    # Process spreadsheet
    try:
        process_spreadsheet(
            input_file=args.input_file,
            output_file=args.output,
            title_prefix_words=args.title_words,
            max_rows=args.max_rows
        )
        return 0

    except KeyboardInterrupt:
        logger.warning("Processing interrupted by user")
        print("\n\nProcessing interrupted by user")
        return 130

    except Exception as e:
        logger.error(f"Error during processing: {e}", exc_info=True)
        print(f"\nError during processing: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
