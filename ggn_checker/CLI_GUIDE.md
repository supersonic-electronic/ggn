# GGn Checker CLI Guide

Complete command-line interface for MAM to GGn verification.

## Quick Start

```bash
cd /home/jin23/Code/eBookGGn/ggn_checker
source .venv/bin/activate

# Show all available commands
python3 ggn_cli.py --help

# Show statistics
python3 ggn_cli.py stats
```

## Commands Overview

| Command | Description |
|---------|-------------|
| `check` | Run verification against GGn API |
| `list` | List upload candidates with filtering |
| `export` | Export results to CSV |
| `stats` | Show verification statistics |
| `series` | Show series information |

---

## 1. CHECK - Run Verification

Verify MAM books against GGn API (creates/updates master database).

### Basic Usage

```bash
# Verify all unverified books (recommended)
python3 ggn_cli.py check
```

### Advanced Options

```bash
# Test with first 10 books only
python3 ggn_cli.py check --max-books 10

# Force re-verification of ALL books
python3 ggn_cli.py check --force-reverify

# Use custom databases
python3 ggn_cli.py check \
    --mam-db /path/to/mam.db \
    --master-db /path/to/master.db

# Verbose logging
python3 ggn_cli.py check --log-level INFO
```

### Options

| Option | Description |
|--------|-------------|
| `--mam-db PATH` | Path to MAM database (default: ../mam_scraper/mam.db) |
| `--master-db PATH` | Path to master database (default: master_books.db) |
| `--max-books N` | Limit number of books to verify (for testing) |
| `--force-reverify` | Re-verify all books (not just new ones) |
| `--log-level LEVEL` | Logging level: DEBUG, INFO, WARNING, ERROR |

---

## 2. LIST - List Upload Candidates

Display upload candidates with powerful filtering options.

### Basic Usage

```bash
# List all upload candidates
python3 ggn_cli.py list

# List first 20 candidates
python3 ggn_cli.py list --limit 20
```

### Filter by Series

```bash
# Show only books in The Witcher series
python3 ggn_cli.py list --series "The Witcher"

# Show Resident Evil series
python3 ggn_cli.py list --series "Resident Evil"
```

### Filter by Format

```bash
# Show only EPUB books
python3 ggn_cli.py list --format epub

# Show only PDF books
python3 ggn_cli.py list --format pdf

# Show books with MOBI format
python3 ggn_cli.py list --format mobi
```

### Search

```bash
# Search in title or author
python3 ggn_cli.py list --search "witcher"

# Search with limit
python3 ggn_cli.py list --search "starcraft" --limit 10
```

### Show Tags

```bash
# Display tags for each book
python3 ggn_cli.py list --show-tags --limit 10
```

### Combined Filters

```bash
# EPUB books from The Witcher series
python3 ggn_cli.py list --series "The Witcher" --format epub

# First 5 PDF books matching "game"
python3 ggn_cli.py list --search "game" --format pdf --limit 5
```

### Options

| Option | Description |
|--------|-------------|
| `--db PATH` | Master database path (default: master_books.db) |
| `--series NAME` | Filter by series name |
| `--format FMT` | Filter by file format (epub, pdf, mobi, etc.) |
| `--search TERM` | Search in title or author |
| `--limit N` | Limit number of results |
| `--show-tags` | Display tags for each book |

---

## 3. EXPORT - Export to CSV

Export results to CSV for external analysis or import.

### Export Upload Candidates

```bash
# Export all upload candidates (default)
python3 ggn_cli.py export

# Export to specific file
python3 ggn_cli.py export --output my_candidates.csv
```

### Export Other Types

```bash
# Export books already on GGn
python3 ggn_cli.py export --type matches

# Export ambiguous matches (need manual review)
python3 ggn_cli.py export --type ambiguous

# Export everything
python3 ggn_cli.py export --type all --output complete_database.csv
```

### Output Format

**Candidates CSV includes:**
- title, author, filetypes, size, series_name, tags
- detail_url (MAM link)
- torrent_url (download link)

**Matches CSV includes:**
- title, author, ggn_group_name, ggn_formats
- ggn_seeders_total, ggn_snatched_total

**Ambiguous CSV includes:**
- title, author, ggn_group_id, ggn_group_name

### Options

| Option | Description |
|--------|-------------|
| `--db PATH` | Master database path (default: master_books.db) |
| `--type TYPE` | What to export: candidates, matches, ambiguous, all |
| `--output FILE` | Output CSV filename |

### Auto-Generated Filenames

If no `--output` specified, files are named automatically:
- `upload_candidates_YYYYMMDD_HHMMSS.csv`
- `ggn_matches_YYYYMMDD_HHMMSS.csv`
- `ambiguous_matches_YYYYMMDD_HHMMSS.csv`
- `all_books_YYYYMMDD_HHMMSS.csv`

---

## 4. STATS - Show Statistics

Display verification statistics and breakdowns.

### Basic Statistics

```bash
# Show overall statistics
python3 ggn_cli.py stats
```

**Output:**
```
======================================================================
GGn Verification Statistics
======================================================================

Total books in database: 1974

Breakdown by status:
  ✓ Already on GGn      :   293 ( 14.8%)
  ⬆ Upload candidates   :  1645 ( 83.3%)
  ~ Need manual review  :    36 (  1.8%)
  ✗ Errors              :     0 (  0.0%)

======================================================================
```

### Series Statistics

```bash
# Show series with upload candidates
python3 ggn_cli.py stats --series-stats
```

**Output:**
```
======================================================================
Series Statistics (with upload candidates)
======================================================================

Series Name                              Total    Candidates
----------------------------------------------------------------------
Resident Evil                            10       5
The Witcher                              7        7
Starcraft                                2        2
...
```

### Format Statistics

```bash
# Show format breakdown (upload candidates only)
python3 ggn_cli.py stats --format-stats
```

**Output:**
```
======================================================================
Format Statistics (upload candidates only)
======================================================================

Format(s)                      Count
----------------------------------------------------------------------
epub                           542
epubmobi                       321
pdf                            287
azw3epub                       156
...
```

### All Statistics

```bash
# Show everything
python3 ggn_cli.py stats --series-stats --format-stats
```

### Options

| Option | Description |
|--------|-------------|
| `--db PATH` | Master database path (default: master_books.db) |
| `--series-stats` | Show top 20 series with upload candidates |
| `--format-stats` | Show format breakdown (upload candidates) |

---

## 5. SERIES - Series Information

View detailed information about book series.

### List All Series

```bash
# List all series with upload candidates
python3 ggn_cli.py series
```

**Output:**
```
====================================================================================================
Series with Upload Candidates: 47
====================================================================================================

Series Name                                        Total    Candidates   On GGn
----------------------------------------------------------------------------------------------------
Resident Evil                                      10       5            5
The Witcher                                        7        7            0
Starcraft                                          2        2            0
...
```

### View Specific Series

```bash
# Show all books in The Witcher series
python3 ggn_cli.py series --name "The Witcher"
```

**Output:**
```
====================================================================================================
Series: The Witcher
Total books: 7
====================================================================================================

1. Baptism of Fire
   Author: Andrzej Sapkowski
   Status: ⬆ CANDIDATE
   Formats: epubmobi (1.24 MiB)

2. The Complete Witcher: The Last Wish, Sword of Destiny...
   Author: Andrzej Sapkowski
   Status: ⬆ CANDIDATE
   Formats: epub (2.81 MiB)
...
```

### Options

| Option | Description |
|--------|-------------|
| `--db PATH` | Master database path (default: master_books.db) |
| `--name NAME` | Show specific series details |

---

## Complete Workflow Examples

### 1. Initial Setup and Verification

```bash
cd /home/jin23/Code/eBookGGn/ggn_checker
source .venv/bin/activate

# Run verification (creates master database)
python3 ggn_cli.py check

# Show statistics
python3 ggn_cli.py stats --series-stats
```

### 2. Find Upload Candidates by Series

```bash
# List series with candidates
python3 ggn_cli.py series

# View specific series
python3 ggn_cli.py series --name "The Witcher"

# Export The Witcher books only
python3 ggn_cli.py list --series "The Witcher" > witcher_list.txt
```

### 3. Export Upload Candidates

```bash
# Export all candidates
python3 ggn_cli.py export --output all_candidates.csv

# Export only EPUB candidates
# (need to filter CSV manually or use SQL)
```

### 4. Search and Filter

```bash
# Find all Witcher-related books
python3 ggn_cli.py list --search "witcher" --limit 20

# Find PDF game guides
python3 ggn_cli.py list --search "guide" --format pdf --limit 10

# List first 50 candidates with tags
python3 ggn_cli.py list --show-tags --limit 50
```

### 5. Incremental Updates

```bash
# After scraping new MAM books, just run check again
python3 ggn_cli.py check

# It automatically:
# - Skips already-verified books
# - Only verifies new books
# - Updates master database incrementally
```

---

## Tips and Best Practices

### 1. Use Filters Effectively

Combine filters to narrow down results:
```bash
# EPUB books from specific series
python3 ggn_cli.py list --series "Resident Evil" --format epub

# First 10 search results
python3 ggn_cli.py list --search "minecraft" --limit 10
```

### 2. Export for External Tools

Export to CSV for spreadsheet analysis:
```bash
python3 ggn_cli.py export --output candidates.csv
# Open in Excel, LibreOffice, or Google Sheets
```

### 3. Monitor Series Progress

Check series regularly:
```bash
# See which series have most upload opportunities
python3 ggn_cli.py stats --series-stats

# View specific series details
python3 ggn_cli.py series --name "Halo"
```

### 4. Check Statistics Regularly

After verification:
```bash
# Quick overview
python3 ggn_cli.py stats

# Detailed breakdown
python3 ggn_cli.py stats --series-stats --format-stats
```

---

## Database Location

Default database location: `master_books.db` in the `ggn_checker` directory.

To use a different database:
```bash
python3 ggn_cli.py list --db /path/to/other_master.db
python3 ggn_cli.py stats --db /path/to/other_master.db
```

---

## Error Handling

### Database Not Found

```
Error: Master database not found at master_books.db
Run 'ggn_cli.py check' first to create the database
```

**Solution:** Run verification first:
```bash
python3 ggn_cli.py check
```

### No Results

```
No upload candidates found matching your criteria.
```

**Solution:** Adjust filters or check if books exist:
```bash
# List all without filters
python3 ggn_cli.py list

# Check statistics
python3 ggn_cli.py stats
```

---

## Quick Reference

```bash
# Verification
python3 ggn_cli.py check                              # Verify all unverified books
python3 ggn_cli.py check --max-books 10               # Test with 10 books

# Listing
python3 ggn_cli.py list                               # List all candidates
python3 ggn_cli.py list --limit 20                    # First 20 candidates
python3 ggn_cli.py list --series "The Witcher"        # Specific series
python3 ggn_cli.py list --format epub                 # EPUB only
python3 ggn_cli.py list --search "minecraft"          # Search

# Export
python3 ggn_cli.py export                             # Export candidates
python3 ggn_cli.py export --type matches              # Export matches
python3 ggn_cli.py export --output my_file.csv        # Custom filename

# Statistics
python3 ggn_cli.py stats                              # Basic stats
python3 ggn_cli.py stats --series-stats               # Series breakdown
python3 ggn_cli.py stats --format-stats               # Format breakdown

# Series
python3 ggn_cli.py series                             # List all series
python3 ggn_cli.py series --name "The Witcher"        # Specific series
```

---

## See Also

- `README.md` - Full project documentation
- `QUICKSTART.md` - Streamlined workflow guide
- `USAGE_GUIDE.md` - Complete usage examples
- `MATCHER_IMPROVEMENT_RESULTS.md` - Matcher performance analysis
