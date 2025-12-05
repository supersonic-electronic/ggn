# Quick Start Guide - Streamlined Workflow

Simple workflow: MAM database → GGn API → Master database (no CSV exports needed)

## Setup (One Time)

```bash
cd /home/jin23/Code/eBookGGn/ggn_checker
source .venv/bin/activate

# Create .env with your GGn API key
echo "GGN_API_KEY=your_key_here" > .env
```

## Single Command Usage

```bash
# Verify all unverified books and update master DB
python3 verify_and_update.py

# That's it! Master DB is created/updated automatically
```

## What It Does

1. **Reads** directly from MAM database (`../mam_scraper/mam.db`)
2. **Finds** books that haven't been verified against GGn yet
3. **Verifies** each book via GGn API (with improved matcher)
4. **Updates** master database (`master_books.db`) incrementally

## First Run vs. Subsequent Runs

### First Run
- Creates `master_books.db` from scratch
- Verifies ALL books from MAM database
- Takes ~40-60 minutes for 1969 books (rate limited: 5 requests/10s)

### Subsequent Runs
- Only verifies NEW books (not in master DB yet)
- Much faster - only processes unverified books
- Master DB is updated, not recreated

## Query Results

```bash
# Find upload candidates (books NOT on GGn)
sqlite3 master_books.db "
SELECT title, author, filetypes, size
FROM master_books
WHERE ggn_match_status = 'no_match'
ORDER BY title
"

# Find books by series
sqlite3 master_books.db "
SELECT series_name, COUNT(*) as total,
       SUM(CASE WHEN ggn_match_status = 'no_match' THEN 1 ELSE 0 END) as candidates
FROM master_books
WHERE series_name IS NOT NULL
GROUP BY series_name
ORDER BY total DESC
"

# Export upload candidates to CSV
sqlite3 -header -csv master_books.db "
SELECT title, author, filetypes, size, series_name, tags
FROM master_books
WHERE ggn_match_status = 'no_match'
" > upload_candidates.csv
```

## Advanced Options

```bash
# Test with first 10 books only
python3 verify_and_update.py --max-books 10

# Force re-verification of ALL books (not just new ones)
python3 verify_and_update.py --force-reverify

# Use different databases
python3 verify_and_update.py \
    --mam-db /path/to/mam.db \
    --master-db /path/to/master.db

# Verbose logging
python3 verify_and_update.py --log-level DEBUG

# See all options
python3 verify_and_update.py --help
```

## Typical Workflow

### After Scraping New MAM Books

```bash
# 1. Scrape new books into MAM database
cd /home/jin23/Code/eBookGGn/mam_scraper
./run-with-vpn-bypass.sh python3 mam_scraper_cli.py --tags "Video Game" --max-torrents 100

# 2. Verify new books against GGn (automatic incremental update)
cd /home/jin23/Code/eBookGGn/ggn_checker
python3 verify_and_update.py

# 3. Query results
sqlite3 master_books.db "SELECT COUNT(*) FROM master_books WHERE ggn_match_status = 'no_match'"
```

## Output

The script provides real-time progress:
```
[1/1962] Verifying: Video Game Design for Dummies
  ✓ MATCH: Video Game Design For Dummies EPUB
[2/1962] Verifying: StarCraft: Ghost - Spectres
  ✗ NO MATCH (upload candidate)
[3/1962] Verifying: Encyclopedia of Video Games
  ✓ MATCH: Encyclopedia of Video Games: The Culture Technology and Art of Gaming

Progress: 25/1962 books (1%)
  Matches: 8, No match: 15, Ambiguous: 2, Errors: 0
```

## Database Structure

```
master_books table:
├── MAM fields (from mam_torrents)
│   ├── title, author, series_name, series_id
│   ├── size, filetypes, tags
│   └── detail_url, torrent_url, etc.
│
└── GGn verification fields (auto-added)
    ├── ggn_match_status (match/no_match/ambiguous/error)
    ├── ggn_group_id, ggn_group_name
    ├── ggn_formats, ggn_seeders_total
    └── ggn_verified_at (timestamp)
```

## How Incremental Updates Work

The script automatically detects which books need verification:

```sql
-- Books verified and in master DB: SKIP
-- Books not in master DB yet: VERIFY
-- Books in master DB but ggn_match_status IS NULL: VERIFY
```

This means:
- ✅ No duplicate verification
- ✅ Fast subsequent runs
- ✅ Only pays API cost for new books
- ✅ Master DB always up-to-date

## Comparison: Old vs New Workflow

### Old Workflow (3 steps, CSV exports)
```bash
# Step 1: Export MAM to CSV
python3 export_mam_for_verification.py

# Step 2: Verify CSV against GGn
python3 process_spreadsheet.py mam_books.csv

# Step 3: Create master DB from MAM + GGn CSV
python3 create_master_db.py
```

### New Workflow (1 step, direct DB)
```bash
# Single command - does everything
python3 verify_and_update.py
```

## Benefits

✅ **No CSV exports** - Direct database operations
✅ **Incremental updates** - Only verifies new books
✅ **Single command** - Simpler workflow
✅ **Automatic DB creation** - Master DB initialized on first run
✅ **Resumable** - Can stop and restart without losing progress
✅ **Real-time updates** - Master DB updated as verification proceeds

## Troubleshooting

### "No books to verify"
All books in MAM database are already verified. This is normal after the first full run.

### "MAM database not found"
Make sure MAM database exists at `../mam_scraper/mam.db` or specify path with `--mam-db`

### "API key error"
Create `.env` file with your GGn API key:
```bash
echo "GGN_API_KEY=your_key_here" > .env
```

### Want to re-verify everything
```bash
python3 verify_and_update.py --force-reverify
```

## Quick Reference

```bash
# Most common command (verifies new books only)
python3 verify_and_update.py

# Query upload candidates
sqlite3 master_books.db "SELECT title, author FROM master_books WHERE ggn_match_status = 'no_match'"

# Export to CSV
sqlite3 -header -csv master_books.db "SELECT * FROM master_books WHERE ggn_match_status = 'no_match'" > upload.csv

# Check statistics
sqlite3 master_books.db "SELECT ggn_match_status, COUNT(*) FROM master_books GROUP BY ggn_match_status"
```

## See Also

- Full documentation: `README.md`
- Matcher improvements: `MATCHER_IMPROVEMENT_RESULTS.md`
- Series feature: `SERIES_FEATURE_SUMMARY.md`
