# 🤖 GitHub Repository Visibility Bot

A powerful Telegram bot that allows you to manage GitHub repository visibility (public/private) directly from Telegram. Built with Python, supports multiple GitHub accounts, batch operations, and includes comprehensive logging and security features. Uses Render PostgreSQL for reliable, scalable data storage.

![Bot Demo](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)
![Python](https://img.shields.io/badge/Python-3.11+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## 🚀 Features

### 🔑 GitHub API Management
- **Multiple Account Support**: Manage multiple GitHub accounts simultaneously
- **Secure Token Storage**: GitHub tokens are encrypted before database storage
- **Easy API Switching**: Switch between different GitHub accounts with simple commands
- **Token Validation**: Automatic validation of GitHub tokens during setup

### 📁 Repository Management
- **Visibility Toggle**: Change repository visibility between public and private
- **Batch Operations**: Toggle multiple repositories at once with confirmation prompts
- **Repository Listing**: View all repositories with detailed information
- **Status Checking**: Check current visibility status of any repository
- **Real-time Updates**: Instant feedback on all operations

### 🛡️ Security & Authorization
- **User Authorization System**: Admin-controlled access management
- **Rate Limiting**: Built-in protection against API abuse
- **Encrypted Storage**: All sensitive data encrypted in database
- **Audit Logging**: Complete activity logs for all operations
- **Admin Controls**: Authorize/revoke user access

### 📊 Monitoring & Logging
- **Activity Logs**: Track all repository changes and API operations
- **Success/Failure Tracking**: Detailed operation status monitoring
- **User Management**: View and manage authorized users
- **Database Audit Trail**: Complete history of all bot activities

## 🛠️ Prerequisites

- **Python 3.11+**
- **Render.com Account** (for deployment and database)
- **Telegram Bot Token** (from @BotFather)
- **GitHub Personal Access Token(s)**

## ⚡ Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/github-visibility-bot.git
cd github-visibility-bot
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables

Create a `.env` file in the root directory:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
DATABASE_URL=postgresql://user:password@host:port/database
ENCRYPTION_KEY=your_32_character_encryption_key_here
ADMIN_USER_IDS=your_telegram_user_id,other_admin_id
```

### 4. Set Up Database

Run the following SQL in your Render PostgreSQL database or use the provided migration file:

```sql
-- Create users table
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    is_authorized BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create github_apis table
CREATE TABLE IF NOT EXISTS github_apis (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    api_name VARCHAR(255) NOT NULL,
    github_token TEXT NOT NULL,
    github_username VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, api_name)
);

-- Create repositories table
CREATE TABLE IF NOT EXISTS repositories (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    repo_name VARCHAR(255) NOT NULL,
    owner VARCHAR(255) NOT NULL,
    current_visibility VARCHAR(20) NOT NULL CHECK (current_visibility IN ('public', 'private')),
    last_modified TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, repo_name, owner)
);

-- Create audit_logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    action VARCHAR(255) NOT NULL,
    repository VARCHAR(255) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(50) NOT NULL CHECK (status IN ('success', 'failed'))
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
CREATE INDEX IF NOT EXISTS idx_github_apis_user_id ON github_apis(user_id);
CREATE INDEX IF NOT EXISTS idx_github_apis_user_active ON github_apis(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_repositories_user_id ON repositories(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
```

### 5. Run the Bot

```bash
python -m app.main
```

## 🚀 Deployment on Render.com

### 1. Create Database and Background Worker Service

1. Connect your GitHub repository to Render.com
2. Create a new **PostgreSQL Database** first
3. Create a new **Background Worker** service (not web service)
4. Set the following configuration:

```yaml
services:
  - type: worker
    name: github-visibility-bot
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python -m app.main
    envVars:
      - key: TELEGRAM_BOT_TOKEN
        sync: false
      - key: DATABASE_URL
        fromDatabase:
          name: github-bot-db
          property: connectionString
      - key: ENCRYPTION_KEY
        sync: false
      - key: ADMIN_USER_IDS
        sync: false

databases:
  - name: github-bot-db
    databaseName: github_visibility_bot
    user: github_bot_user
    plan: starter
```

### 2. Set Environment Variables

In your Render.com dashboard, add these environment variables:

- `TELEGRAM_BOT_TOKEN`: Your bot token from @BotFather
- `DATABASE_URL`: Automatically set from your Render PostgreSQL database
- `ENCRYPTION_KEY`: A 32-character encryption key
- `ADMIN_USER_IDS`: Comma-separated list of admin Telegram user IDs

### 3. Deploy

Your bot will automatically deploy and start running!

## 📱 Usage Guide

### Getting Started

1. **Start the bot**: Send `/start` to your bot
2. **Get authorized**: Ask an admin to authorize you with `/authorize YOUR_USER_ID`
3. **Add GitHub API**: Use `/add_api personal YOUR_GITHUB_TOKEN`
4. **Load the API**: Use `/load_api personal`
5. **List repositories**: Use `/list_repos`

### GitHub Token Setup

1. Go to GitHub → Settings → Developer settings → Personal access tokens
2. Generate new token with these scopes:
   - `repo` (Full control of private repositories)
   - `public_repo` (Access public repositories)
3. Copy the token and use it with `/add_api`

## 🎯 Command Reference

### 🔑 GitHub API Management

| Command | Description | Example |
|---------|-------------|---------|
| `/add_api <name> <token>` | Add new GitHub API credentials | `/add_api personal ghp_xxxxxxxxxxxx` |
| `/list_apis` | Show all your GitHub APIs | `/list_apis` |
| `/load_api <name>` | Switch to specific GitHub API | `/load_api personal` |
| `/current_api` | Show currently active API | `/current_api` |
| `/remove_api <name>` | Remove GitHub API credentials | `/remove_api old-account` |

### 📁 Repository Management

| Command | Description | Example |
|---------|-------------|---------|
| `/list_repos` | List all repositories from current API | `/list_repos` |
| `/public <repo>` | Make repository public | `/public my-awesome-project` |
| `/private <repo>` | Make repository private | `/private secret-project` |
| `/repo_status <repo>` | Check repository visibility status | `/repo_status my-project` |
| `/batch_toggle <repos>` | Toggle multiple repositories | `/batch_toggle repo1,repo2,repo3` |
| `/batch_toggle private <repos>` | Make multiple repos private | `/batch_toggle private repo1,repo2` |
| `/batch_toggle public <repos>` | Make multiple repos public | `/batch_toggle public repo1,repo2` |

### 📊 Monitoring & Admin

| Command | Description | Example |
|---------|-------------|---------|
| `/logs` | Show recent activity logs | `/logs` |
| `/authorize <user_id>` | Authorize user access (admin only) | `/authorize 123456789` |
| `/revoke <user_id>` | Revoke user access (admin only) | `/revoke 123456789` |
| `/help` | Show all available commands | `/help` |
| `/start` | Initialize and check your status | `/start` |

## 📂 Project Structure

```
github-visibility-bot/
├── app/
│   ├── __init__.py
│   ├── main.py              # Bot entry point and application setup
│   ├── config.py            # Configuration management
│   ├── database.py          # Database operations with Supabase
│   ├── github_api.py        # GitHub API integration
│   ├── handlers.py          # Telegram command handlers
│   ├── auth.py              # Authorization and rate limiting
│   ├── utils.py             # Utility functions
│   └── encryption.py        # Token encryption utilities
├── migrations/
│   └── init.sql             # Database schema setup
├── Dockerfile               # Docker configuration
├── requirements.txt         # Python dependencies
├── render.yaml             # Render.com deployment config
└── README.md               # This file
```

## 🔒 Security Features

### Data Protection
- **Token Encryption**: All GitHub tokens are encrypted using Fernet encryption before storage
- **Secure Database**: Render PostgreSQL provides enterprise-grade security for data storage
- **Environment Variables**: Sensitive configuration stored as environment variables

### Access Control
- **User Authorization**: Only authorized users can access bot functionality
- **Admin Controls**: Admins can authorize/revoke user access
- **Rate Limiting**: Built-in protection against API abuse and spam

### Audit Trail
- **Complete Logging**: All operations are logged with timestamps and status
- **User Tracking**: All actions are linked to specific users
- **Operation History**: Full history of repository visibility changes

## 🛠️ Configuration Options

### Environment Variables

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather | Yes | `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz` |
| `DATABASE_URL` | Render PostgreSQL connection string | Yes | `postgresql://user:pass@host:port/db` |
| `ENCRYPTION_KEY` | 32-character encryption key | Yes | `your-32-character-encryption-key` |
| `ADMIN_USER_IDS` | Comma-separated admin user IDs | Yes | `123456789,987654321` |

### Bot Configuration

- **Rate Limiting**: 30 requests per minute per user
- **Batch Limit**: Maximum 10 repositories per batch operation
- **Token Validation**: Automatic validation of GitHub tokens
- **Error Handling**: Comprehensive error handling with user-friendly messages

## 🔧 Development

### Running Locally

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables in `.env` file
4. Set up Render PostgreSQL database with provided SQL
5. Run: `python -m app.main`

### Adding New Features

1. Create feature branch: `git checkout -b feature/new-feature`
2. Implement changes in appropriate modules
3. Test thoroughly with different scenarios
4. Update documentation and tests
5. Submit pull request

### Database Migrations

To add new database features:

1. Create migration SQL in `migrations/` directory
2. Test migration on development database
3. Update database schema documentation
4. Include migration in deployment process

## 🐛 Troubleshooting

### Common Issues

**Bot not responding to commands:**
- Check if bot token is valid
- Verify bot is running and not crashed
- Check Render.com logs for errors

**GitHub API errors:**
- Verify GitHub token has correct permissions (`repo` scope)
- Check if token is expired
- Ensure repository exists and you have access

**Database connection issues:**
- Verify DATABASE_URL is correct
- Check if database tables are created
- Ensure network connectivity to Render PostgreSQL

**Authorization problems:**
- Verify user ID is in admin list
- Check if user is authorized in database
- Ensure proper admin privileges

### Getting Help

1. Check the logs in Render.com dashboard
2. Verify all environment variables are set correctly
3. Test database connection manually
4. Check GitHub token permissions
5. Review Telegram bot configuration

### Debug Mode

Enable debug logging by setting log level to DEBUG in `main.py`:

```python
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # Change from INFO to DEBUG
)
```

## 📈 Performance

### Optimization Features
- **Async Operations**: All GitHub API calls are asynchronous
- **Connection Pooling**: Efficient database connection management
- **Rate Limiting**: Prevents API rate limit exceeded errors
- **Batch Processing**: Efficient handling of multiple repository operations
- **Caching**: Minimal API calls through smart caching

### Scalability
- **Multi-user Support**: Handles multiple users simultaneously
- **Database Indexing**: Optimized database queries with proper indexes
- **Resource Management**: Efficient memory and CPU usage
- **Background Processing**: Non-blocking operation execution

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** with proper testing
4. **Commit your changes**: `git commit -m 'Add amazing feature'`
5. **Push to the branch**: `git push origin feature/amazing-feature`
6. **Open a Pull Request**

### Contribution Guidelines

- Write clear, readable code with comments
- Include tests for new features
- Update documentation for any changes
- Follow existing code style and patterns
- Test thoroughly before submitting

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **python-telegram-bot** - Excellent Telegram bot framework
- **Render PostgreSQL** - Reliable, scalable database platform
- **GitHub API** - Comprehensive repository management API
- **Render.com** - Simple and reliable deployment platform

## 📞 Support

For support and questions:

1. **Check the troubleshooting section** in this README
2. **Review the logs** in your deployment platform
3. **Open an issue** on GitHub with detailed information
4. **Contact the maintainers** for urgent issues

## 🔄 Changelog

### v1.0.0 (Current)
- ✅ Initial release with full functionality
- ✅ Multiple GitHub account support
- ✅ Batch repository operations
- ✅ Comprehensive security features
- ✅ Complete audit logging
- ✅ Production-ready deployment

---

**Made with ❤️ by @medusaXD for Personal Use**

*Star this repository if you find it useful! 🌟*
