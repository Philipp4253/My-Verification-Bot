#!/usr/bin/env python3
"""
Валидация конфигурации MedVerify Bot

Проверяет:
- Формат токенов
- Реальные подключения к API
- Выводит понятные ошибки
"""

import os
import re
import sys
import requests
import json


def validate_env_file():
    """Проверяем наличие и формат .env файла"""
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        print("Please create .env file with your configuration")
        return False

    # Загружаем переменные
    env_vars = {}
    with open('.env', 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()

    # Проверяем обязательные поля
    required_fields = ['TELEGRAM_BOT_TOKEN', 'OPENAI_API_KEY']

    for field in required_fields:
        if field not in env_vars or not env_vars[field]:
            print(f"❌ Missing or empty {field} in .env file")
            return False

    return env_vars


def validate_telegram_token(token):
    """Проверяем формат и работоспособность Telegram токена"""
    # Проверка формата
    if not re.match(r'^\d+:[a-zA-Z0-9_-]+$', token):
        print("❌ Invalid Telegram bot token format")
        print("   Should be like: 123456789:ABCdefGHI...")
        return False

    # Проверка API
    try:
        response = requests.get(f'https://api.telegram.org/bot{token}/getMe', timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                bot_info = data.get('result', {})
                print(f"✅ Bot connected successfully: @{bot_info.get('username', 'unknown')}")
                return True
            else:
                print("❌ Invalid bot token (API returned error)")
                return False
        elif response.status_code == 401:
            print("❌ Invalid bot token (401 Unauthorized)")
            return False
        else:
            print(f"❌ Telegram API error: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error connecting to Telegram: {e}")
        return False


def validate_openai_key(api_key):
    """Проверяем формат и работоспособность OpenAI ключа"""
    # Проверка формата
    if not api_key.startswith('sk-') or len(api_key) < 40:
        print("❌ Invalid OpenAI API key format")
        print("   Should start with 'sk-' and be longer")
        return False

    # Проверка API
    try:
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        response = requests.get('https://api.openai.com/v1/models', headers=headers, timeout=10)
        if response.status_code == 200:
            print("✅ OpenAI API key is valid")
            return True
        elif response.status_code == 401:
            print("❌ Invalid OpenAI API key (401 Unauthorized)")
            return False
        elif response.status_code == 429:
            print("❌ OpenAI API rate limit exceeded")
            return False
        else:
            print(f"❌ OpenAI API error: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error connecting to OpenAI: {e}")
        return False


def validate_admin_ids(admin_ids):
    """Проверяем формат Admin User IDs"""
    if not admin_ids or not admin_ids.strip():
        print("✅ Admin IDs not specified (no global admins)")
        return True

    try:
        ids = [int(x.strip()) for x in admin_ids.split(',') if x.strip()]
        for user_id in ids:
            if user_id <= 0:
                print(f"❌ Invalid admin user ID: {user_id} (should be positive)")
                return False
        print(f"✅ Admin IDs format is valid ({len(ids)} admins)")
        return True
    except ValueError:
        print("❌ Invalid Admin User IDs format")
        print("   Should be comma-separated numbers: 123456789,987654321")
        return False


def main():
    print("🔍 MedVerify Bot - Configuration Validation")
    print("=" * 50)

    # Валидация файла
    env_vars = validate_env_file()
    if not env_vars:
        sys.exit(1)

    validation_failed = False

    # Проверяем каждое поле
    print("\n🔍 Validating configuration...")

    if not validate_telegram_token(env_vars['TELEGRAM_BOT_TOKEN']):
        validation_failed = True

    if not validate_openai_key(env_vars['OPENAI_API_KEY']):
        validation_failed = True

    if not validate_admin_ids(env_vars.get('ADMIN_USER_IDS', '')):
        validation_failed = True

    if validation_failed:
        print("\n❌ Configuration validation failed!")
        print("Please fix the issues above before running the bot.")
        sys.exit(1)
    else:
        print("\n✅ All configuration checks passed!")
        print("Bot is ready to start.")


if __name__ == "__main__":
    main()
