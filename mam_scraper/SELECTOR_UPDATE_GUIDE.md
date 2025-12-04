# CSS Selector Update Guide

This guide explains how to find and update the CSS selectors needed for the MyAnonamouse crawler.

## Tools Needed

- Firefox or Chrome browser
- Browser Developer Tools (F12)
- Access to MyAnonamouse account

## Part 1: Browse Page Selectors (filters.py)

### Step 1: Open Browse Page

1. Navigate to: https://www.myanonamouse.net/tor/browse.php
2. Open DevTools (F12)
3. Click the "Inspector" or "Elements" tab

### Step 2: Find Category Dropdown

1. Look for the category dropdown (should say "All Categories" or similar)
2. Right-click → Inspect Element
3. Find the `<select>` tag, look for attributes like:
   - `name="cat"` or `name="category"`
   - `id="category"` or similar
4. Update in `filters.py` line ~50:
   ```python
   category_selectors = [
       'select[name="ACTUAL_NAME"]',  # Replace with actual name
       '#ACTUAL_ID',                   # Replace with actual ID
   ]
   ```

### Step 3: Find Language Dropdown

1. Look for language filter (might be "Advanced Search" section)
2. Right-click → Inspect Element
3. Note the selector (similar process as category)
4. Update in `filters.py` line ~70

### Step 4: Find Tags Toggle & Input

1. Look for "Tags" toggle button and text input
2. Inspect both elements
3. Update in `filters.py` line ~90 (toggle) and ~110 (input)

### Step 5: Find Filetype Checkboxes

1. Look for filetype options (epub, pdf, mobi checkboxes)
2. Inspect checkboxes
3. Note how to identify each filetype checkbox
4. Update in `filters.py` line ~130

### Step 6: Find Submit Button

1. Find the search/submit button
2. Inspect element
3. Update in `filters.py` line ~160

## Part 2: Detail Page Selectors (scraper.py)

### Step 1: Open a Torrent Detail Page

1. Navigate to any torrent: https://www.myanonamouse.net/t/XXXXXX
2. Open DevTools (F12)

### Step 2: Find Each Field

For each field below:
1. Locate the element visually on the page
2. Right-click → Inspect Element
3. Note the CSS selector (class, id, or element structure)
4. Update in `scraper.py`

#### Title (line ~60)
- Usually an `<h1>` or prominent heading
- Update: `title_selectors`

#### Author (line ~75)
- Often near the title
- Might be labeled "Author:", "By:", etc.
- Update: `author_selectors`

#### Size (line ~90)
- Usually shows "XX.XX MiB" or "X.XX GiB"
- Might be in torrent info section
- Update: `size_selectors`

#### Tags (line ~110)
- Often shown as clickable tags/badges
- Might be comma-separated or individual elements
- Update: `tags_selectors`

#### File Count (line ~130)
- Shows "X files" or similar
- Update: `files_selectors`

#### Filetypes (line ~145)
- Shows "epub, pdf" or file extensions
- Update: `filetypes_selectors`

#### Added Time (line ~160)
- Upload date/time
- Format might be "YYYY-MM-DD HH:MM:SS"
- Update: `added_time_selectors`

#### Description (line ~175)
- Main content/description area
- Usually a large text block or HTML content
- Update: `description_selectors`

#### Cover Image (line ~190)
- Book cover thumbnail or large image
- Look for `<img>` tag
- Update: `cover_selectors`

#### Download Link (line ~205)
- "Download" button or link
- URL usually contains `/tor/download.php`
- Update: `download_selectors`

## Quick Selector Examples

### Common selector patterns:

```css
/* By ID */
#torrent-title

/* By class */
.torrent-info

/* By attribute */
input[name="category"]
a[href*="/download"]

/* By text content */
button:has-text("Search")
span:has-text("Size:")

/* By position */
.info-row:nth-child(2)

/* Combined */
div.torrent-details span.author
```

## Testing Selectors

### In Browser Console:

```javascript
// Test if selector finds element
document.querySelector('YOUR_SELECTOR')

// Test if it finds multiple elements
document.querySelectorAll('YOUR_SELECTOR')

// Get text content
document.querySelector('YOUR_SELECTOR').textContent
```

### In Python (after updating):

```bash
# Run test crawler
./run-with-vpn-bypass.sh python test_crawler.py

# Check logs for warnings
tail -f logs/mam_errors.log
```

## Tips

1. **Be Specific**: Use unique selectors that won't match unintended elements
2. **Test Multiple Pages**: Check if selectors work across different torrents
3. **Handle Missing Data**: Not all fields may be present on all torrents
4. **Use Fallbacks**: Provide multiple selector options (already in code)
5. **Check Logs**: Look for "WARNING: Could not extract" messages

## After Updating Selectors

1. Save changes to `filters.py` and `scraper.py`
2. Run test: `./run-with-vpn-bypass.sh python test_crawler.py`
3. Check database: Look for complete data in `mam.db`
4. Review logs: Verify no warnings about missing selectors
5. Export to CSV: `python export_to_csv.py` to review data

## Files to Update

- **filters.py**: Lines 50-165 (browse page filters)
- **scraper.py**: Lines 60-210 (detail page data extraction)

## Need Help?

If you're stuck finding selectors:
1. Take a screenshot of the DevTools inspector
2. Share the HTML structure of the element
3. We can help identify the correct selector
