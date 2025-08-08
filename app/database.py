import asyncio
from datetime import datetime
from typing import List, Dict, Optional
import logging
import traceback
import base64
from cryptography.fernet import Fernet
import os

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from psycopg2 import pool
    PSYCOPG2_AVAILABLE = True
except ImportError as e:
    logging.error(f"psycopg2 not available: {e}")
    PSYCOPG2_AVAILABLE = False

from app.config import Config

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        if not PSYCOPG2_AVAILABLE:
            raise ImportError("psycopg2 client not available")

        try:
            logger.info(f"🔌 Connecting to Render PostgreSQL...")

            # Get database URL from config
            self.database_url = Config.DATABASE_URL

            # Create connection pool
            self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=20,
                dsn=self.database_url,
                cursor_factory=RealDictCursor
            )

            logger.info("✅ Render PostgreSQL connection pool created successfully")

            # Initialize encryption
            self._init_encryption()

            # Test connection
            self._test_connection()

        except Exception as e:
            logger.error(f"❌ Failed to create PostgreSQL connection: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def _init_encryption(self):
        """Initialize encryption cipher"""
        try:
            # Create cipher from config key
            key = Config.ENCRYPTION_KEY.encode()
            key = base64.urlsafe_b64encode(key.ljust(32)[:32])
            self.cipher = Fernet(key)
            logger.debug("✅ Encryption initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize encryption: {e}")
            raise

    def _encrypt_token(self, token: str) -> str:
        """Encrypt GitHub token"""
        try:
            encrypted = self.cipher.encrypt(token.encode())
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"❌ Failed to encrypt token: {e}")
            raise

    def _decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt GitHub token"""
        try:
            encrypted_bytes = base64.b64decode(encrypted_token.encode())
            decrypted = self.cipher.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"❌ Failed to decrypt token: {e}")
            raise

    def _get_connection(self):
        """Get a connection from the pool"""
        return self.connection_pool.getconn()

    def _put_connection(self, conn):
        """Return a connection to the pool"""
        self.connection_pool.putconn(conn)

    def _test_connection(self):
        """Test database connection"""
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
                logger.info("✅ Database connection test successful")
                return True
            finally:
                self._put_connection(conn)
        except Exception as e:
            logger.error(f"❌ Database connection test failed: {e}")
            return False

    # User Management
    async def create_user(self, user_id: int, username: str) -> bool:
        try:
            logger.info(f"👤 Creating user: {user_id} ({username})")

            # Check if user already exists
            existing = await self.get_user(user_id)
            if existing:
                logger.info(f"ℹ️ User {user_id} already exists")
                return True

            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO users (user_id, username, is_authorized, created_at)
                        VALUES (%s, %s, %s, %s)
                    """, (user_id, username, False, datetime.utcnow()))
                    conn.commit()

                logger.info(f"✅ User created successfully: {user_id}")
                return True
            finally:
                self._put_connection(conn)

        except Exception as e:
            logger.error(f"❌ Error creating user {user_id}: {e}")
            return False

    async def get_user(self, user_id: int) -> Optional[Dict]:
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
                    user = cursor.fetchone()
                    if user:
                        user = dict(user)
                        logger.debug(f"👤 User {user_id} found - authorized: {user.get('is_authorized')}")
                    return user
            finally:
                self._put_connection(conn)
        except Exception as e:
            logger.error(f"❌ Error getting user {user_id}: {e}")
            return None

    async def authorize_user(self, user_id: int) -> bool:
        try:
            logger.info(f"🔐 Authorizing user: {user_id}")
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("UPDATE users SET is_authorized = %s WHERE user_id = %s", (True, user_id))
                    conn.commit()
                logger.info(f"✅ User {user_id} authorized successfully")
                return True
            finally:
                self._put_connection(conn)
        except Exception as e:
            logger.error(f"❌ Error authorizing user {user_id}: {e}")
            return False

    async def revoke_user(self, user_id: int) -> bool:
        try:
            logger.info(f"🚫 Revoking user: {user_id}")
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("UPDATE users SET is_authorized = %s WHERE user_id = %s", (False, user_id))
                    conn.commit()
                logger.info(f"✅ User {user_id} revoked successfully")
                return True
            finally:
                self._put_connection(conn)
        except Exception as e:
            logger.error(f"❌ Error revoking user {user_id}: {e}")
            return False

    # GitHub API Management
    async def add_github_api(self, user_id: int, api_name: str, github_token: str, github_username: str) -> bool:
        try:
            logger.info(f"📝 Adding GitHub API '{api_name}' for user {user_id}")

            # Encrypt the token
            encrypted_token = self._encrypt_token(github_token)

            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    # Check if API name already exists for this user
                    cursor.execute("SELECT id FROM github_apis WHERE user_id = %s AND api_name = %s", (user_id, api_name))
                    existing = cursor.fetchone()

                    if existing:
                        # Update existing
                        cursor.execute("""
                            UPDATE github_apis
                            SET github_token = %s, github_username = %s, created_at = %s
                            WHERE user_id = %s AND api_name = %s
                        """, (encrypted_token, github_username, datetime.utcnow(), user_id, api_name))
                        logger.info(f"✅ Updated existing API '{api_name}' for user {user_id}")
                    else:
                        # Insert new
                        cursor.execute("""
                            INSERT INTO github_apis (user_id, api_name, github_token, github_username, is_active, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (user_id, api_name, encrypted_token, github_username, False, datetime.utcnow()))
                        logger.info(f"✅ Added new API '{api_name}' for user {user_id}")

                    conn.commit()
                return True
            finally:
                self._put_connection(conn)

        except Exception as e:
            logger.error(f"❌ Error adding GitHub API: {e}")
            return False

    async def get_user_apis(self, user_id: int) -> List[Dict]:
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT * FROM github_apis WHERE user_id = %s ORDER BY created_at DESC", (user_id,))
                    apis = [dict(row) for row in cursor.fetchall()]
                    logger.debug(f"📋 Found {len(apis)} APIs for user {user_id}")
                    return apis
            finally:
                self._put_connection(conn)
        except Exception as e:
            logger.error(f"❌ Error getting user APIs: {e}")
            return []

    async def get_active_api(self, user_id: int) -> Optional[Dict]:
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT * FROM github_apis WHERE user_id = %s AND is_active = %s", (user_id, True))
                    api_data = cursor.fetchone()
                    if api_data:
                        api_data = dict(api_data)
                        # Decrypt the token
                        api_data['github_token'] = self._decrypt_token(api_data['github_token'])
                        logger.debug(f"🔧 Found active API for user {user_id}: {api_data['api_name']}")
                        return api_data
                    logger.debug(f"ℹ️ No active API found for user {user_id}")
                    return None
            finally:
                self._put_connection(conn)
        except Exception as e:
            logger.error(f"❌ Error getting active API: {e}")
            return None

    async def set_active_api(self, user_id: int, api_name: str) -> bool:
        try:
            logger.info(f"⚙️ Setting active API '{api_name}' for user {user_id}")

            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    # First, deactivate all APIs for user
                    cursor.execute("UPDATE github_apis SET is_active = %s WHERE user_id = %s", (False, user_id))

                    # Then activate the selected API
                    cursor.execute("UPDATE github_apis SET is_active = %s WHERE user_id = %s AND api_name = %s",
                                 (True, user_id, api_name))

                    if cursor.rowcount > 0:
                        conn.commit()
                        logger.info(f"✅ Set active API '{api_name}' for user {user_id}")
                        return True
                    else:
                        logger.warning(f"⚠️ API '{api_name}' not found for user {user_id}")
                        return False
            finally:
                self._put_connection(conn)

        except Exception as e:
            logger.error(f"❌ Error setting active API: {e}")
            return False

    async def remove_github_api(self, user_id: int, api_name: str) -> bool:
        try:
            logger.info(f"🗑️ Removing API '{api_name}' for user {user_id}")
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM github_apis WHERE user_id = %s AND api_name = %s", (user_id, api_name))
                    conn.commit()
                logger.info(f"✅ Removed API '{api_name}' for user {user_id}")
                return True
            finally:
                self._put_connection(conn)
        except Exception as e:
            logger.error(f"❌ Error removing GitHub API: {e}")
            return False

    # Repository Management
    async def update_repository_status(self, user_id: int, repo_name: str, owner: str, visibility: str) -> bool:
        try:
            logger.debug(f"📊 Updating repo status: {owner}/{repo_name} -> {visibility}")

            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    # Upsert repository status
                    cursor.execute("""
                        INSERT INTO repositories (user_id, repo_name, owner, current_visibility, last_modified)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (user_id, repo_name, owner)
                        DO UPDATE SET current_visibility = EXCLUDED.current_visibility,
                                     last_modified = EXCLUDED.last_modified
                    """, (user_id, repo_name, owner, visibility, datetime.utcnow()))
                    conn.commit()
                return True
            finally:
                self._put_connection(conn)
        except Exception as e:
            logger.error(f"❌ Error updating repository status: {e}")
            return False

    # Audit Logging
    async def log_action(self, user_id: int, action: str, repository: str, status: str) -> bool:
        try:
            logger.debug(f"📝 Logging action: {action} on {repository} - {status}")

            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO audit_logs (user_id, action, repository, timestamp, status)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (user_id, action, repository, datetime.utcnow(), status))
                    conn.commit()
                return True
            finally:
                self._put_connection(conn)
        except Exception as e:
            logger.error(f"❌ Error logging action: {e}")
            return False

    async def get_user_logs(self, user_id: int, limit: int = 10) -> List[Dict]:
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT * FROM audit_logs WHERE user_id = %s ORDER BY timestamp DESC LIMIT %s",
                                 (user_id, limit))
                    logs = [dict(row) for row in cursor.fetchall()]
                    logger.debug(f"📋 Found {len(logs)} logs for user {user_id}")
                    return logs
            finally:
                self._put_connection(conn)
        except Exception as e:
            logger.error(f"❌ Error getting user logs: {e}")
            return []
