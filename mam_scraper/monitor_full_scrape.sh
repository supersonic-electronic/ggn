#!/bin/bash
echo "Full Scrape Monitor - Will check every 5 minutes"
echo "Press Ctrl+C to stop monitoring (scrape will continue)"
echo ""

while true; do
    echo "=================================================="
    date
    echo "=================================================="
    
    # Check if process is still running
    if [ -f test_full_scrape.pid ]; then
        PID=$(cat test_full_scrape.pid)
        if ps -p $PID > /dev/null; then
            echo "✅ Scraper is running (PID: $PID)"
        else
            echo "❌ Scraper has stopped"
            break
        fi
    fi
    
    # Count total torrents scraped
    if [ -f mam.db ]; then
        TOTAL=$(sqlite3 mam.db "SELECT COUNT(*) FROM mam_torrents" 2>/dev/null || echo "0")
        echo "Total torrents scraped: $TOTAL"
    fi
    
    # Show last few log lines
    echo ""
    echo "Recent activity:"
    tail -n 5 test_full_scrape.log | grep -E "(Saved torrent|next page|Page|No more pages)" || tail -n 3 test_full_scrape.log
    
    echo ""
    echo "Next check in 5 minutes..."
    echo ""
    
    # Check if complete
    if grep -q "Full scrape complete" test_full_scrape.log; then
        echo "✅ SCRAPE COMPLETED!"
        break
    fi
    
    sleep 300  # 5 minutes
done
