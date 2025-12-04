#!/bin/bash
# Firefox wrapper script for Playwright that bypasses VPN using firejail
# This script is called by Playwright instead of the regular Firefox binary

# Firejail network configuration (using IP .201 for Playwright automation)
# firefox-no-vpn uses .199, login-to-profile.sh uses .200, this uses .201
# Uses direct ethernet connection bypassing VPN
# Using --noprofile to minimize sandboxing and allow Playwright communication
exec firejail --noprofile --net=enp2s0 --ip=192.168.100.201 --dns=8.8.8.8 firefox "$@"
