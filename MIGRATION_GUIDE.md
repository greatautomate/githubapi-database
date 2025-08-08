# Migration Guide: Supabase to Render PostgreSQL

This guide explains the migration from Supabase to Render PostgreSQL for the GitHub Repository Visibility Bot.

## 🎯 Migration Overview

### Why Migrate to Render PostgreSQL?

1. **Unified Platform**: Database and application on the same platform
2. **Better Performance**: Private network connectivity between services
3. **Simplified Management**: Single dashboard for all resources
4. **Cost Optimization**: Integrated billing and resource management
5. **Enhanced Security**: Private network communication

### Key Changes Made

- **Database Provider**: Supabase → Render PostgreSQL
- **Connection Method**: HTTP API → Direct PostgreSQL connection
- **Dependencies**: `supabase` → `psycopg2-binary`
- **Configuration**: Environment variables updated
- **Deployment**: Integrated database in render.yaml

## 🔧 Technical Changes

### 1. Database Connection

**Before (Supabase):**
```python
from supabase import create_client, Client
self.client: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
```

**After (Render PostgreSQL):**
```python
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool

self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
    minconn=1,
    maxconn=20,
    dsn=self.database_url,
    cursor_factory=RealDictCursor
)
```

### 2. Query Execution

**Before (Supabase):**
```python
result = self.client.table('users').select('*').eq('user_id', user_id).execute()
user = result.data[0] if result.data else None
```

**After (PostgreSQL):**
```python
with conn.cursor() as cursor:
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    if user:
        user = dict(user)
```

### 3. Environment Variables

**Before:**
```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_service_role_key
```

**After:**
```env
DATABASE_URL=postgresql://user:password@host:port/database
```

## 📋 Migration Steps

### Step 1: Update Dependencies

1. Remove Supabase from requirements.txt
2. Ensure psycopg2-binary is included
3. Update imports in database.py

### Step 2: Create Render PostgreSQL Database

1. Go to Render Dashboard
2. Create new PostgreSQL database
3. Choose appropriate plan (Free/Starter/Pro)
4. Note the connection details

### Step 3: Update Configuration

1. Update `app/config.py` to use DATABASE_URL
2. Remove Supabase-related configuration
3. Update validation logic

### Step 4: Migrate Database Schema

1. Connect to your new Render PostgreSQL database
2. Run the migration SQL from `migrations/init.sql`
3. Verify all tables and indexes are created

### Step 5: Update Application Code

1. Replace Supabase client with PostgreSQL connection pool
2. Convert all queries from Supabase syntax to SQL
3. Update error handling for PostgreSQL exceptions

### Step 6: Update Deployment Configuration

1. Update `render.yaml` to include database definition
2. Link DATABASE_URL to the database service
3. Remove Supabase environment variables

### Step 7: Data Migration (if needed)

If you have existing data in Supabase:

1. Export data from Supabase
2. Transform to PostgreSQL format
3. Import into Render PostgreSQL

## 🔒 Security Considerations

### Connection Security
- Uses TLS encryption for all connections
- Private network connectivity within Render
- Connection pooling for efficient resource usage

### Token Encryption
- Same Fernet encryption maintained
- No changes to encryption logic
- Tokens remain secure in transit and at rest

## 🚀 Performance Improvements

### Connection Pooling
- ThreadedConnectionPool for efficient connections
- Configurable min/max connections
- Automatic connection management

### Network Performance
- Private network connectivity
- Reduced latency between services
- No external API calls for database operations

### Query Performance
- Direct SQL queries instead of API calls
- Proper indexing maintained
- Connection reuse reduces overhead

## 🧪 Testing the Migration

### 1. Local Testing
```bash
# Set up local environment
export DATABASE_URL="postgresql://localhost:5432/test_db"
export ENCRYPTION_KEY="your-test-encryption-key"
export TELEGRAM_BOT_TOKEN="your-test-bot-token"

# Run the application
python -m app.main
```

### 2. Database Connection Test
```python
from app.database import Database
db = Database()
# Should connect successfully without errors
```

### 3. Functionality Testing
- Test user registration
- Test GitHub API management
- Test repository operations
- Test audit logging

## 🔍 Troubleshooting

### Common Issues

**Connection Errors:**
- Verify DATABASE_URL format
- Check network connectivity
- Ensure database is running

**Permission Errors:**
- Verify database user permissions
- Check table ownership
- Ensure proper grants

**Migration Errors:**
- Check SQL syntax compatibility
- Verify data types match
- Ensure constraints are valid

### Debug Commands

```bash
# Test database connection
psql $DATABASE_URL -c "SELECT version();"

# Check tables
psql $DATABASE_URL -c "\dt"

# Verify indexes
psql $DATABASE_URL -c "\di"
```

## 📊 Monitoring

### Database Metrics
- Connection count monitoring
- Query performance tracking
- Storage usage monitoring

### Application Metrics
- Error rate monitoring
- Response time tracking
- Resource usage monitoring

## 🎉 Benefits Achieved

1. **Simplified Architecture**: Single platform management
2. **Better Performance**: Private network connectivity
3. **Cost Efficiency**: Integrated billing
4. **Enhanced Security**: Private network communication
5. **Easier Maintenance**: Unified dashboard and monitoring

## 📞 Support

If you encounter issues during migration:

1. Check Render PostgreSQL documentation
2. Review application logs
3. Test database connectivity
4. Verify environment variables
5. Contact Render support if needed

---

**Migration completed successfully! 🎉**

The bot now uses Render PostgreSQL for improved performance, security, and management simplicity.
