#!/bin/bash

# Flask Backend Deployment Script for EC2
# This script handles the deployment of the Flask API on the EC2 instance

set -e  # Exit on any error

echo "================================================"
echo "   Flask Backend Deployment Script"
echo "================================================"

# Configuration
APP_DIR="${APP_DIR:-/home/ubuntu/pdf-summariser-microservice}"
FLASK_DIR="$APP_DIR/flask-api"
VENV_DIR="$FLASK_DIR/venv"
SERVICE_NAME="flask-api"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Navigate to application directory
echo_info "Navigating to application directory: $APP_DIR"
cd "$APP_DIR" || { echo_error "Failed to navigate to $APP_DIR"; exit 1; }

# Pull latest changes from Git
echo_info "Pulling latest code from repository..."
git fetch origin
git reset --hard origin/$(git rev-parse --abbrev-ref HEAD)
echo_info "Code updated successfully"

# Navigate to Flask API directory
cd "$FLASK_DIR" || { echo_error "Failed to navigate to $FLASK_DIR"; exit 1; }

# Create or activate virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo_info "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
else
    echo_info "Virtual environment already exists"
fi

# Activate virtual environment
echo_info "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo_info "Upgrading pip..."
pip install --upgrade pip --quiet

# Install dependencies
echo_info "Installing application dependencies..."
pip install -r app/requirements.txt --quiet
echo_info "Dependencies installed successfully"

# Clean up unnecessary files to save disk space
echo_info "Cleaning up unnecessary files..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
rm -rf htmlcov/ .coverage .pytest_cache/ tests/ 2>/dev/null || true
rm -rf chroma_db/ 2>/dev/null || true
echo_info "Cleanup completed"

# Set environment variables (if .env file exists)
if [ -f "$FLASK_DIR/.env" ]; then
    echo_info "Loading environment variables from .env file"
    export $(cat "$FLASK_DIR/.env" | grep -v '^#' | xargs)
fi

# Check if service exists and restart
echo_info "Restarting Flask application..."

if systemctl list-units --full -all | grep -Fq "$SERVICE_NAME.service"; then
    # Using systemd
    echo_info "Restarting service using systemd..."
    sudo systemctl restart "$SERVICE_NAME"
    sudo systemctl status "$SERVICE_NAME" --no-pager
elif command -v supervisorctl &> /dev/null; then
    # Using supervisor
    echo_info "Restarting service using supervisor..."
    sudo supervisorctl restart "$SERVICE_NAME"
    sudo supervisorctl status "$SERVICE_NAME"
else
    # Manual restart
    echo_warn "No service manager found. Attempting manual restart..."
    pkill -f "python.*main.py" || true
    sleep 2
    nohup python app/main.py > logs/app.log 2>&1 &
    echo_info "Application started manually"
fi

# Health check
echo_info "Performing health check..."
sleep 3

if curl -f http://localhost:5000/health &> /dev/null; then
    echo_info "✅ Health check passed - Application is running"
else
    echo_warn "Health check endpoint not responding (this may be normal if /health endpoint doesn't exist)"
fi

# Show recent logs
echo_info "Recent application logs:"
if [ -f "logs/app.log" ]; then
    tail -n 20 logs/app.log
else
    echo_warn "No log file found at logs/app.log"
fi

echo_info "================================================"
echo_info "✅ Deployment completed successfully!"
echo_info "================================================"

deactivate
