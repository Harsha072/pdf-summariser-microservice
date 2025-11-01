#!/bin/bash

# EC2 Storage Optimization Script for Flask Backend
# This script removes unnecessary files and optimizes storage usage

set -e

echo "================================================"
echo "   EC2 Storage Optimization Script"
echo "================================================"

APP_DIR="${APP_DIR:-/home/ubuntu/pdf-summariser-microservice}"
FLASK_DIR="$APP_DIR/flask-api"

cd "$FLASK_DIR"

echo "📊 Storage usage BEFORE cleanup:"
du -sh .

echo ""
echo "🧹 Starting cleanup..."

# 1. Remove Python cache files
echo "Removing Python cache files..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true
find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

# 2. Remove test coverage files
echo "Removing test coverage files..."
rm -rf htmlcov/ .coverage .pytest_cache/ 2>/dev/null || true

# 3. Remove test files (not needed in production)
echo "Removing test files..."
rm -rf tests/ 2>/dev/null || true
rm -f pytest.ini requirements-test.txt BACKEND_TESTS_README.md 2>/dev/null || true

# 4. Remove Docker files (if using systemd/direct deployment)
echo "Removing Docker files..."
rm -f Dockerfile .dockerignore 2>/dev/null || true

# 5. Clean up temporary files
echo "Cleaning temporary files..."
rm -rf app/temp/* 2>/dev/null || true
rm -rf app/temp_uploads/* 2>/dev/null || true
find app/logs/ -name "*.log" -mtime +7 -delete 2>/dev/null || true

# 6. Remove unused modules (citation_checker if not used)
echo "Checking for unused modules..."
if ! grep -r "citation_checker" app/main.py app/config.py app/rag_pipeline.py 2>/dev/null; then
    echo "  - citation_checker.py not imported, removing..."
    rm -f app/citation_checker.py 2>/dev/null || true
fi

# 7. Clean pip cache
echo "Cleaning pip cache..."
rm -rf ~/.cache/pip/* 2>/dev/null || true

# 8. Remove chroma_db if exists and not used
if [ -d "chroma_db" ] && [ ! -s "chroma_db/chroma.sqlite3" ]; then
    echo "Removing empty chroma_db..."
    rm -rf chroma_db/ 2>/dev/null || true
fi

# 9. Clean apt cache (system-wide)
echo "Cleaning apt cache..."
sudo apt-get clean 2>/dev/null || true
sudo apt-get autoclean 2>/dev/null || true

# 10. Remove old log files
echo "Removing old log files..."
find /var/log -name "*.gz" -mtime +30 -delete 2>/dev/null || true
sudo journalctl --vacuum-time=7d 2>/dev/null || true

echo ""
echo "📊 Storage usage AFTER cleanup:"
du -sh .

echo ""
echo "💾 System disk usage:"
df -h /

echo ""
echo "✅ Cleanup completed successfully!"
echo ""
echo "💡 Additional optimization tips:"
echo "   1. Run: sudo apt-get autoremove"
echo "   2. Setup log rotation: sudo nano /etc/logrotate.d/flask-api"
echo "   3. Clear old journal logs: sudo journalctl --vacuum-size=100M"
