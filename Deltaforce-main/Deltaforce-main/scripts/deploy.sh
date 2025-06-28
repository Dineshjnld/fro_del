#!/bin/bash
# CCTNS Copilot Engine Deployment Script

set -e

echo "🚀 Deploying CCTNS Copilot Engine..."

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "❌ This script should not be run as root"
   exit 1
fi

# Create directories
echo "📁 Creating directories..."
mkdir -p logs reports temp models_cache data/exports

# Install system dependencies
echo "📦 Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y python3-dev python3-pip ffmpeg libsm6 libxext6 libfontconfig1 libxrender1

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip install -r requirements.txt

# Download models
echo "🤖 Downloading AI models..."
python scripts/download_models.py

# Setup database (if connection string provided)
if [ ! -z "$ORACLE_CONNECTION_STRING" ]; then
    echo "🗄️ Setting up database..."
    python scripts/setup_database.py
fi

# Create systemd service
echo "⚙️ Creating systemd service..."
sudo tee /etc/systemd/system/cctns-copilot.service > /dev/null <<EOL
[Unit]
Description=CCTNS Copilot Engine
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/python run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOL

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable cctns-copilot
sudo systemctl start cctns-copilot

echo "✅ Deployment completed!"
echo "🌐 Service running at: http://localhost:8000"
echo "📊 Health check: http://localhost:8000/api/health"
echo "📋 Service status: sudo systemctl status cctns-copilot"