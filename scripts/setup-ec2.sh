#!/bin/bash

# Initial EC2 Setup Script for Flask Backend
# Run this script on your EC2 instance to set up the environment

set -e

echo "================================================"
echo "   Flask Backend - EC2 Initial Setup"
echo "================================================"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Update system
echo_info "Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install Python and dependencies
echo_info "Installing Python and build tools..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    libssl-dev \
    libffi-dev \
    git \
    curl \
    wget

# Verify installations
echo_info "Verifying installations..."
python3 --version
pip3 --version
git --version

# Set up application directory
APP_DIR="${HOME}/pdf-summariser-microservice"
echo_info "Setting up application directory: $APP_DIR"

if [ ! -d "$APP_DIR" ]; then
    echo_info "Cloning repository..."
    cd ~
    git clone https://github.com/Harsha072/pdf-summariser-microservice.git
else
    echo_warn "Repository already exists. Pulling latest changes..."
    cd "$APP_DIR"
    git pull
fi

cd "$APP_DIR"

# Configure Git
echo_info "Configuring Git..."
git config pull.rebase false
git config --global user.email "ci-cd@example.com"
git config --global user.name "CI/CD Bot"

# Create virtual environment for Flask app
FLASK_DIR="$APP_DIR/flask-api"
echo_info "Creating virtual environment in $FLASK_DIR..."
cd "$FLASK_DIR"

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo_info "Virtual environment created"
else
    echo_warn "Virtual environment already exists"
fi

# Activate and install dependencies
echo_info "Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r app/requirements.txt
deactivate

# Create necessary directories
echo_info "Creating application directories..."
mkdir -p "$FLASK_DIR/logs"
mkdir -p "$FLASK_DIR/temp"
mkdir -p "$FLASK_DIR/temp_uploads"
mkdir -p "$FLASK_DIR/app/data/citation_cache"

# Set permissions
echo_info "Setting directory permissions..."
chmod -R 755 "$APP_DIR"

# Create systemd service
echo_info "Setting up systemd service..."
sudo tee /etc/systemd/system/flask-api.service > /dev/null <<EOF
[Unit]
Description=Flask API Service for PDF Summariser
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$FLASK_DIR
Environment="PATH=$FLASK_DIR/venv/bin"
ExecStart=$FLASK_DIR/venv/bin/python app/main.py
Restart=always
RestartSec=10
StandardOutput=append:$FLASK_DIR/logs/app.log
StandardError=append:$FLASK_DIR/logs/error.log

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
echo_info "Enabling Flask API service..."
sudo systemctl daemon-reload
sudo systemctl enable flask-api

# Configure firewall
echo_info "Configuring firewall..."
sudo ufw allow 22/tcp
sudo ufw allow 5000/tcp
echo_info "Firewall rules added (not enabled yet)"

# Create .env template
if [ ! -f "$FLASK_DIR/.env" ]; then
    echo_info "Creating .env template..."
    cat > "$FLASK_DIR/.env" <<EOF
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=$(openssl rand -hex 32)

# Redis Configuration (update with your values)
REDIS_HOST=localhost
REDIS_PORT=6379

# Firebase Configuration
# Add your Firebase credentials path here
FIREBASE_CREDENTIALS_PATH=app/credentials/firebase-adminsdk.json

# API Configuration
CORS_ORIGINS=*
EOF
    echo_info ".env file created. Please update with your actual values!"
else
    echo_warn ".env file already exists"
fi

# Make deployment script executable
if [ -f "$APP_DIR/scripts/deploy-backend.sh" ]; then
    chmod +x "$APP_DIR/scripts/deploy-backend.sh"
    echo_info "Deployment script made executable"
fi

# Display summary
echo "================================================"
echo_info "✅ Initial setup completed successfully!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Update the .env file with your actual configuration:"
echo "   nano $FLASK_DIR/.env"
echo ""
echo "2. Add your Firebase credentials to:"
echo "   $FLASK_DIR/app/credentials/firebase-adminsdk.json"
echo ""
echo "3. Start the Flask API service:"
echo "   sudo systemctl start flask-api"
echo ""
echo "4. Check service status:"
echo "   sudo systemctl status flask-api"
echo ""
echo "5. View logs:"
echo "   sudo journalctl -u flask-api -f"
echo ""
echo "6. Test the API:"
echo "   curl http://localhost:5000/health"
echo ""
echo "7. Set up GitHub secrets for CI/CD (see docs/CI-CD-SETUP.md)"
echo ""
echo "================================================"
