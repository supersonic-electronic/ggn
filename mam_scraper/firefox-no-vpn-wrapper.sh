#!/bin/bash
# Firefox wrapper script for Playwright that bypasses VPN using firejail
# This script is called by Playwright instead of the regular Firefox binary

# Firejail network configuration (using different IP than firefox-no-vpn.sh)
# Uses direct ethernet connection bypassing VPN
exec firejail --net=enp2s0 --ip=192.168.100.200 --dns=8.8.8.8 firefox "$@"
