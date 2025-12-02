# Quick Start Guide

Get up and running with the MyAnonamouse crawler in 5 steps:

## 1. Set Up Python Environment

```bash
cd /home/jin23/Code/eBookGGn/mam_scraper

# Create virtual environment
python -m venv .venv

# Activate it
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
playwright install firefox
```

## 2. Configure Credentials

```bash
# Copy the template
cp .env.example .env

# Edit with your credentials
nano .env  # or use your preferred editor
```

**Minimum required settings:**
```env
MAM_USERNAME=your_actual_username
MAM_PASSWORD=your_actual_password
LOGIN_MODE=form
```

## 3. Update Selectors (Critical!)

**IMPORTANT**: The CSS selectors in the code are placeholders. You MUST update them by inspecting the actual MyAnonamouse website.

### Testing Each Component:

```bash
# Test 1: Login
python auth.py
# ✓ If this works, you'll see "Authentication successful!"

# Test 2: Filters
python filters.py
# ✓ Check test_filters_result.png screenshot
# ✓ Update selectors in filters.py if needed

# Test 3: Detail Page Scraping
python scraper.py
# ✓ Enter a test URL when prompted (e.g., /t/1060422)
# ✓ Check test_scraper_result.png screenshot
# ✓ Update selectors in scraper.py if needed
```

### How to Find Correct Selectors:

1. Log into MyAnonamouse in Firefox
2. Navigate to the page you want to scrape
3. Right-click an element → "Inspect" (F12)
4. Note the element's:
   - `id` (e.g., `id="title"` → selector: `#title`)
   - `class` (e.g., `class="torrent-title"` → selector: `.torrent-title`)
   - Tag and attributes (e.g., `<input name="username">` → selector: `input[name="username"]`)

## 4. Run Test Crawl

```bash
# Small test: 1 page, 5 torrents max
python main.py --test-mode
```

**What should happen:**
- Browser launches (you'll see it unless using --headless)
- Logs into MyAnonamouse
- Applies filters for first search
- Scrapes up to 5 torrents
- Saves to `mam.db` database

**Check results:**
```bash
python main.py --stats
```

## 5. Run Full Crawl (After Testing)

```bash
# Full crawl with default limits (50 pages, 1000 torrents)
python main.py

# Or custom limits
python main.py --max-torrents 100 --max-pages 10

# Run specific search only
python main.py --search "Video Game + epub"
```

## Export Your Data

```bash
# Export everything to CSV
python export_to_csv.py

# The file will be named: mam_export_YYYYMMDD_HHMM.csv
```

## Troubleshooting Checklist

### ❌ Authentication fails
```bash
# Verify credentials
cat .env | grep MAM_

# Test login manually
python auth.py
```

**Fix**: Check username/password, update selectors in `auth.py`

### ❌ No torrents found
```bash
# Check with debug logging
python main.py --test-mode --log-level DEBUG
```

**Fix**: Update selectors in `crawler.py` (torrent link extraction)

### ❌ Scraper returns None for fields
```bash
# Test specific page
python scraper.py
# Enter URL when prompted
# Check the screenshot created
```

**Fix**: Update selectors in `scraper.py` for that specific field

### ❌ Rate limiting / Cloudflare challenges

**Fix**: Edit `config.py`:
```python
SAFE_CRAWL = {
    "min_delay_seconds": 5,     # Increase from 3
    "max_delay_seconds": 10,    # Increase from 7
    "max_pages_per_search": 20, # Reduce from 50
}
```

## Files to Check

- **Logs**: `logs/mam_errors.log` - Check for errors
- **Database**: `mam.db` - Your scraped data
- **Exports**: `mam_export_*.csv` - CSV exports

## Common Commands

```bash
# Activate environment
source .venv/bin/activate

# Run test
python main.py --test-mode

# View stats
python main.py --stats

# Export data
python export_to_csv.py

# Check logs
cat logs/mam_errors.log | tail -50
```

## Next Steps After Success

1. Customize searches in `config.py`
2. Adjust rate limits based on experience
3. Set up scheduled runs (cron jobs)
4. Use exported CSV data for Phase 2 of project

## Critical Reminder

**You MUST update CSS selectors** in these files:
- `auth.py` - Login form
- `filters.py` - Search filters
- `scraper.py` - Detail page fields
- `crawler.py` - Result links and pagination

The placeholders will likely NOT work out of the box!
