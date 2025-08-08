import functools
import time
from typing import Dict, Callable
from collections import defaultdict
from telegram import Update
from telegram.ext import ContextTypes
from app.config import Config
from app.database import Database
import logging

logger = logging.getLogger(__name__)

# Rate limiting storage
user_requests = defaultdict(list)

def rate_limit(max_requests: int = Config.MAX_REQUESTS_PER_MINUTE, window: int = 60):
    """Rate limiting decorator"""
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id = update.effective_user.id
            current_time = time.time()

            # Clean old requests
            user_requests[user_id] = [req_time for req_time in user_requests[user_id] 
                                    if current_time - req_time < window]

            # Check rate limit
            if len(user_requests[user_id]) >= max_requests:
                await update.message.reply_text(
                    "⚠️ **Rate limit exceeded!**\n"
                    f"Please wait before making more requests. "
                    f"Maximum {max_requests} requests per minute allowed.",
                    parse_mode='Markdown'
                )
                return

            # Add current request
            user_requests[user_id].append(current_time)

            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator

def require_authorization(func: Callable):
    """Authorization decorator"""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        db = Database()

        user = await db.get_user(user_id)
        if not user:
            await update.message.reply_text(
                "❌ **Access Denied**\n"
                "You are not registered. Please contact an administrator.",
                parse_mode='Markdown'
            )
            return

        if not user['is_authorized']:
            await update.message.reply_text(
                "❌ **Access Denied**\n"
                "You are not authorized to use this bot. Please contact an administrator.",
                parse_mode='Markdown'
            )
            return

        return await func(update, context, *args, **kwargs)
    return wrapper

def require_admin(func: Callable):
    """Admin authorization decorator"""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id

        if user_id not in Config.ADMIN_USER_IDS:
            await update.message.reply_text(
                "❌ **Admin Access Required**\n"
                "This command requires administrator privileges.",
                parse_mode='Markdown'
            )
            return

        return await func(update, context, *args, **kwargs)
    return wrapper

def require_active_api(func: Callable):
    """Require active GitHub API decorator"""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        db = Database()

        active_api = await db.get_active_api(user_id)
        if not active_api:
            await update.message.reply_text(
                "❌ **No Active GitHub API**\n"
                "Please add and load a GitHub API first using `/add_api` and `/load_api`.",
                parse_mode='Markdown'
            )
            return

        context.user_data['active_api'] = active_api
        return await func(update, context, *args, **kwargs)
    return wrapper
