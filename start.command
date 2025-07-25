#!/bin/bash
cd "$(dirname "$0")"

echo "🤖 MedVerify Bot v2.4.1 - Starting..."

if [ ! -f .env ]; then
    echo "❌ ERROR: .env file not found!"
    echo "Please copy example.env to .env and configure your tokens."
    echo "To show hidden files: Cmd+Shift+."
    read -p "Press Enter to exit..."
    exit 1
fi

if ! grep -q "^TELEGRAM_BOT_TOKEN=." .env; then
    echo "❌ ERROR: TELEGRAM_BOT_TOKEN not configured in .env"
    echo "Please edit .env file and set your bot token."
    read -p "Press Enter to exit..."
    exit 1
fi

if ! grep -q "^OPENAI_API_KEY=." .env; then
    echo "❌ ERROR: OPENAI_API_KEY not configured in .env"
    echo "Please edit .env file and set your OpenAI API key."
    read -p "Press Enter to exit..."
    exit 1
fi

echo "📦 Validating configuration..."
if command -v python3 &> /dev/null; then
    python3 validate_config.py
else
    python validate_config.py
fi

if [ $? -ne 0 ]; then
    echo "❌ Configuration validation failed. Please check .env file."
    read -p "Press Enter to exit..."
    exit 1
fi

if [ ! -d .venv ]; then
    echo "📦 Creating virtual environment..."
    if command -v python3 &> /dev/null; then
        python3 -m venv .venv
    else
        python -m venv .venv
    fi
    echo "📦 Installing dependencies..."
    ./.venv/bin/pip install -r requirements.txt
else
    echo "⚡ Using existing virtual environment..."
    ./.venv/bin/pip install -r requirements.txt --quiet
fi

echo "🚀 Starting MedVerify Bot v2.4.1..."
./.venv/bin/python start.py
