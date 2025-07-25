#!/bin/bash

echo "🤖 MedVerify Bot v2.4.1 - Server Setup"
echo "====================================="

# Проверяем Python3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

# Создаем .env если не существует
if [ ! -f .env ]; then
    echo "📝 Creating .env from example..."
    cp example.env .env
    echo "✅ Created .env file. Please edit it with your configuration:"
    echo "   nano .env"
    echo ""
    read -p "Press Enter after you've configured .env file..."
fi

# Валидация
echo "📦 Validating configuration..."
python3 validate_config.py
if [ $? -ne 0 ]; then
    echo "❌ Configuration validation failed. Please check .env file."
    exit 1
fi

# Виртуальное окружение
if [ ! -d .venv ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
    echo "📦 Installing dependencies..."
    ./.venv/bin/pip install -r requirements.txt
else
    echo "⚡ Using existing virtual environment..."
    ./.venv/bin/pip install -r requirements.txt --quiet
fi

echo "🚀 Starting MedVerify Bot v2.4.1..."
echo "   (Press Ctrl+C to stop)"
./.venv/bin/python start.py
