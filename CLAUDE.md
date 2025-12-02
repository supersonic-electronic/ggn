PROJECT: MyAnonamouse (MyM) Video Game eBook Crawler for Claude Code
====================================================================
This will be one phase of the bigger project that will use output from this phase to search for similar torrents on another site.

GOAL
----
Automate browsing of MyAnonamouse (MyM) to collect structured metadata about
video game-related eBooks under specific filters (eBooks, English, certain tags
and filetypes) and store them locally (SQLite + CSV export).

We will:
1. Log in to MyM (using either existing Firefox cookies/profile or scripted login).
2. Apply search filters (Category=eBooks, Language=English, Tags + FileType filtered).
3. Crawl through all results pages (with safe crawling practices).
4. Open each torrent’s detail page (/t/ID) and extract:
   - title
   - author
   - size
   - tags
   - files_number
   - filetypes
   - added_time
   - full description
   - cover_image_url
   - torrent_url
   - search_label
   - search_position (index in search results)
5. Save the data into a local DB (SQLite) and export to CSV when needed.

----------------------------------------------------------------------
0. SAFETY, LEGALITY & "POLITE CRAWLING" PRACTICES
----------------------------------------------------------------------

- Respect MyM rules:
  - Double-check site rules/FAQ for any bans on scraping or automation.
  - Use this only on your own account, for personal cataloging.
- Rate limiting (VERY IMPORTANT):
  - Only a single browser/tab doing requests at once (no concurrency).
  - Between page loads:
    - Delay between 3–7 seconds (randomized).
    - Longer (10–20 second) pauses after N pages (e.g., every 10–20 pages).
  - If the server responds slowly or you see errors / Cloudflare / rate limiting:
    - Back off exponentially (e.g., wait 30s → 1 min → 3 min, then abort).
- Volume limits:
  - Configurable maximum:
    - Max pages per search (e.g., 50).
    - Max torrents per run (e.g., 1000).
- Identification:
  - Use a standard browser-like user-agent (Playwright/Selenium default is fine).
- Error handling:
  - Catch navigation errors, timeouts, missing fields.
  - Log errors to a file (`logs/mam_errors.log`) for review.
  - Don’t hammer retry: at most 2–3 retries with delay.

We will bake delays and limits directly into the crawler logic.

----------------------------------------------------------------------
1. TECH STACK & FILE STRUCTURE
----------------------------------------------------------------------

Language: Python 3.x

Browser Automation:
- Playwright (preferred) OR Selenium + geckodriver.

Storage:
- SQLite database for structured data.
- CSV export next to DB for quick manual inspection.

Configuration:
- Environment variables or .env file for credentials and options.

Example project structure:

mam_scraper/
  ├─ .env                      # MAM_USERNAME, MAM_PASSWORD, etc.
  ├─ config.py                 # Search definitions, rate limits, options
  ├─ auth.py                   # Login / session helpers
  ├─ filters.py                # Functions to apply MyM search filters
  ├─ crawler.py                # Core crawling loop (searches + pagination)
  ├─ scraper.py                # Detail-page scraping logic
  ├─ db.py                     # SQLite init + insert/upsert functions
  ├─ export_to_csv.py          # Simple exporter
  ├─ utils.py                  # Shared timing / safe-crawling helpers
  ├─ requirements.txt          # playwright, python-dotenv, etc.
  └─ README.md                 # How to run

----------------------------------------------------------------------
2. ENVIRONMENT SETUP
----------------------------------------------------------------------

Task A: Environment & Dependencies

1. Create project folder and virtual environment:
   - mkdir mam_scraper
   - cd mam_scraper
   - python -m venv .venv
   - source .venv/bin/activate

2. Install dependencies (example):
   - pip install playwright python-dotenv
   - playwright install firefox
   (If using Selenium instead: pip install selenium webdriver-manager)

3. Create .env file (NOT checked into git):
   MAM_USERNAME="your_username"
   MAM_PASSWORD="your_password"
   MAM_BASE_URL="https://www.myanonamouse.net"

4. Create requirements.txt from the venv if desired:
   - pip freeze > requirements.txt

Claude Code tasks:
- Generate requirements.txt.
- Add sample .env template (.env.example) without real credentials.

----------------------------------------------------------------------
3. LOGIN STRATEGY (COOKIES VS FORM LOGIN)
----------------------------------------------------------------------

We support two modes:

Mode 1: Reuse existing Firefox profile ("firefox-no-vpn")
---------------------------------------------------------

- Identify the Firefox profile used by your `firefox-no-vpn` launcher:
  - Something like: ~/.mozilla/firefox/XXXXX.no-vpn-profile
- Configure Playwright to use:
  - user_data_dir = "~/.mozilla/firefox/XXXXX.no-vpn-profile"
- This way:
  - If you’re already logged in via GUI in that profile, the crawler starts
    with valid cookies and no login step needed.
- Limitation: profile must be readable; avoid simultaneous modification by GUI
  Firefox and Playwright at the same time if possible.

Mode 2: Scripted login using form
---------------------------------

- Suitable if:
  - Reusing profile is inconvenient.
  - You’re fine with storing creds in env.

auth.py
- Implement:

  - load creds from env
  - function ensure_logged_in(page):

    1. Go to login page:
       https://www.myanonamouse.net/login.php?returnto=%2F
    2. Check if already logged in:
       - For example, look for an element that only appears when logged in,
         like a "logout" link or username in header.
    3. If not logged in:
       - Fill username/email input.
       - Fill password input.
       - Submit form and wait for navigation.
    4. Verify success (again check header elements).

Claude Code tasks:
- Inspect login page DOM (using its browser tool).
- Fill in correct CSS selectors / IDs for email, password, and submit button.
- Implement auth.py.

config.py
- Add a flag:
  USE_EXISTING_PROFILE = True/False
  LOGIN_MODE = "cookies" or "form"

----------------------------------------------------------------------
4. DEFINING SEARCHES & OPTIONS
----------------------------------------------------------------------

Goal searches:
- Category: eBooks
- Language: English
- Tags ON, FileType ON
- Tags: e.g., "Video Game"
- Filetypes: e.g., "epub", "pdf" (we’ll run different searches)

config.py example:

SEARCHES = [
    {
        "label": "Video Game + epub",
        "category": "eBooks",
        "language": "English",
        "tags": ["Video Game"],
        "filetypes": ["epub"],
    },
    {
        "label": "Video Game + pdf",
        "category": "eBooks",
        "language": "English",
        "tags": ["Video Game"],
        "filetypes": ["pdf"],
    },
    # Additional combinations as needed...
]

Safe crawling parameters:

SAFE_CRAWL = {
    "min_delay_seconds": 3,          # minimum wait after each page action
    "max_delay_seconds": 7,          # maximum wait for random sleep
    "pages_before_long_pause": 15,   # after 15 pages, long pause
    "long_pause_seconds": 20,        # 20s long pause
    "max_pages_per_search": 50,      # safety limit
    "max_torrents_total": 1000,      # per run cap
    "max_retries": 3,                # for transient errors
}

Claude Code tasks:
- Populate config.py with SEARCHES and SAFE_CRAWL.
- Make SAFE_CRAWL tunable via env or CLI.

----------------------------------------------------------------------
5. APPLYING SEARCH FILTERS IN THE BROWSER
----------------------------------------------------------------------

filters.py
- Provide a function:

  async def apply_filters(page, search) -> str:
      """
      Applies Category, Language, tags, filetypes for a given search.
      Returns the resulting search URL (permalink) after applying filters.
      """

Steps:
1. Navigate to torrent browse/search page:
   - Likely something like /tor/browse.php (you will confirm while logged in).
2. Set "Category" dropdown to "eBooks".
3. Set "Advanced language" dropdown to "English".
4. Ensure the toggles:
   - Tags ON
   - FileType ON
5. Enter/Select tags:
   - For example "Video Game" in the tag box.
6. Select filetypes:
   - e.g., check the "epub" checkbox, or multi-select.
7. Click the search/submit button.
8. Wait for network idle and store `page.url` as search_url.

Also, call safe_sleep() after applying filters and after results load.

Claude Code tasks:
- Inspect the browse/search page DOM.
- Insert correct CSS selectors / ID attributes.
- Implement apply_filters(page, search).

----------------------------------------------------------------------
6. SAFE SLEEP / TIMING UTILITIES
----------------------------------------------------------------------

utils.py
- Implement helper:

  import asyncio, random, time, logging

  async def safe_sleep(config, is_long=False):
      if is_long:
          delay = config["long_pause_seconds"]
      else:
          delay = random.uniform(
              config["min_delay_seconds"],
              config["max_delay_seconds"],
          )
      logging.info(f"Sleeping for {delay:.2f} seconds to be polite.")
      await asyncio.sleep(delay)

Use safe_sleep:
- After each:
  - page.goto(...)
  - click on pagination link
  - navigation to detail page
  - returning from detail page
- After N pages, call safe_sleep(config, is_long=True).

Claude Code tasks:
- Implement safe_sleep in utils.py and hook it throughout crawler logic.

----------------------------------------------------------------------
7. CRAWLING SEARCH RESULTS (PAGINATION + LINK COLLECTION)
----------------------------------------------------------------------

crawler.py
- Main function:

  async def crawl_all_searches():
      - Set up browser and context (respect USE_EXISTING_PROFILE).
      - Create a single page object.
      - Initialize DB connection.
      - For each search in SEARCHES:
          - Run crawl_single_search(page, db, search)

- For each search:

  async def crawl_single_search(page, db, search):
      - search_url = await apply_filters(page, search)
      - Call safe_sleep(...) after filters.
      - position_counter = 0
      - pages_seen = 0

      while True:
          - pages_seen += 1
          - If pages_seen > SAFE_CRAWL["max_pages_per_search"]:
              - break

          - Extract all torrent rows:
              * Use CSS selectors for result table rows.
              * Each row should contain:
                  - link to detail page (href with /t/ID).
              * For each row:
                  - position_counter += 1
                  - If total torrents saved > SAFE_CRAWL["max_torrents_total"]:
                      - break entire crawl.
                  - detail_url = ... from row
                  - data = await scrape_detail_page(page, detail_url)
                  - data["search_label"] = search["label"]
                  - data["search_position"] = position_counter
                  - data["search_url"] = search_url
                  - save_to_db(db, data)
                  - await safe_sleep(...) between each detail page visit.

          - Find "next page" link or button:
              * If not found: break.
              * Click next.
              * Wait for network idle.
              * Call safe_sleep(...).
              * If pages_seen % SAFE_CRAWL["pages_before_long_pause"] == 0:
                    await safe_sleep(config, is_long=True)

Claude Code tasks:
- Fill in CSS selectors for torrent rows and next-page button.
- Implement pagination detection.
- Plug in safe_sleep in all the right places.

----------------------------------------------------------------------
8. SCRAPING DETAIL PAGES
----------------------------------------------------------------------

scraper.py
- Core function:

  async def scrape_detail_page(page, url) -> dict:

Fields to extract (based on your example /t/1060422):

- title:
  "Player vs. Monster: The Making and Breaking of Video Game Monstrosity"
- author:
  "Jaroslav Svelch"
- size:
  "40.83 MiB"
- tags:
  "Video Game Studies, Cultural Studies, Media Studies, Game Design, Pop Culture, Digital Media"
- files_number:
  2
- filetypes:
  "epub, pdf"
- added_time:
  "2024-08-08 04:00:57"
- description:
  Full text/HTML of description, starting with:
  "A study of the gruesome game characters we love to beat..."
- cover_image_url:
  "https://cdn.myanonamouse.net/t/p/1764032830/large/1060422.jpeg"
- torrent_url:
  Long download link:
  "https://www.myanonamouse.net/tor/download.php/..."

Implementation steps:
1. await page.goto(url)
2. await page.wait_for_load_state("networkidle")
3. await safe_sleep(...) to be polite.
4. Use page.inner_text / inner_html / get_attribute to extract each field.
5. Normalize:
   - tags: split by comma, strip whitespace.
   - filetypes: split by comma, lower-case.
6. Return dict with keys:
   - "detail_url"
   - "title"
   - "author"
   - "size"
   - "tags"           (comma-separated string or list)
   - "files_number"
   - "filetypes"      (comma-separated string or list)
   - "added_time"
   - "description_html"
   - "cover_image_url"
   - "torrent_url"

Claude Code tasks:
- Inspect a sample detail page’s HTML.
- Insert correct selectors for each field.
- Implement scrape_detail_page(page, url).

----------------------------------------------------------------------
9. DATABASE DESIGN & OPERATIONS
----------------------------------------------------------------------

db.py
- Use sqlite3 or SQLAlchemy. Simple sqlite3 is fine.

Schema: table mam_torrents:

- id              INTEGER PRIMARY KEY AUTOINCREMENT
- detail_url      TEXT UNIQUE
- title           TEXT
- author          TEXT
- size            TEXT
- tags            TEXT          -- comma-separated
- files_number    INTEGER
- filetypes       TEXT          -- comma-separated
- added_time      TEXT
- description_html TEXT
- cover_image_url TEXT
- torrent_url     TEXT
- search_label    TEXT
- search_position INTEGER
- search_url      TEXT
- scraped_at      TEXT          -- ISO timestamp

Functions:

- init_db(db_path="mam.db"):
  - Create table if not exists.
- save_to_db(conn, record: dict):
  - INSERT OR REPLACE INTO mam_torrents
    (detail_url, title, author, size, tags, files_number, filetypes,
     added_time, description_html, cover_image_url, torrent_url,
     search_label, search_position, search_url, scraped_at)
  - Values from record + current timestamp.
  - Use detail_url as UNIQUE to avoid duplicates across runs.

Claude Code tasks:
- Implement init_db and save_to_db with parameterized SQL.
- Wire into crawler.py so each scraped record is saved immediately.

----------------------------------------------------------------------
10. CSV EXPORT
----------------------------------------------------------------------

export_to_csv.py
- Script that:
  - Connects to mam.db.
  - SELECTs rows from mam_torrents.
  - Writes to CSV, e.g. mam_export_YYYYMMDD_HHMM.csv.

Fields:
- id, detail_url, title, author, size, tags, files_number, filetypes,
  added_time, description_html, cover_image_url, torrent_url,
  search_label, search_position, search_url, scraped_at.

Claude Code tasks:
- Implement export_to_csv.py.
- Optionally, add CLI args (e.g., `--since-date`).

----------------------------------------------------------------------
11. COMMAND-LINE RUNNER / ENTRY POINT
----------------------------------------------------------------------

Entry script: main.py or crawler.py with CLI.

Example behavior:
- `python crawler.py`  -> runs all SEARCHES.
- Optional flags:
  - `--search-label "Video Game + epub"` to run only specific search.
  - `--max-torrents 300` to override config.
  - `--dry-run` to just list URLs without scraping/saving.

Flow in main():
1. Load config.
2. Initialize DB.
3. Initialize Playwright browser:
   - if USE_EXISTING_PROFILE:
       - use the relevant user_data_dir.
   - else:
       - default context + scripted login via auth.ensure_logged_in().
4. For each selected search:
   - call crawl_single_search().
5. Close browser.
6. Exit cleanly.

Claude Code tasks:
- Create main.py.
- Add argparse for basic flags.
- Call crawl_all_searches() with respect to config & flags.

----------------------------------------------------------------------
12. INTEGRATION WITH CLAUDE CODE
----------------------------------------------------------------------

How you’ll use Claude Code with this plan:

1. Paste this plan into Claude Code as your “project outline” / instructions.
2. Ask it to:
   a. Scaffold the file structure and empty files.
   b. Fill in config.py, db.py, utils.py with appropriate code.
   c. Implement auth.py based on the actual login form (you may need to run
      its browser tool once to show the HTML).
   d. Implement filters.py and scraper.py by inspecting MyM’s HTML inside
      Claude Code’s browser (while you’re logged in or via scripted login).
   e. Implement crawler.py and main.py with safe crawling and delays.
3. Run small tests:
   - First, just log in and print current username.
   - Next, apply filters and print search_url.
   - Then, scrape a single page and 1–2 detail pages.
   - Only after that, allow full-run mode (with SAFE_CRAWL limits active).
4. Adjust rate limits:
   - If you see any slowdown or captcha/rate-limit, increase delays and reduce
     max pages / torrents per run.

----------------------------------------------------------------------
13. OPTIONAL: LAUNCHING `firefox-no-vpn` SPECIFICALLY
----------------------------------------------------------------------

If you need the automated browser to use the same binary/network as your
`firefox-no-vpn` script:

- Determine what `firefox-no-vpn` actually does:
  - If it’s simply a wrapper calling firefox with a specific profile:
      - In Playwright, you can set:
        - executable path to that same firefox binary.
        - user_data_dir to the same profile directory.
  - If it changes routing (e.g., using a special network namespace), it might
    be easier to run the crawler in that same environment (e.g., run the script
    inside the same shell / namespace where firefox-no-vpn operates).

However, for the crawling code itself, we will NOT automate an already-open GUI
Firefox window; instead we use our own Firefox instance with the same profile
and cookies.

----------------------------------------------------------------------
END OF PLAN
----------------------------------------------------------------------
