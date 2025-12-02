# VPN Bypass Setup for MAM Scraper

This document explains the VPN bypass configuration that allows the scraper to access MyAnonamouse even when your system is behind a VPN.

## What Was Set Up

### 1. New Firefox Profile
- **Profile Name**: `MAM-Scraper`
- **Profile Path**: `/home/jin23/.mozilla/firefox/i07xqr33.MAM-Scraper`
- **Purpose**: Dedicated profile for the scraper, separate from your regular browsing

### 2. VPN Bypass Wrapper Script
- **File**: `firefox-no-vpn-wrapper.sh`
- **Function**: Launches Firefox through `firejail` with direct network access
- **Network Config**: Same as your `firefox-no-vpn` command
  - Interface: `enp2s0`
  - IP: `192.168.100.199`
  - DNS: `8.8.8.8`

### 3. Login Helper Script
- **File**: `login-to-profile.sh`
- **Purpose**: Easy way to log into MyAnonamouse in the MAM-Scraper profile

## How It Works

```
User runs scraper
    ↓
Playwright launches Firefox
    ↓
Uses firefox-no-vpn-wrapper.sh
    ↓
Wrapper executes: firejail --net=enp2s0 firefox
    ↓
Firefox bypasses VPN, accesses MyAnonamouse
    ↓
Reuses cookies from MAM-Scraper profile
```

## Setup Steps

### Step 1: Log Into MyAnonamouse (One-Time)

Before running the scraper, you need to log into MyAnonamouse in the MAM-Scraper profile:

```bash
./login-to-profile.sh
```

This will:
1. Open Firefox with VPN bypass
2. Navigate to MyAnonamouse
3. Let you log in with your credentials
4. Save cookies in the MAM-Scraper profile

**IMPORTANT**: After logging in, close Firefox. The cookies are now saved.

### Step 2: Test Authentication

Verify the scraper can access your cookies:

```bash
source .venv/bin/activate
python auth.py
```

You should see:
```
Using Firefox with VPN bypass (firejail)
Using existing Firefox profile: /home/jin23/.mozilla/firefox/i07xqr33.MAM-Scraper
Already logged in - no authentication needed
✓ Authentication successful!
```

### Step 3: Run the Scraper

Now you can run the scraper normally:

```bash
python main.py --test-mode
```

## Configuration

The `.env` file is configured as:

```env
LOGIN_MODE=cookies                    # Use saved cookies
FIREFOX_PROFILE_PATH=/home/jin23/.mozilla/firefox/i07xqr33.MAM-Scraper
USE_VPN_BYPASS=True                   # Use firejail wrapper
```

## Switching Between Modes

### Use VPN Bypass (Default)
```env
USE_VPN_BYPASS=True
```

### Use Regular Firefox (No VPN Bypass)
```env
USE_VPN_BYPASS=False
```

### Use Form Login Instead of Cookies
```env
LOGIN_MODE=form
MAM_USERNAME=your_username
MAM_PASSWORD=your_password
USE_VPN_BYPASS=True  # Still bypass VPN for form login
```

## Network Verification

To verify the scraper is bypassing VPN:

1. Check your VPN IP:
```bash
curl https://api.ipify.org
```

2. Run the scraper and watch the logs - it should connect successfully to MyAnonamouse even though you're on VPN

3. The wrapper uses `192.168.100.199` which is your direct ethernet IP (not VPN IP)

## Troubleshooting

### Authentication Fails
```bash
# Re-login to update cookies
./login-to-profile.sh
```

### Firejail Not Found
```bash
# Install firejail
sudo dnf install firejail  # Fedora
# or
sudo apt install firejail  # Ubuntu/Debian
```

### Network Interface Not Found
If `enp2s0` doesn't exist on your system:
1. Find your network interface:
```bash
ip addr show
```
2. Update `firefox-no-vpn-wrapper.sh` with the correct interface name
3. Update `login-to-profile.sh` with the same interface

### Wrong IP Address
If `192.168.100.199` is not your IP:
1. Check your ethernet IP:
```bash
ip addr show enp2s0
```
2. Update both scripts with your correct IP

## Files Created

- `firefox-no-vpn-wrapper.sh` - Wrapper script for Playwright
- `login-to-profile.sh` - Helper to log into MAM in the profile
- `i07xqr33.MAM-Scraper/` - Firefox profile directory (in ~/.mozilla/firefox/)
- Updated `auth.py` - Uses wrapper when USE_VPN_BYPASS=True
- Updated `config.py` - Added USE_VPN_BYPASS setting

## Security Notes

- The MAM-Scraper profile is separate from your regular browsing
- Cookies are stored locally in the Firefox profile
- The `.env` file (containing credentials if using form mode) is in .gitignore
- Profile directory is in your home folder (not in git repo)

## Comparison with firefox-no-vpn

| Feature | firefox-no-vpn | MAM Scraper |
|---------|---------------|-------------|
| Profile | VPNBypass | MAM-Scraper |
| Launch method | Manual shell alias | Automated by Playwright |
| VPN bypass | firejail | Same (firejail) |
| Network config | enp2s0, 192.168.100.199 | Same |
| Purpose | General browsing | Dedicated scraping |

## Advanced: Customize Network Settings

Edit `firefox-no-vpn-wrapper.sh` to change network settings:

```bash
#!/bin/bash
# Example: Different network interface or IP
exec firejail --net=eth0 --ip=192.168.1.100 --dns=1.1.1.1 firefox "$@"
```

Then update `login-to-profile.sh` with the same settings.
