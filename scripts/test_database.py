#!/usr/bin/env python3
"""
Database Test Script for GitHub Repository Visibility Bot
Tests all database operations with Render PostgreSQL
"""

import os
import sys
import asyncio
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import Database
from app.config import Config
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_user_operations():
    """Test user-related database operations"""
    logger.info("🧪 Testing user operations...")
    
    db = Database()
    test_user_id = 999999999
    test_username = "test_user"
    
    try:
        # Test user creation
        success = await db.create_user(test_user_id, test_username)
        assert success, "User creation failed"
        logger.info("✅ User creation successful")
        
        # Test user retrieval
        user = await db.get_user(test_user_id)
        assert user is not None, "User retrieval failed"
        assert user['user_id'] == test_user_id, "User ID mismatch"
        assert user['username'] == test_username, "Username mismatch"
        logger.info("✅ User retrieval successful")
        
        # Test user authorization
        success = await db.authorize_user(test_user_id)
        assert success, "User authorization failed"
        
        user = await db.get_user(test_user_id)
        assert user['is_authorized'] == True, "User authorization not reflected"
        logger.info("✅ User authorization successful")
        
        # Test user revocation
        success = await db.revoke_user(test_user_id)
        assert success, "User revocation failed"
        
        user = await db.get_user(test_user_id)
        assert user['is_authorized'] == False, "User revocation not reflected"
        logger.info("✅ User revocation successful")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ User operations test failed: {e}")
        return False

async def test_github_api_operations():
    """Test GitHub API-related database operations"""
    logger.info("🧪 Testing GitHub API operations...")
    
    db = Database()
    test_user_id = 999999999
    test_api_name = "test_api"
    test_token = "ghp_test_token_12345"
    test_username = "test_github_user"
    
    try:
        # Test API addition
        success = await db.add_github_api(test_user_id, test_api_name, test_token, test_username)
        assert success, "GitHub API addition failed"
        logger.info("✅ GitHub API addition successful")
        
        # Test API listing
        apis = await db.get_user_apis(test_user_id)
        assert len(apis) > 0, "No APIs found for user"
        assert apis[0]['api_name'] == test_api_name, "API name mismatch"
        logger.info("✅ GitHub API listing successful")
        
        # Test setting active API
        success = await db.set_active_api(test_user_id, test_api_name)
        assert success, "Setting active API failed"
        logger.info("✅ Setting active API successful")
        
        # Test getting active API
        active_api = await db.get_active_api(test_user_id)
        assert active_api is not None, "No active API found"
        assert active_api['api_name'] == test_api_name, "Active API name mismatch"
        assert active_api['github_token'] == test_token, "Token decryption failed"
        logger.info("✅ Getting active API successful")
        
        # Test API removal
        success = await db.remove_github_api(test_user_id, test_api_name)
        assert success, "GitHub API removal failed"
        
        apis = await db.get_user_apis(test_user_id)
        assert len(apis) == 0, "API not removed properly"
        logger.info("✅ GitHub API removal successful")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ GitHub API operations test failed: {e}")
        return False

async def test_repository_operations():
    """Test repository-related database operations"""
    logger.info("🧪 Testing repository operations...")
    
    db = Database()
    test_user_id = 999999999
    test_repo_name = "test-repo"
    test_owner = "test-owner"
    test_visibility = "private"
    
    try:
        # Test repository status update
        success = await db.update_repository_status(test_user_id, test_repo_name, test_owner, test_visibility)
        assert success, "Repository status update failed"
        logger.info("✅ Repository status update successful")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Repository operations test failed: {e}")
        return False

async def test_audit_operations():
    """Test audit log-related database operations"""
    logger.info("🧪 Testing audit operations...")
    
    db = Database()
    test_user_id = 999999999
    test_action = "test_action"
    test_repository = "test-owner/test-repo"
    test_status = "success"
    
    try:
        # Test action logging
        success = await db.log_action(test_user_id, test_action, test_repository, test_status)
        assert success, "Action logging failed"
        logger.info("✅ Action logging successful")
        
        # Test log retrieval
        logs = await db.get_user_logs(test_user_id, 10)
        assert len(logs) > 0, "No logs found for user"
        assert logs[0]['action'] == test_action, "Action mismatch in logs"
        assert logs[0]['repository'] == test_repository, "Repository mismatch in logs"
        assert logs[0]['status'] == test_status, "Status mismatch in logs"
        logger.info("✅ Log retrieval successful")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Audit operations test failed: {e}")
        return False

async def cleanup_test_data():
    """Clean up test data from database"""
    logger.info("🧹 Cleaning up test data...")
    
    try:
        db = Database()
        test_user_id = 999999999
        
        # Get a connection and clean up manually
        conn = db._get_connection()
        try:
            with conn.cursor() as cursor:
                # Delete in reverse order of dependencies
                cursor.execute("DELETE FROM audit_logs WHERE user_id = %s", (test_user_id,))
                cursor.execute("DELETE FROM repositories WHERE user_id = %s", (test_user_id,))
                cursor.execute("DELETE FROM github_apis WHERE user_id = %s", (test_user_id,))
                cursor.execute("DELETE FROM users WHERE user_id = %s", (test_user_id,))
                conn.commit()
            logger.info("✅ Test data cleanup successful")
        finally:
            db._put_connection(conn)
            
    except Exception as e:
        logger.error(f"❌ Test data cleanup failed: {e}")

async def main():
    """Main test function"""
    logger.info("🚀 Starting database tests...")
    
    # Check environment
    if not os.getenv('DATABASE_URL'):
        logger.error("❌ DATABASE_URL environment variable not set")
        sys.exit(1)
    
    if not os.getenv('ENCRYPTION_KEY'):
        logger.error("❌ ENCRYPTION_KEY environment variable not set")
        sys.exit(1)
    
    tests = [
        ("User Operations", test_user_operations),
        ("GitHub API Operations", test_github_api_operations),
        ("Repository Operations", test_repository_operations),
        ("Audit Operations", test_audit_operations)
    ]
    
    failed_tests = []
    
    for test_name, test_func in tests:
        logger.info(f"\n--- {test_name} ---")
        try:
            if await test_func():
                logger.info(f"✅ {test_name} passed")
            else:
                failed_tests.append(test_name)
                logger.error(f"❌ {test_name} failed")
        except Exception as e:
            failed_tests.append(test_name)
            logger.error(f"❌ {test_name} failed with exception: {e}")
    
    # Cleanup
    await cleanup_test_data()
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("DATABASE TEST SUMMARY")
    logger.info("="*50)
    
    if failed_tests:
        logger.error(f"❌ Failed tests: {failed_tests}")
        sys.exit(1)
    else:
        logger.info("✅ All database tests passed!")
        logger.info("Database is ready for production use")

if __name__ == "__main__":
    asyncio.run(main())
