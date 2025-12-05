# GGn Checker - MAM to GGn Cross-Reference Tool

Automated tool to check if MyAnonamouse (MAM) eBooks already exist on GazelleGames (GGn), helping identify upload candidates.

## Features

- ✅ Search GGn API for books from MAM database
- ✅ Smart matching algorithm (title + author verification)
- ✅ **NEW:** Checks both group name and Artists field for author matching
- ✅ Rate limiting (5 requests per 10 seconds)
- ✅ Creates master database combining MAM and GGn data
- ✅ Identifies upload candidates automatically
- ✅ Supports series information from MAM scraper

## Quick Start

### 1. Prerequisites

```bash
cd /home/jin23/Code/eBookGGn/ggn_checker
source .venv/bin/activate

# Install dependencies if not already installed
pip install -r requirements.txt
```

### 2. Set Up GGn API Key

Create `.env` file:
```bash
GGN_API_KEY=your_api_key_here
```

Get your API key from: https://gazellegames.net/user.php?action=edit (User Settings → Access Settings → API Key)

### 3. Complete Workflow (From MAM Database to Master DB)

```bash
# Step 1: Export MAM books for verification
python3 export_mam_for_verification.py

# Step 2: Check against GGn (takes ~20 min for 583 books)
python3 process_spreadsheet.py mam_books_for_verification.csv --log-level INFO

# Step 3: Create master database with combined data
python3 create_master_db.py

# Step 4: View upload candidates
sqlite3 master_books.db "
SELECT title, author, filetypes, size
FROM master_books
WHERE ggn_match_status = 'no_match'
LIMIT 10
"
```

## Detailed Usage

### Export MAM Books for Verification

Extract books from MAM database that need GGn verification:

```bash
python3 export_mam_for_verification.py

# Options:
python3 export_mam_for_verification.py \
    --db ../mam_scraper/mam.db \
    --output mam_books.csv
```

**Output:** `mam_books_for_verification.csv` with title and author columns

### Run GGn Verification

Check each book against GGn API:

```bash
python3 process_spreadsheet.py mam_books_for_verification.csv

# With options:
python3 process_spreadsheet.py mam_books_for_verification.csv \
    --log-level INFO \
    --title-words 5
```

**Options:**
- `--log-level`: DEBUG, INFO, WARNING, ERROR (default: WARNING)
- `--title-words`: Number of title words to match (default: 5)
- `--max-rows`: Limit number of rows to process (for testing)
- `-o, --output`: Custom output filename

**Output:** `output_books_ggn.csv` with GGn match status for each book

**Match Status Values:**
- `match` - Single strong match found on GGn (skip upload)
- `no_match` - No matching book found (upload candidate!)
- `ambiguous` - Multiple versions found (manual review needed)
- `error` - API error or network issue

**Processing Time:** ~2 seconds per book (rate limited)
- 583 books ≈ 20 minutes
- Progress updates every 25 books

### Create Master Database

Combine MAM data with GGn verification results:

```bash
python3 create_master_db.py

# With custom paths:
python3 create_master_db.py \
    --mam-db ../mam_scraper/mam.db \
    --ggn-csv output_books_ggn.csv \
    --output master_books.db
```

**Output:** `master_books.db` with combined data from both trackers

**Schema:**
```sql
CREATE TABLE master_books (
    -- MAM fields
    id INTEGER,
    detail_url TEXT,
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

    -- GGn verification fields
    ggn_match_status TEXT,
    ggn_group_id INTEGER,
    ggn_group_name TEXT,
    ggn_formats TEXT,
    ggn_seeders_total INTEGER,
    ggn_snatched_total INTEGER
);
```

## Querying Master Database

### Find Upload Candidates

Books on MAM but not on GGn:

```bash
sqlite3 master_books.db "
SELECT title, author, filetypes, size
FROM master_books
WHERE ggn_match_status = 'no_match'
ORDER BY title
"
```

### Find Confirmed Duplicates

Books on both trackers:

```bash
sqlite3 master_books.db "
SELECT title, author, ggn_group_name
FROM master_books
WHERE ggn_match_status = 'match'
ORDER BY title
"
```

### Export Upload Candidates to CSV

```bash
sqlite3 -header -csv master_books.db "
SELECT title, author, filetypes, size, tags
FROM master_books
WHERE ggn_match_status = 'no_match'
" > upload_candidates.csv
```

### Find Books by Series

```bash
sqlite3 master_books.db "
SELECT series_name, COUNT(*) as book_count,
       SUM(CASE WHEN ggn_match_status = 'no_match' THEN 1 ELSE 0 END) as upload_candidates
FROM master_books
WHERE series_name IS NOT NULL
GROUP BY series_name
HAVING upload_candidates > 0
ORDER BY book_count DESC
"
```

### Statistics by Match Status

```bash
sqlite3 master_books.db "
SELECT
    ggn_match_status,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM master_books), 1) as percentage
FROM master_books
GROUP BY ggn_match_status
ORDER BY count DESC
"
```

## Matching Algorithm (IMPROVED)

The matcher uses a two-step verification process with **improved author matching**:

### 1. Title Matching
- Normalizes title (lowercase, alphanumeric only)
- Extracts first N words (default: 5)
- Checks if title prefix appears in GGn group name

### 2. Author Matching (IMPROVED)
- Extracts author's last name
- Checks **both**:
  1. GGn group name (e.g., "Book Title by John Smith")
  2. **GGn Artists array field** (proper metadata field)
- Handles Artists as strings or dicts
- **Lenient mode:** If GGn has no author info (empty Artists), accepts based on title match alone

### Why This Matters

**Before (checking group name only):**
- ❌ Match rate: 23.3% (136/583 books)
- ❌ Many false negatives (books exist on GGn but marked as "no_match")

**After (checking group name + Artists field):**
- ✅ Match rate: 30.7% (179/583 books)
- ✅ +43 additional matches found (+31.6% improvement)
- ✅ 59 false negatives eliminated

### Example

**MAM Book:**
- Title: "Encyclopedia of Video Games: The Culture, Technology, and Art of Gaming"
- Author: "Mark J P Wolf"

**GGn Group:**
- Group Name: "Encyclopedia of Video Games: The Culture, Technology, and Art of Gaming"
- Artists: [] (empty)

**Result:** ✅ MATCH (title matches, lenient on author since GGn has no author info)

**See:** `MATCHER_IMPROVEMENT_RESULTS.md` for detailed analysis

## Rate Limiting

The GGn API enforces rate limits:
- **Limit:** 5 requests per 10 seconds
- **Implementation:** Token bucket algorithm with timestamps
- **Automatic:** Built-in delays ensure compliance

**Best Practices:**
- Run verification during off-peak hours
- Don't run multiple concurrent sessions
- Monitor for 429 (Too Many Requests) errors

## Troubleshooting

### API Key Issues

```bash
# Test API connection
curl -H "Authorization: YOUR_API_KEY" \
  "https://gazellegames.net/api.php?request=search&search_type=torrents&searchstr=minecraft"
```

### Rate Limit Exceeded

If you see `429` errors:
1. Wait 30 seconds
2. Resume with the same CSV (script tracks progress)
3. Consider reducing concurrent requests

### Empty Results

If no books are found:
- Check MAM database has books: `sqlite3 ../mam_scraper/mam.db "SELECT COUNT(*) FROM mam_torrents"`
- Verify CSV format: `head -5 mam_books_for_verification.csv`
- Check API key is valid

### Database Locked

If master DB creation fails:
- Close any open SQLite connections
- `rm master_books.db` and recreate

## Performance Benchmarks

**Processing Speed:**
- API rate limit: 5 requests / 10 seconds = ~2 seconds per book
- 100 books: ~3.5 minutes
- 500 books: ~17 minutes
- 1000 books: ~35 minutes

**Match Accuracy (after improvement):**
- Match rate: 30.7% (179/583 books)
- False negative rate: 13.3% reduction vs. old matcher
- Ambiguous detection: 3.3% (multi-version books)

## Example Complete Workflow

```bash
#!/bin/bash
# Complete MAM to GGn verification workflow

cd /home/jin23/Code/eBookGGn/ggn_checker
source .venv/bin/activate

echo "Step 1: Export MAM books..."
python3 export_mam_for_verification.py

echo "Step 2: Verify against GGn (this takes ~20 minutes)..."
python3 process_spreadsheet.py mam_books_for_verification.csv --log-level INFO

echo "Step 3: Create master database..."
python3 create_master_db.py

echo "Step 4: Generate upload candidates report..."
sqlite3 -header -csv master_books.db "
SELECT title, author, filetypes, size, series_name
FROM master_books
WHERE ggn_match_status = 'no_match'
ORDER BY series_name, title
" > upload_candidates_$(date +%Y%m%d).csv

echo "Done! Upload candidates saved to upload_candidates_$(date +%Y%m%d).csv"

# Show statistics
echo ""
echo "=== Statistics ==="
sqlite3 master_books.db "
SELECT
    ggn_match_status,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM master_books), 1) || '%' as percentage
FROM master_books
GROUP BY ggn_match_status
"
```

## Project Structure

```
ggn_checker/
├── config.py                         # Configuration and API settings
├── ggn_api.py                        # GGn API client with rate limiting
├── matcher.py                        # Matching logic (IMPROVED with Artists field)
├── process_spreadsheet.py            # Main verification script
├── export_mam_for_verification.py    # Export MAM books to CSV
├── create_master_db.py               # Create combined master database
├── requirements.txt                  # Python dependencies
├── .env.example                      # Environment template
├── .env                              # Your API key (git-ignored)
├── README.md                         # This file
├── MATCHER_IMPROVEMENT_RESULTS.md    # Performance analysis of improved matcher
└── api_guide.txt                     # GGn API documentation
```

## Files

- `process_spreadsheet.py` - Main verification script
- `export_mam_for_verification.py` - Export MAM books to CSV
- `create_master_db.py` - Create combined master database
- `ggn_api.py` - GGn API client with rate limiting
- `matcher.py` - Title/author matching logic (improved)
- `MATCHER_IMPROVEMENT_RESULTS.md` - Performance analysis

## Environment Variables

```bash
# .env file
GGN_API_KEY=your_api_key_here

# Optional overrides
GGN_API_URL=https://gazellegames.net/api.php
MAM_DB_PATH=../mam_scraper/mam.db
```

## Integration with MAM Scraper

This tool integrates with the MAM scraper in `../mam_scraper/`:

**Workflow:**
1. Scrape MAM books → `mam_scraper/mam.db`
2. Export books → `mam_books_for_verification.csv`
3. Check GGn → `output_books_ggn.csv`
4. Combine data → `master_books.db`

**See also:** `../mam_scraper/README.md` for MAM scraping instructions

## Recent Improvements

### Matcher Enhancement (2025-12-05)

- ✅ Now checks GGn Artists field in addition to group name
- ✅ Improved match rate from 23.3% to 30.7% (+31.6%)
- ✅ Eliminated 59 false negatives (13.3% of no_match pool)
- ✅ Better handling of books with missing author metadata

See `MATCHER_IMPROVEMENT_RESULTS.md` for full details.

## API Documentation

For detailed GGn API documentation, see: `api_guide.txt`

Key endpoints used:
- `?request=search&search_type=torrents` - Search for books
- `?request=torrentgroup&id=X` - Get group details

## Security Notes

- ⚠️ **Never commit `.env` to git** - it contains your API key
- ⚠️ **Keep API key private** - treat it like a password
- ✅ `.gitignore` is configured to exclude `.env`
- ✅ Logs don't contain API keys

## License

This tool is for personal use only. Respect tracker rules and rate limits.
