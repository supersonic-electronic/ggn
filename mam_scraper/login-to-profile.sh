#!/bin/bash
# Helper script to log into MyAnonamouse in the MAM-Scraper Firefox profile
# Run this ONCE before using the scraper in cookies mode

echo "================================================"
echo "  MyAnonamouse Login Helper"
echo "================================================"
echo ""
echo "This will open Firefox with VPN bypass so you can"
echo "log into MyAnonamouse in the MAM-Scraper profile."
echo ""
echo "Steps:"
echo "1. Firefox will open with the MAM-Scraper profile"
echo "2. Log into MyAnonamouse with your credentials"
echo "3. Close Firefox when done"
echo "4. Run the scraper - it will reuse your cookies!"
echo ""
echo "Network: Bypassing VPN via firejail"
echo "Profile: MAM-Scraper"
echo ""
read -p "Press Enter to open Firefox..."

# Launch Firefox with VPN bypass using the MAM-Scraper profile
# Using IP .200 (different from firefox-no-vpn which uses .199)
firejail --net=enp2s0 --ip=192.168.100.200 --dns=8.8.8.8 \
    firefox -P MAM-Scraper --new-window "https://www.myanonamouse.net"

echo ""
echo "✓ Firefox closed"
echo "If you logged in successfully, you can now run the scraper!"
echo ""
echo "Test with:"
echo "  source .venv/bin/activate"
echo "  python auth.py"
echo ""
