#!/bin/bash

echo "=== Checking latest Cordis API execution ==="

# Get the most recent logs
sudo docker logs europa-scraper-prod --tail 100 | grep -A 3 -B 3 "Translated\|Cordis API returned"

echo ""
echo "=== Checking if server is updated ==="
cd /opt/docuscraper
git log --oneline -3
