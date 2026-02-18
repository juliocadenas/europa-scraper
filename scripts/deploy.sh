#!/bin/bash

# ==============================================================================
# Automated Deployment Script - EUROPA SCRAPER (servidor01)
# ==============================================================================

set -e

# If GITHUB_WORKSPACE is set, we are running inside an Action
if [ -n "$GITHUB_WORKSPACE" ]; then
    PROJECT_DIR="$GITHUB_WORKSPACE"
    echo "🤖 Running inside GitHub Action Runner"
else
    # Manual execution fallback
    PROJECT_DIR="/opt/docuscraper"
    echo "👤 Running manual deployment"
fi

echo "⏳ Starting automated deployment at $(date)"
cd "$PROJECT_DIR"

# 1. Pull latest changes
echo "⬇️ Pulling latest changes from main..."
git pull origin main

# 2. Ensure results/logs directories exist
mkdir -p results logs client
touch courses.db counties.db

# 3. Build and Restart Container
# Check if current user can run docker without sudo
if docker ps >/dev/null 2>&1; then
    DOCKER_CMD="docker"
    DOCKER_COMPOSE_CMD="docker compose"
else
    echo "⚠️ Warning: 'docker' command failed. If you need sudo, please ensure the user is in the 'docker' group."
    # We'll try to use docker anyway, as the user mentioned handled it in their session
    DOCKER_CMD="docker"
    DOCKER_COMPOSE_CMD="docker compose"
fi

echo "🏗️ Rebuilding and restarting container..."
$DOCKER_COMPOSE_CMD up -d --build

# 4. Cleanup old images
echo "🧹 Cleaning up dangling images..."
docker image prune -f

echo "✅ Deployment successful at $(date)"
