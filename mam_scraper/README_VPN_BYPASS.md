# MyAnonamouse Scraper - VPN Bypass Setup

## Overview

This scraper uses **firejail** to bypass VPN and access MyAnonamouse directly, while using **Playwright** for browser automation with form-based login.

## How It Works

1. **Network Bypass**: The entire Python script runs inside a firejail network namespace (IP: 192.168.100.201) which bypasses the VPN
2. **Browser Automation**: Playwright launches Firefox (bundled version) inside this namespace, so it inherits the bypassed network
3. **Authentication**: Form-based login using credentials from `.env` file

## Quick Start

### 1. Set Up Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
# Edit .env and add your MAM_USERNAME and MAM_PASSWORD
```

### 2. Test VPN Bypass

```bash
./run-with-vpn-bypass.sh python test_mam_login.py
```

You should see:
- Firejail network configuration (IP: 192.168.100.201)
- "Successfully logged in!"
- Your MyAnonamouse username

### 3. Run the Scraper

```bash
./run-with-vpn-bypass.sh python crawler.py
```

## Configuration (`.env`)

```bash
# MyAnonamouse credentials
MAM_USERNAME=your_email@example.com
MAM_PASSWORD=your_password
MAM_BASE_URL=https://www.myanonamouse.net

# Always use "form" login mode
LOGIN_MODE=form

# Leave profile path empty to use fresh profile
FIREFOX_PROFILE_PATH=

# Set to False when using run-with-vpn-bypass.sh
USE_VPN_BYPASS=False

# Browser settings
BROWSER_HEADLESS=True  # Set to False to see the browser window
BROWSER_TYPE=firefox
```

## Important Notes

### Why Not Use Firefox Profile?

The system Firefox and Playwright's bundled Firefox have different versions, causing profile incompatibility. Using a fresh profile for each run avoids this issue.

### Why run-with-vpn-bypass.sh?

Running the entire Python process inside firejail (instead of wrapping the Firefox binary) allows Playwright to communicate properly with Firefox while still bypassing the VPN.

### Network Configuration

- IP Address: 192.168.100.201
- Interface: enp2s0
- DNS: 8.8.8.8
- Gateway: 192.168.100.1

## Troubleshooting

### Login Fails

1. Check credentials in `.env`
2. Verify MyAnonamouse is accessible: `./run-with-vpn-bypass.sh curl -I https://www.myanonamouse.net`
3. Run with `BROWSER_HEADLESS=False` to see what's happening

### Firejail Errors

1. Ensure firejail is installed: `which firejail`
2. Check network interface name: `ip addr` (should show `enp2s0`)
3. Try running with `--noprofile` if you get permission errors

### Playwright Errors

1. Ensure Playwright Firefox is installed: `playwright install firefox`
2. Check Python dependencies: `pip install -r requirements.txt`

## Files

- `run-with-vpn-bypass.sh` - Wrapper to run Python scripts with VPN bypass
- `test_mam_login.py` - Test script to verify login works
- `auth.py` - Authentication logic
- `config.py` - Configuration management
- `.env` - Your credentials (not in git)
- `.env.example` - Template for `.env`
