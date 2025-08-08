import os
from typing import List

class Config:
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

    # Database - Render PostgreSQL
    DATABASE_URL = os.getenv('DATABASE_URL')

    # Security
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')

    # Hardcoded Admin User IDs - Add your admin IDs here
    HARDCODED_ADMIN_IDS = [
        7527795504,  # Your main admin ID - REPLACE WITH YOUR ACTUAL TELEGRAM USER ID
        # 123456789,  # Add more admin IDs here if needed
        # 987654321,  # Another admin ID
    ]

    # Environment admin IDs (optional fallback)
    ENV_ADMIN_IDS = []
    try:
        env_ids = os.getenv('ADMIN_USER_IDS', '')
        if env_ids:
            ENV_ADMIN_IDS = [int(uid.strip()) for uid in env_ids.split(',') if uid.strip()]
    except (ValueError, AttributeError):
        ENV_ADMIN_IDS = []

    # Combined admin list (hardcoded takes priority)
    ADMIN_USER_IDS = list(set(HARDCODED_ADMIN_IDS + ENV_ADMIN_IDS))

    # Rate limiting
    MAX_REQUESTS_PER_MINUTE = 30

    # GitHub API
    GITHUB_API_BASE = 'https://api.github.com'

    @classmethod
    def validate(cls):
        required_vars = ['TELEGRAM_BOT_TOKEN', 'DATABASE_URL', 'ENCRYPTION_KEY']
        missing = [var for var in required_vars if not getattr(cls, var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {missing}")

        if not cls.ADMIN_USER_IDS:
            raise ValueError("No admin user IDs specified (check hardcoded admin IDs in config.py)")

    @classmethod
    def is_admin(cls, user_id: int) -> bool:
        """Check if user is an admin"""
        return user_id in cls.ADMIN_USER_IDS

    @classmethod
    def get_admin_count(cls) -> int:
        """Get total number of admins"""
        return len(cls.ADMIN_USER_IDS)
