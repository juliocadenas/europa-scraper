#!/bin/bash

echo "=== Checking Server Status ==="

# Check if server is running
echo -e "\n1. Docker container status:"
sudo docker ps | grep europa-scraper

# Check server logs for Cordis API calls
echo -e "\n2. Recent Cordis API logs:"
sudo docker logs europa-scraper-prod 2>&1 | grep -i "cordis" | tail -20

# Check if git is up to date
echo -e "\n3. Git status:"
git log --oneline -5

# Check current commit
echo -e "\n4. Current commit:"
git rev-parse HEAD

echo -e "\n=== End of diagnostics ==="
