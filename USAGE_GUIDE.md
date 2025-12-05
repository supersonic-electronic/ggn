# Complete Usage Guide: MAM Scraper + GGn Checker

This guide shows you how to use the complete workflow from scraping MAM books to creating a master database with GGn verification.

## Overview

The workflow has 3 main phases:

1. **MAM Scraper** - Scrape books from MyAnonamouse
2. **GGn Checker** - Verify which books exist on GGn
3. **Master Database** - Combine data and identify upload candidates

```
MAM Scraper → mam.db → Export CSV → GGn Checker → Master Database
```

## Prerequisites

### 1. MAM Cookies/Login

Set up firefox-no-vpn profile with MAM login or configure credentials. See `mam_scraper/README.md`

### 2. GGn API Key

Get your API key from: https://gazellegames.net/user.php?action=edit

Create `ggn_checker/.env`:
```bash
GGN_API_KEY=your_api_key_here
```

### 3. Python Environment

```bash
# MAM Scraper
cd /home/jin23/Code/eBookGGn/mam_scraper
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install firefox

# GGn Checker
cd /home/jin23/Code/eBookGGn/ggn_checker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Phase 1: Scrape MAM Books

### Option A: Scrape by Tags (Recommended)

```bash
cd /home/jin23/Code/eBookGGn/mam_scraper
source .venv/bin/activate

# Scrape video game books (EPUB)
./run-with-vpn-bypass.sh python3 mam_scraper_cli.py \
    --tags "Video Game" \
    --filetypes "epub" \
    --max-torrents 500 \
    --db mam.db

# Takes ~30-60 minutes depending on max-torrents
```

### Option B: Scrape from URL List

```bash
# Create CSV with URLs
cat > my_books.csv <<EOF
url
https://www.myanonamouse.net/t/1234567
https://www.myanonamouse.net/t/2345678
EOF

# Scrape specific URLs
./run-with-vpn-bypass.sh python3 mam_scraper_cli.py \
    --url-file my_books.csv \
    --db mam.db
```

### Verify MAM Database

```bash
sqlite3 mam.db "
SELECT COUNT(*) as total_books,
       COUNT(DISTINCT series_name) as total_series
FROM mam_torrents
"
```

## Phase 2: Export for GGn Verification

```bash
cd /home/jin23/Code/eBookGGn/ggn_checker
source .venv/bin/activate

# Export MAM books to CSV for verification
python3 export_mam_for_verification.py

# Output: mam_books_for_verification.csv
# Preview:
head mam_books_for_verification.csv
```

**Output Format:**
```csv
title,author
"Video Game Design for Dummies","John Smith"
"StarCraft: Ghost - Spectres","Nate Kenyon"
...
```

## Phase 3: Check Against GGn

```bash
# Run GGn verification (takes ~2 seconds per book)
python3 process_spreadsheet.py mam_books_for_verification.csv --log-level INFO

# For 583 books: ~20 minutes
# Progress updates every 25 books
```

**What Happens:**
1. Searches GGn API for each book
2. Checks title + author matching
3. Verifies in both group name and Artists field
4. Classifies as: match, no_match, ambiguous, error

**Output:** `output_books_ggn.csv`

### Monitor Progress

```bash
# In another terminal:
tail -f ggn_checker.log

# Check progress:
grep "Progress:" verification_run.log | tail -1
```

## Phase 4: Create Master Database

```bash
# Combine MAM data with GGn verification results
python3 create_master_db.py

# Output: master_books.db
```

**What's Included:**
- All MAM fields (title, author, size, series, etc.)
- GGn match status
- GGn group details (if matched)

### View Statistics

```bash
sqlite3 master_books.db "
SELECT
    ggn_match_status,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM master_books), 1) || '%' as percentage
FROM master_books
GROUP BY ggn_match_status
"
```

**Expected Output:**
```
no_match|385|66.0%
match|179|30.7%
ambiguous|19|3.3%
```

## Phase 5: Query Master Database

### Find Upload Candidates

Books on MAM but NOT on GGn:

```bash
sqlite3 -header -csv master_books.db "
SELECT title, author, filetypes, size, tags
FROM master_books
WHERE ggn_match_status = 'no_match'
ORDER BY title
" > upload_candidates.csv
```

### Find Books Already on GGn

Books on BOTH trackers:

```bash
sqlite3 -header -csv master_books.db "
SELECT title, author, ggn_group_name, ggn_formats
FROM master_books
WHERE ggn_match_status = 'match'
ORDER BY title
" > confirmed_on_ggn.csv
```

### Find Books by Series

```bash
sqlite3 master_books.db "
SELECT series_name,
       COUNT(*) as total_books,
       SUM(CASE WHEN ggn_match_status = 'no_match' THEN 1 ELSE 0 END) as upload_candidates,
       SUM(CASE WHEN ggn_match_status = 'match' THEN 1 ELSE 0 END) as on_ggn
FROM master_books
WHERE series_name IS NOT NULL
GROUP BY series_name
HAVING upload_candidates > 0
ORDER BY total_books DESC
LIMIT 10
"
```

**Example Output:**
```
Halo|12|8|4
StarCraft|10|6|4
World of Warcraft|8|3|5
```

This shows:
- Halo: 12 total books, 8 upload candidates, 4 already on GGn
- StarCraft: 10 total books, 6 upload candidates, 4 already on GGn

### Find High-Priority Upload Candidates

Books with EPUB format, not on GGn:

```bash
sqlite3 -header -csv master_books.db "
SELECT title, author, size, tags
FROM master_books
WHERE ggn_match_status = 'no_match'
  AND filetypes LIKE '%epub%'
ORDER BY series_name, title
" > priority_uploads.csv
```

### Advanced Query: Series Analysis

```bash
sqlite3 master_books.db "
SELECT series_name,
       GROUP_CONCAT(
           CASE WHEN ggn_match_status = 'no_match' THEN title END,
           '; '
       ) as books_to_upload
FROM master_books
WHERE series_name IS NOT NULL
  AND ggn_match_status = 'no_match'
GROUP BY series_name
HAVING COUNT(*) >= 3
ORDER BY COUNT(*) DESC
"
```

This finds complete series (3+ books) that are upload candidates.

## Complete Automation Script

Save this as `run_complete_workflow.sh`:

```bash
#!/bin/bash
set -e  # Exit on error

echo "===================================================================="
echo "  MAM → GGn Complete Workflow"
echo "===================================================================="
echo ""

# Configuration
MAM_DB="../mam_scraper/mam.db"
GGN_CSV="output_books_ggn.csv"
MASTER_DB="master_books.db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

cd /home/jin23/Code/eBookGGn/ggn_checker
source .venv/bin/activate

echo "Step 1: Export MAM books for verification..."
python3 export_mam_for_verification.py --db "$MAM_DB"
BOOK_COUNT=$(wc -l < mam_books_for_verification.csv)
BOOK_COUNT=$((BOOK_COUNT - 1))  # Subtract header
echo "  → Exported $BOOK_COUNT books"
echo ""

echo "Step 2: Verify against GGn (this will take ~$((BOOK_COUNT * 2 / 60)) minutes)..."
echo "  → Processing with improved matcher (checks Artists field)"
python3 process_spreadsheet.py mam_books_for_verification.csv --log-level INFO
echo "  → Verification complete"
echo ""

echo "Step 3: Create master database..."
python3 create_master_db.py --mam-db "$MAM_DB" --ggn-csv "$GGN_CSV" --output "$MASTER_DB"
echo "  → Master database created: $MASTER_DB"
echo ""

echo "Step 4: Generate reports..."

# Upload candidates
sqlite3 -header -csv "$MASTER_DB" "
SELECT title, author, filetypes, size, series_name, tags
FROM master_books
WHERE ggn_match_status = 'no_match'
ORDER BY series_name, title
" > "upload_candidates_$TIMESTAMP.csv"
echo "  → Upload candidates: upload_candidates_$TIMESTAMP.csv"

# Already on GGn
sqlite3 -header -csv "$MASTER_DB" "
SELECT title, author, ggn_group_name
FROM master_books
WHERE ggn_match_status = 'match'
ORDER BY title
" > "confirmed_on_ggn_$TIMESTAMP.csv"
echo "  → Confirmed on GGn: confirmed_on_ggn_$TIMESTAMP.csv"

# Series summary
sqlite3 -header -csv "$MASTER_DB" "
SELECT series_name,
       COUNT(*) as total_books,
       SUM(CASE WHEN ggn_match_status = 'no_match' THEN 1 ELSE 0 END) as upload_candidates,
       SUM(CASE WHEN ggn_match_status = 'match' THEN 1 ELSE 0 END) as on_ggn
FROM master_books
WHERE series_name IS NOT NULL
GROUP BY series_name
ORDER BY total_books DESC
" > "series_summary_$TIMESTAMP.csv"
echo "  → Series summary: series_summary_$TIMESTAMP.csv"
echo ""

echo "===================================================================="
echo "  Statistics"
echo "===================================================================="
sqlite3 "$MASTER_DB" "
SELECT
    ggn_match_status as Status,
    COUNT(*) as Count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM master_books), 1) || '%' as Percentage
FROM master_books
GROUP BY ggn_match_status
ORDER BY COUNT(*) DESC
"
echo ""

echo "===================================================================="
echo "  Complete! Next Steps:"
echo "===================================================================="
echo "1. Review upload candidates: upload_candidates_$TIMESTAMP.csv"
echo "2. Check series for batch uploads: series_summary_$TIMESTAMP.csv"
echo "3. Query master database: sqlite3 $MASTER_DB"
echo ""
```

Make it executable:
```bash
chmod +x run_complete_workflow.sh
```

Run it:
```bash
./run_complete_workflow.sh
```

## Incremental Updates

### Update with New MAM Books

```bash
# 1. Scrape new books
cd /home/jin23/Code/eBookGGn/mam_scraper
./run-with-vpn-bypass.sh python3 mam_scraper_cli.py --tags "Video Game" --max-torrents 100

# 2. Re-run GGn verification (only new books will be checked)
cd /home/jin23/Code/eBookGGn/ggn_checker
python3 export_mam_for_verification.py
python3 process_spreadsheet.py mam_books_for_verification.csv

# 3. Recreate master database
python3 create_master_db.py
```

## Troubleshooting

### MAM Scraper Issues

**VPN Connection Failed:**
```bash
# Check VPN status
./mam_scraper/firefox-no-vpn-wrapper.sh --check

# Restart VPN
sudo systemctl restart openvpn
```

**Firejail Address Conflict:**
```bash
# Kill existing firejail instances
killall firejail

# Or use existing Firefox profile
./run-with-vpn-bypass.sh python3 mam_scraper_cli.py ...
```

### GGn Checker Issues

**API Key Invalid:**
```bash
# Test API key
curl -H "Authorization: YOUR_API_KEY" \
  "https://gazellegames.net/api.php?request=search&searchstr=minecraft"
```

**Rate Limit Hit:**
- Normal behavior, script automatically waits
- Don't run multiple concurrent sessions
- Processing takes ~2 seconds per book

**No Matches Found:**
```bash
# Check if GGn API is working
python3 -c "
from ggn_api import GGNClient
client = GGNClient()
print(client.search_torrents('minecraft'))
"
```

### Database Issues

**Database Locked:**
```bash
# Close all connections
rm master_books.db
python3 create_master_db.py
```

**Missing Columns:**
```bash
# MAM database auto-migrates
# Just open it:
sqlite3 ../mam_scraper/mam.db "SELECT series_name FROM mam_torrents LIMIT 1"
```

## Performance Tips

1. **Batch Processing:** Scrape MAM in batches of 500-1000 books
2. **Off-Peak Hours:** Run GGn verification during off-peak hours
3. **Incremental Updates:** Only verify new books, not entire database
4. **Series-First:** Focus on complete series for batch uploads

## File Reference

```
eBookGGn/
├── mam_scraper/
│   ├── mam.db                          # MAM books database
│   ├── mam_scraper_cli.py              # Main scraper
│   └── README.md                       # Scraper docs
│
├── ggn_checker/
│   ├── export_mam_for_verification.py  # Export MAM → CSV
│   ├── process_spreadsheet.py          # GGn verification
│   ├── create_master_db.py             # Create master DB
│   ├── master_books.db                 # Master database
│   ├── output_books_ggn.csv            # GGn results
│   └── README.md                       # Checker docs
│
└── USAGE_GUIDE.md                      # This file
```

## GitHub Repository

View code and documentation:
https://github.com/supersonic-electronic/ggn

## Support

For issues:
1. Check log files: `ggn_checker.log`, `verification_run.log`
2. Run with `--log-level DEBUG` for verbose output
3. Review README files in each module
4. Check GitHub issues

## Quick Reference

```bash
# Complete workflow (one command)
cd /home/jin23/Code/eBookGGn/ggn_checker && ./run_complete_workflow.sh

# Manual workflow
cd /home/jin23/Code/eBookGGn/ggn_checker
source .venv/bin/activate
python3 export_mam_for_verification.py
python3 process_spreadsheet.py mam_books_for_verification.csv --log-level INFO
python3 create_master_db.py

# View results
sqlite3 master_books.db "SELECT * FROM master_books WHERE ggn_match_status = 'no_match' LIMIT 10"
```
