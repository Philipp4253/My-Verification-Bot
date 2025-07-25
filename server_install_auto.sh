#!/bin/bash

# MedVerify Bot v2.4.1 - Automatic Production Installation
# Requires: sudo ./server_install_auto.sh

set -e  # Exit on any error

echo "🤖 MedVerify Bot v2.4.1 - Production Auto-Installer"
echo "=================================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ This script must be run as root: sudo ./server_install_auto.sh"
    exit 1
fi

# Variables
PROJECT_DIR="/opt/medverify_bot"
SERVICE_NAME="medverify-bot"
BACKUP_DIR="/var/backups/medverify-bot"
CURRENT_USER=${SUDO_USER:-$USER}

echo "📍 Installing to: $PROJECT_DIR"
echo "👤 User: $CURRENT_USER"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup existing installation if exists
if [ -d "$PROJECT_DIR" ]; then
    BACKUP_FILE="$BACKUP_DIR/medverify-bot-backup-$(date +%Y%m%d_%H%M%S).tar.gz"
    echo "📂 Creating backup: $BACKUP_FILE"
    tar -czf "$BACKUP_FILE" -C /opt medverify_bot
    
    # Stop service if running
    if systemctl is-active --quiet $SERVICE_NAME; then
        echo "⏸️  Stopping existing service..."
        systemctl stop $SERVICE_NAME
    fi
fi

# Install Python 3.12 if needed
if ! command -v python3.12 &> /dev/null; then
    echo "📦 Installing Python 3.12..."
    apt update
    apt install -y software-properties-common
    add-apt-repository -y ppa:deadsnakes/ppa
    apt update
    apt install -y python3.12 python3.12-venv python3.12-pip
fi

# Create project directory
echo "📁 Setting up project directory..."
mkdir -p "$PROJECT_DIR"
cp -r . "$PROJECT_DIR/"
cd "$PROJECT_DIR"

# Set ownership
chown -R $CURRENT_USER:$CURRENT_USER "$PROJECT_DIR"

# Setup .env if not exists or restore from backup
if [ ! -f .env ]; then
    if [ -f "$BACKUP_DIR"/../.env ]; then
        echo "🔄 Restoring .env from backup..."
        cp "$BACKUP_DIR"/../.env .env
    else
        echo "📝 Creating .env from example..."
        cp example.env .env
        echo "⚠️  Please configure .env file with your tokens:"
        echo "   nano $PROJECT_DIR/.env"
    fi
fi

# Restore database if exists
if [ -f "$BACKUP_DIR/../sqlite.db" ]; then
    echo "🔄 Restoring database from backup..."
    cp "$BACKUP_DIR/../sqlite.db" sqlite.db
    chown $CURRENT_USER:$CURRENT_USER sqlite.db
fi

# Setup virtual environment as user
echo "📦 Setting up virtual environment..."
sudo -u $CURRENT_USER python3.12 -m venv .venv
sudo -u $CURRENT_USER ./.venv/bin/pip install -r requirements.txt

# Validate configuration
echo "📦 Validating configuration..."
sudo -u $CURRENT_USER ./.venv/bin/python validate_config.py

# Create systemd service
echo "🔧 Creating systemd service..."
cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=MedVerify Bot v2.4.1 Multi-Group Edition
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/.venv/bin
ExecStart=$PROJECT_DIR/.venv/bin/python start.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
echo "🚀 Starting service..."
systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl start $SERVICE_NAME

# Check status
sleep 3
if systemctl is-active --quiet $SERVICE_NAME; then
    echo "✅ MedVerify Bot v2.4.1 installed and running successfully!"
    echo ""
    echo "📊 Management commands:"
    echo "   systemctl status $SERVICE_NAME"
    echo "   systemctl restart $SERVICE_NAME"
    echo "   journalctl -u $SERVICE_NAME -f"
    echo ""
    echo "📂 Project location: $PROJECT_DIR"
    echo "🔧 Edit config: nano $PROJECT_DIR/.env"
else
    echo "❌ Service failed to start. Check logs:"
    echo "   journalctl -u $SERVICE_NAME -n 20"
    exit 1
fi

# Cleanup old backups (keep last 10)
echo "🧹 Cleaning old backups..."
cd "$BACKUP_DIR" && ls -t medverify-bot-backup-*.tar.gz 2>/dev/null | tail -n +11 | xargs -r rm

echo "🎉 Installation complete!"
