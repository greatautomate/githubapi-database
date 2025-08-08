#!/usr/bin/env python3
"""
Render Deployment Script for GitHub Repository Visibility Bot
Helps with database setup and deployment verification
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = [
        'DATABASE_URL',
        'TELEGRAM_BOT_TOKEN', 
        'ENCRYPTION_KEY',
        'ADMIN_USER_IDS'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        return False
    
    logger.info("✅ All required environment variables are set")
    return True

def test_database_connection():
    """Test connection to Render PostgreSQL database"""
    try:
        database_url = os.getenv('DATABASE_URL')
        logger.info("🔌 Testing database connection...")
        
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        with conn.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            logger.info(f"✅ Database connection successful: {version['version']}")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

def setup_database_schema():
    """Set up database schema from migration file"""
    try:
        database_url = os.getenv('DATABASE_URL')
        logger.info("📋 Setting up database schema...")
        
        # Read migration file
        migration_file = os.path.join(os.path.dirname(__file__), '..', 'migrations', 'init.sql')
        with open(migration_file, 'r') as f:
            schema_sql = f.read()
        
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        with conn.cursor() as cursor:
            cursor.execute(schema_sql)
            conn.commit()
            logger.info("✅ Database schema created successfully")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Database schema setup failed: {e}")
        return False

def verify_tables():
    """Verify that all required tables exist"""
    try:
        database_url = os.getenv('DATABASE_URL')
        logger.info("🔍 Verifying database tables...")
        
        required_tables = ['users', 'github_apis', 'repositories', 'audit_logs']
        
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            existing_tables = [row['table_name'] for row in cursor.fetchall()]
            
            missing_tables = [table for table in required_tables if table not in existing_tables]
            
            if missing_tables:
                logger.error(f"❌ Missing tables: {missing_tables}")
                return False
            
            logger.info(f"✅ All required tables exist: {required_tables}")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Table verification failed: {e}")
        return False

def verify_indexes():
    """Verify that all required indexes exist"""
    try:
        database_url = os.getenv('DATABASE_URL')
        logger.info("🔍 Verifying database indexes...")
        
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE schemaname = 'public'
            """)
            existing_indexes = [row['indexname'] for row in cursor.fetchall()]
            
            required_indexes = [
                'idx_users_user_id',
                'idx_github_apis_user_id', 
                'idx_github_apis_user_active',
                'idx_repositories_user_id',
                'idx_audit_logs_user_id',
                'idx_audit_logs_timestamp'
            ]
            
            missing_indexes = [idx for idx in required_indexes if idx not in existing_indexes]
            
            if missing_indexes:
                logger.warning(f"⚠️ Missing indexes: {missing_indexes}")
            else:
                logger.info(f"✅ All required indexes exist")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Index verification failed: {e}")
        return False

def test_encryption():
    """Test encryption functionality"""
    try:
        logger.info("🔐 Testing encryption...")
        
        # Import encryption functions
        sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
        from app.encryption import encrypt_token, decrypt_token
        
        test_token = "test_github_token_12345"
        encrypted = encrypt_token(test_token)
        decrypted = decrypt_token(encrypted)
        
        if decrypted == test_token:
            logger.info("✅ Encryption test successful")
            return True
        else:
            logger.error("❌ Encryption test failed: decrypted value doesn't match")
            return False
            
    except Exception as e:
        logger.error(f"❌ Encryption test failed: {e}")
        return False

def main():
    """Main deployment verification function"""
    logger.info("🚀 Starting Render deployment verification...")
    
    checks = [
        ("Environment Variables", check_environment),
        ("Database Connection", test_database_connection),
        ("Database Schema", setup_database_schema),
        ("Table Verification", verify_tables),
        ("Index Verification", verify_indexes),
        ("Encryption Test", test_encryption)
    ]
    
    failed_checks = []
    
    for check_name, check_func in checks:
        logger.info(f"\n--- {check_name} ---")
        if not check_func():
            failed_checks.append(check_name)
    
    logger.info("\n" + "="*50)
    logger.info("DEPLOYMENT VERIFICATION SUMMARY")
    logger.info("="*50)
    
    if failed_checks:
        logger.error(f"❌ Failed checks: {failed_checks}")
        logger.error("Please fix the issues above before deploying")
        sys.exit(1)
    else:
        logger.info("✅ All checks passed! Ready for deployment")
        logger.info("\nNext steps:")
        logger.info("1. Commit your changes to Git")
        logger.info("2. Push to your repository")
        logger.info("3. Deploy on Render.com")
        logger.info("4. Monitor logs for successful startup")

if __name__ == "__main__":
    main()
