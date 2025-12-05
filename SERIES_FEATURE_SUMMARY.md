# Series Data Extraction Feature

## Summary

Added series name and series ID extraction to the MAM scraper to capture book series information.

## Changes Made

### 1. Updated `mam_scraper/scraper.py`
- Added `series_name` and `series_id` fields to result dictionary
- Added series extraction logic using CSS selector: `a.altColor[href*="/tor/browse.php?series="]`
- Extracts series name from link text
- Parses series ID from URL using regex: `series=(\d+)`

### 2. Updated `mam_scraper/db.py`
- Added `series_name TEXT` and `series_id INTEGER` columns to database schema
- Added migration logic to update existing databases automatically
- Updated `save_to_db()` function to include series fields in INSERT statement

### 3. Database Migration
- Existing `mam.db` has been migrated successfully
- New columns added: `series_name` and `series_id`
- All existing data preserved

## How It Works

When scraping a MAM torrent page, the scraper now looks for series links like:
```html
<a class="altColor" href="/tor/browse.php?series=1918&amp;tor%5Bcat%5D%5D=0">Halo</a>
```

And extracts:
- **Series Name**: "Halo"
- **Series ID**: 1918

## Testing

### Test with Specific Books

Test file created: `mam_scraper/test_halo_series.csv`
```
url
https://www.myanonamouse.net/t/1010772
https://www.myanonamouse.net/t/860984
```

### Run Test (when VPN is available)
```bash
cd /home/jin23/Code/eBookGGn/mam_scraper
source .venv/bin/activate

# Test scrape of Halo books with series data
./run-with-vpn-bypass.sh python3 mam_scraper_cli.py \
    --url-file test_halo_series.csv \
    --db test_series.db
```

### Verify Series Data
```bash
# Check if series data was captured
sqlite3 test_series.db "
SELECT title, author, series_name, series_id 
FROM mam_torrents 
WHERE series_name IS NOT NULL
"
```

Expected output:
```
Halo: Epitaph|Kelly Gay|Halo|1918
Halo: The Rubicon Protocol|Kelly Gay|Halo|1918
```

## Database Schema (Updated)

```sql
CREATE TABLE mam_torrents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    detail_url TEXT UNIQUE NOT NULL,
    title TEXT,
    author TEXT,
    co_author TEXT,
    series_name TEXT,          -- NEW
    series_id INTEGER,         -- NEW
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
);
```

## Usage Examples

### Query Books by Series
```sql
-- Get all books in the Halo series
SELECT title, author, series_id 
FROM mam_torrents 
WHERE series_name = 'Halo'
ORDER BY title;

-- Count books per series
SELECT series_name, COUNT(*) as book_count
FROM mam_torrents
WHERE series_name IS NOT NULL
GROUP BY series_name
ORDER BY book_count DESC;

-- Get all unique series
SELECT DISTINCT series_name, series_id
FROM mam_torrents
WHERE series_name IS NOT NULL
ORDER BY series_name;
```

### Export Series Data
```python
import pandas as pd
import sqlite3

conn = sqlite3.connect('mam.db')
df = pd.read_sql_query("""
    SELECT title, author, series_name, series_id, filetypes
    FROM mam_torrents
    WHERE series_name IS NOT NULL
    ORDER BY series_name, title
""", conn)

df.to_csv('books_by_series.csv', index=False)
```

## GGn Checker Integration

The master database creator (`ggn_checker/create_master_db.py`) will automatically include series fields when merging MAM and GGn data.

### Update Master DB (after rescraping with series data)
```bash
cd /home/jin23/Code/eBookGGn/ggn_checker
source .venv/bin/activate
python3 create_master_db.py
```

The master database will now include:
- All MAM fields (including series_name and series_id)
- GGn verification status
- GGn match details

## Next Steps

1. **Rescrape books with series** (optional):
   ```bash
   # Run a targeted scrape to update series data for existing books
   cd /home/jin23/Code/eBookGGn/mam_scraper
   ./run-with-vpn-bypass.sh python3 mam_scraper_cli.py \
       --tags "video game" \
       --max-torrents 100 \
       --db mam.db
   ```

2. **Recreate master database** to include series fields:
   ```bash
   cd /home/jin23/Code/eBookGGn/ggn_checker
   python3 create_master_db.py
   ```

3. **Query series data** to see which series are most common

## Benefits

- **Better Organization**: Group books by series
- **Upload Decisions**: Easier to identify complete series vs single books
- **GGn Matching**: Can use series information for better matching logic
- **Series Analysis**: Understand which series are most represented

## Files Modified

1. `/home/jin23/Code/eBookGGn/mam_scraper/scraper.py`
2. `/home/jin23/Code/eBookGGn/mam_scraper/db.py`
3. `/home/jin23/Code/eBookGGn/mam_scraper/mam.db` (migrated)

## Files Created

1. `/home/jin23/Code/eBookGGn/mam_scraper/test_halo_series.csv`
2. `/home/jin23/Code/eBookGGn/SERIES_FEATURE_SUMMARY.md` (this file)
