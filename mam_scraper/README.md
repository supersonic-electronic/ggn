# MyAnonamouse (MyM) Video Game eBook Crawler

Automated web scraper for collecting metadata about video game-related eBooks from MyAnonamouse.
Designed with polite crawling practices, rate limiting, and structured data storage.

**⚠️ IMPORTANT: For Personal Use Only**
- Only use on your own MyAnonamouse account
- Respect MyM's rules and terms of service
- This tool implements rate limiting and polite crawling practices
- Check MyM's FAQ/rules before running

## Features

- **VPN Bypass**: Automatic VPN bypass using firejail (optional)
- **Polite Crawling**: Built-in rate limiting (3-7s delays, long pauses every 15 pages)
- **Dual Authentication**: Support for Firefox profile cookies or form-based login
- **Configurable Searches**: Multiple search configurations for different tags/filetypes
- **SQLite Storage**: Local database with deduplication and CSV export
- **Safety Limits**: Configurable max pages/torrents per run
- **Comprehensive Metadata**: Extracts title, author, tags, description, cover images, etc.
- **Error Handling**: Robust retry logic and error logging

## Project Structure

```
mam_scraper/
├── .env.example                # Environment variable template
├── requirements.txt            # Python dependencies
├── config.py                   # Search definitions and settings
├── auth.py                     # Login and authentication
├── filters.py                  # Search filter application
├── scraper.py                  # Detail page data extraction
├── crawler.py                  # Main crawling logic with pagination
├── db.py                       # SQLite database operations
├── utils.py                    # Timing and helper utilities
├── mam_scraper_cli.py          # Production CLI interface (NEW!)
├── main.py                     # Legacy CLI entry point
├── export_to_csv.py            # CSV export tool
├── run-with-vpn-bypass.sh      # VPN bypass runner script
├── firefox-no-vpn-wrapper.sh   # VPN bypass wrapper (firejail)
├── login-to-profile.sh         # Helper to log into MAM profile
├── README_VPN_BYPASS.md        # VPN bypass documentation
└── logs/                       # Error logs directory
```

## Installation

### 1. Prerequisites

- Python 3.11 or higher (Note: Python 3.13 not yet supported)
- pip (Python package manager)
- A MyAnonamouse account
- firejail (optional, for VPN bypass)

### 2. Set Up Virtual Environment

```bash
cd mam_scraper

# Use Python 3.11 (not 3.13)
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
playwright install firefox
```

### 4. Create Firefox Profile

The scraper uses a dedicated Firefox profile (MAM-Scraper) which is created automatically:

```bash
# Create the profile (done automatically on first run)
firefox -CreateProfile "MAM-Scraper"
```

### 5. Configure Environment

Create a `.env` file from the template:

```bash
cp .env.example .env
```

Find your MAM-Scraper profile path:

```bash
ls ~/.mozilla/firefox/ | grep MAM-Scraper
# Output example: i07xqr33.MAM-Scraper
```

Edit `.env` with your profile path:

```env
# Authentication Mode: "cookies" (recommended) or "form"
LOGIN_MODE=cookies

# Firefox Profile Path - update XXXXXXXX with your actual profile ID
FIREFOX_PROFILE_PATH=/home/username/.mozilla/firefox/XXXXXXXX.MAM-Scraper

# VPN Bypass: Bypass VPN using firejail (optional)
USE_VPN_BYPASS=True
```

### 6. Log Into MyAnonamouse (One-Time Setup)

**IMPORTANT**: Before running the scraper, log into MyAnonamouse in the MAM-Scraper profile:

```bash
./login-to-profile.sh
```

This will:
1. Open Firefox with VPN bypass (if enabled)
2. Navigate to MyAnonamouse
3. Let you log in with your credentials
4. Save cookies in the MAM-Scraper profile

**Close Firefox after logging in.**

### Authentication Modes

**Mode 1: Cookie Reuse (RECOMMENDED - Default)**
- Uses dedicated MAM-Scraper Firefox profile with saved cookies
- No credentials stored in `.env` file
- Supports VPN bypass via firejail
- Requires one-time login via `./login-to-profile.sh`

**Mode 2: Form Login**
- Scripted login using username/password
- Credentials stored in `.env`
- Also supports VPN bypass

```env
LOGIN_MODE=form
MAM_USERNAME=your_username
MAM_PASSWORD=your_password
USE_VPN_BYPASS=True
```

### VPN Bypass (Optional)

If you're behind a VPN and need to access MyAnonamouse directly:

1. Install firejail:
```bash
sudo dnf install firejail  # Fedora
# or
sudo apt install firejail  # Ubuntu/Debian
```

2. Update network settings in `firefox-no-vpn-wrapper.sh` if needed:
```bash
# Edit the script to match your network interface and IP
nano firefox-no-vpn-wrapper.sh
```

3. Set `USE_VPN_BYPASS=True` in `.env` (default)

See **VPN-BYPASS-SETUP.md** for detailed documentation.

## Usage

### Production CLI (Recommended)

The new production CLI (`mam_scraper_cli.py`) provides flexible tag-based searching:

```bash
# Scrape 500 video game epubs
python3 mam_scraper_cli.py --tags "Video Game" --formats epub --max-torrents 500

# Multiple formats
python3 mam_scraper_cli.py --tags "SciFi" --formats epub pdf mobi --max-torrents 1000

# Multiple tags
python3 mam_scraper_cli.py --tags "Video Game" "Fantasy" --formats epub --max-torrents 500

# With CSV export
python3 mam_scraper_cli.py --tags "Video Game" --formats epub --max-torrents 500 --export

# Custom database
python3 mam_scraper_cli.py --tags "SciFi" --formats epub --max-torrents 300 --db scifi.db

# Dry run (test without scraping)
python3 mam_scraper_cli.py --tags "Video Game" --formats epub --max-torrents 500 --dry-run

# Export only (no scraping)
python3 mam_scraper_cli.py --export-only --db mam.db

# Full help
python3 mam_scraper_cli.py --help
```

### Legacy main.py Interface

```bash
# Test mode (1 page, 5 torrents max)
python main.py --test-mode

# Run all searches with default limits
python main.py

# Run specific search
python main.py --search "Video Game + epub"

# Custom limits
python main.py --max-torrents 100 --max-pages 10

# Show database statistics
python main.py --stats

# Run in headless mode (no GUI)
python main.py --headless
```

### Export to CSV

```bash
# Export all data
python export_to_csv.py

# Export to specific file
python export_to_csv.py -o my_export.csv

# Export only one search
python export_to_csv.py --search "Video Game + epub"

# Export with limit
python export_to_csv.py --limit 100

# Show database stats
python export_to_csv.py --stats
```

## Configuration

### Search Definitions

Edit `config.py` to customize searches:

```python
SEARCHES = [
    {
        "label": "Video Game + epub",
        "category": "eBooks",
        "language": "English",
        "tags": ["Video Game"],
        "filetypes": ["epub"],
    },
    # Add more search configurations...
]
```

### Safe Crawl Parameters

Adjust rate limiting in `config.py` or via environment variables:

```python
SAFE_CRAWL = {
    "min_delay_seconds": 3,           # Min wait between requests
    "max_delay_seconds": 7,           # Max wait (randomized)
    "pages_before_long_pause": 15,    # Pages before long pause
    "long_pause_seconds": 20,         # Duration of long pause
    "max_pages_per_search": 50,       # Max pages per search
    "max_torrents_total": 1000,       # Max torrents per run
    "max_retries": 3,                 # Retry attempts
}
```

## Database Schema

SQLite table `mam_torrents`:

| Field | Type | Description |
|-------|------|-------------|
| id | INTEGER | Primary key |
| detail_url | TEXT | Torrent detail page URL (unique) |
| title | TEXT | Book title |
| author | TEXT | Book author(s) |
| size | TEXT | Torrent size |
| tags | TEXT | Comma-separated tags |
| files_number | INTEGER | Number of files |
| filetypes | TEXT | Comma-separated file types |
| added_time | TEXT | When torrent was added |
| description_html | TEXT | Full HTML description |
| cover_image_url | TEXT | Cover image URL |
| torrent_url | TEXT | Download URL |
| search_label | TEXT | Which search found this |
| search_position | INTEGER | Position in search results |
| search_url | TEXT | Search results URL |
| scraped_at | TEXT | When data was scraped |

## Testing & Development

### Step-by-Step Testing

Before running full crawls, test each component:

```bash
# 1. Test authentication
python auth.py

# 2. Test filter application
python filters.py

# 3. Test detail page scraping
python scraper.py

# 4. Test crawler with minimal limits
python crawler.py

# 5. Full test mode
python main.py --test-mode
```

### Updating Selectors

**IMPORTANT**: CSS selectors in the code are placeholders and need verification:

1. Log into MyAnonamouse in your browser
2. Inspect page elements (F12 Developer Tools)
3. Update selectors in:
   - `auth.py` - Login form fields
   - `filters.py` - Search filter controls
   - `scraper.py` - Detail page data fields
   - `crawler.py` - Result rows and pagination

### Example Selector Update

In `scraper.py`, update title selector after inspecting:

```python
# Before (placeholder)
title_selectors = [
    'h1.torrent-title',
    'h1#torrent-title',
]

# After inspecting actual page
title_selectors = [
    'div.torrent-header h1',  # Actual selector found
]
```

## Safety & Best Practices

### Rate Limiting

The crawler implements multiple safety mechanisms:
- Random delays (3-7s) between requests
- Long pauses (20s) every 15 pages
- Configurable limits on pages and torrents
- Single-threaded operation (no concurrency)

### Error Handling

- Errors logged to `logs/mam_errors.log`
- Retry logic with exponential backoff
- Graceful handling of missing fields
- Safe interruption with Ctrl+C

### Volume Limits

Default limits are conservative:
- 50 pages per search
- 1000 torrents per run
- Increase cautiously based on server response

## Troubleshooting

### Authentication Fails

```bash
# Check credentials in .env
cat .env | grep MAM_

# Test login manually
python auth.py
```

### No Results Found

- Verify selectors by inspecting the website
- Check search filters are correctly applied
- Run with `--log-level DEBUG` for detailed output

### Selector Errors

```bash
# Run tests with screenshots
python filters.py    # Creates test_filters_result.png
python scraper.py    # Creates test_scraper_result.png
```

Check screenshots to verify page structure.

### Rate Limiting Detected

If you see errors or Cloudflare challenges:
1. Increase delays in `config.py`
2. Reduce `max_pages_per_search`
3. Add longer pauses between searches

## File Outputs

- **Database**: `mam.db` (SQLite)
- **Logs**: `logs/mam_errors.log`
- **CSV Exports**: `mam_export_YYYYMMDD_HHMM.csv`

## Next Steps

This crawler is Phase 1 of a larger project:
- **Phase 2**: Use collected data to search for similar torrents on other sites
- **Phase 3**: Cross-reference and deduplication
- **Phase 4**: Automated monitoring and notifications

## License & Disclaimer

This tool is for educational and personal use only. Users are responsible for:
- Complying with MyAnonamouse's terms of service
- Respecting rate limits and server resources
- Not sharing or misusing scraped data
- Understanding legal implications in their jurisdiction

## Support

For issues or questions:
1. Check logs: `cat logs/mam_errors.log`
2. Run with debug logging: `python main.py --log-level DEBUG`
3. Test individual components (see Testing section)

---

**Remember**: Always be a good citizen of the MyAnonamouse community. This tool is designed to be polite and respectful of server resources.
