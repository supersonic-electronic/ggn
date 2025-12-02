# MyAnonamouse (MyM) Video Game eBook Crawler

Automated web scraper for collecting metadata about video game-related eBooks from MyAnonamouse.
Designed with polite crawling practices, rate limiting, and structured data storage.

**⚠️ IMPORTANT: For Personal Use Only**
- Only use on your own MyAnonamouse account
- Respect MyM's rules and terms of service
- This tool implements rate limiting and polite crawling practices
- Check MyM's FAQ/rules before running

## Features

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
├── .env.example          # Environment variable template
├── requirements.txt      # Python dependencies
├── config.py            # Search definitions and settings
├── auth.py              # Login and authentication
├── filters.py           # Search filter application
├── scraper.py           # Detail page data extraction
├── crawler.py           # Main crawling logic with pagination
├── db.py                # SQLite database operations
├── utils.py             # Timing and helper utilities
├── main.py              # CLI entry point
├── export_to_csv.py     # CSV export tool
└── logs/                # Error logs directory
```

## Installation

### 1. Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- A MyAnonamouse account

### 2. Set Up Virtual Environment

```bash
cd mam_scraper
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
playwright install firefox
```

### 4. Configure Environment

Create a `.env` file from the template:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# MyAnonamouse Credentials
MAM_USERNAME=your_username
MAM_PASSWORD=your_password
MAM_BASE_URL=https://www.myanonamouse.net

# Authentication Mode: "cookies" or "form"
LOGIN_MODE=form

# Firefox Profile Path (only if LOGIN_MODE=cookies)
# FIREFOX_PROFILE_PATH=/home/username/.mozilla/firefox/xxxxx.default
```

### Authentication Modes

**Mode 1: Form Login (`LOGIN_MODE=form`)**
- Scripted login using username/password
- Simpler setup, credentials stored in `.env`
- Recommended for most users

**Mode 2: Cookie Reuse (`LOGIN_MODE=cookies`)**
- Uses existing Firefox profile with saved cookies
- Set `FIREFOX_PROFILE_PATH` to your Firefox profile directory
- More complex but avoids storing credentials

## Usage

### Basic Commands

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
