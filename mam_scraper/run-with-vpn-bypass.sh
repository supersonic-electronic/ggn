#!/bin/bash
# Wrapper script to run Python scripts with VPN bypass
# This runs the entire Python process inside firejail's network namespace
# so that Firefox launched by Playwright inherits the bypassed network

# Usage: ./run-with-vpn-bypass.sh python script.py [args...]

exec firejail --noprofile --net=enp2s0 --ip=192.168.100.201 --dns=8.8.8.8 "$@"
