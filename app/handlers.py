import asyncio
import logging
import traceback
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.config import Config
from app.database import Database
from app.github_api import GitHubAPI
from app.utils import format_repository_list, format_logs, parse_repository_list

logger = logging.getLogger(__name__)

class BotHandlers:
    def __init__(self):
        logger.info("Initializing BotHandlers...")
        try:
            self.db = Database()
            logger.info("✅ BotHandlers initialized successfully")
            logger.info(f"🔧 Admin configuration: {len(Config.ADMIN_USER_IDS)} admin(s) configured")
            logger.info(f"🔧 Admin IDs: {Config.ADMIN_USER_IDS}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize BotHandlers: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def _rate_limit_check(self, user_id: int) -> bool:
        return True

    def _is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized (admin or database authorized)"""
        # First check if user is hardcoded admin
        if Config.is_admin(user_id):
            return True

        # Then check database authorization (for future expansion)
        # This allows admins to authorize other users via database
        return False

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command with enhanced formatting"""
        try:
            user_id = update.effective_user.id
            username = update.effective_user.username or f"user_{user_id}"

            logger.info(f"📍 Processing /start command from user {user_id} ({username})")
            logger.info(f"🔍 User admin status: {Config.is_admin(user_id)}")

            # Create or get user
            user = await self.db.get_user(user_id)
            if not user:
                logger.info(f"🆕 Creating new user: {user_id}")
                success = await self.db.create_user(user_id, username)
                if success:
                    user = await self.db.get_user(user_id)
                else:
                    await update.message.reply_text(
                        "❌ <b>Registration Failed</b>\n"
                        "Could not register your account. Please try again.",
                        parse_mode='HTML'
                    )
                    return

            # Check authorization (hardcoded admin or database authorized)
            is_authorized = self._is_authorized(user_id) or (user and user.get('is_authorized', False))

            if is_authorized:
                # Get user's current status
                apis = await self.db.get_user_apis(user_id)
                active_api = await self.db.get_active_api(user_id)
                recent_logs = await self.db.get_user_logs(user_id, 5)

                # Build admin status info
                admin_status = ""
                if Config.is_admin(user_id):
                    admin_status = "\n🔱 <b>Admin Status:</b> You have administrator privileges"

                # Build API status info
                api_status = ""
                if apis:
                    api_count = len(apis)
                    if active_api:
                        api_status = f"\n<b>📊 Your Status:</b>\n• GitHub APIs: {api_count} (Active: <code>{active_api['api_name']}</code>)\n• Recent actions: {len(recent_logs)}"
                    else:
                        api_status = f"\n<b>📊 Your Status:</b>\n• GitHub APIs: {api_count} (None active)\n• Use <code>/load_api &lt;name&gt;</code> to activate one"
                else:
                    api_status = f"\n<b>📊 Your Status:</b>\n• No GitHub APIs added yet\n• Start with <code>/add_api personal YOUR_TOKEN</code>"

                welcome_text = f"""
🚀 <b>Welcome back, {username}!</b>

You are authorized to use this bot.{admin_status}{api_status}

<b>🔑 GitHub API Management:</b>
• <code>/add_api &lt;name&gt; &lt;token&gt;</code> - Add GitHub API
• <code>/list_apis</code> - Show your APIs
• <code>/load_api &lt;name&gt;</code> - Switch API
• <code>/current_api</code> - Show active API

<b>📁 Repository Management:</b>
• <code>/list_repos</code> - List repositories
• <code>/public &lt;repo&gt;</code> - Make repository public
• <code>/private &lt;repo&gt;</code> - Make repository private
• <code>/repo_status &lt;repo&gt;</code> - Check repository status
• <code>/batch_toggle &lt;repos&gt;</code> - Batch operations

<b>📊 Other Commands:</b>
• <code>/logs</code> - View activity logs
• <code>/help</code> - Show all commands

<b>🚀 Quick Start Guide:</b>
1. <code>/add_api personal YOUR_TOKEN</code>
2. <code>/load_api personal</code>
3. <code>/list_repos</code>
4. <code>/private repo-name</code> or <code>/public repo-name</code>
                """
            else:
                welcome_text = f"""
👋 <b>Hello, {username}!</b>

You have been registered but are not yet authorized.
Please contact an administrator to get access.

<b>📋 Your Information:</b>
• User ID: <code>{user_id}</code>
• Username: <code>{username}</code>
• Status: <b>Pending Authorization</b>

<b>📞 Next Steps:</b>
• Contact an admin to authorize your account
• Share your User ID: <code>{user_id}</code>
• Wait for authorization confirmation

<b>ℹ️ Available Commands:</b>
• <code>/help</code> - Show help information
• <code>/start</code> - Refresh your status
                """

            await update.message.reply_text(welcome_text, parse_mode='HTML')
            logger.info(f"✅ Successfully processed /start for user {user_id}")

        except Exception as e:
            logger.error(f"❌ Error in start_command: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            await update.message.reply_text(
                f"❌ <b>Error in Start Command</b>\n"
                f"Error: <code>{str(e)[:200]}</code>\n\n"
                f"Please contact support.",
                parse_mode='HTML'
            )

    async def add_api_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /add_api command - Now with real GitHub integration"""
        try:
            user_id = update.effective_user.id

            if not self._is_authorized(user_id):
                await update.message.reply_text(
                    "❌ <b>Access Denied</b>\n"
                    "You are not authorized to use this command.",
                    parse_mode='HTML'
                )
                return

            if len(context.args) != 2:
                await update.message.reply_text(
                    "❌ <b>Invalid Usage</b>\n"
                    "Usage: <code>/add_api &lt;api_name&gt; &lt;github_token&gt;</code>\n\n"
                    "Example: <code>/add_api personal ghp_xxxxxxxxxxxx</code>",
                    parse_mode='HTML'
                )
                return

            api_name, github_token = context.args

            # Show processing message
            processing_msg = await update.message.reply_text("🔍 <b>Validating GitHub token...</b>", parse_mode='HTML')

            # Validate GitHub token
            github_api = GitHubAPI(github_token, "")
            is_valid, result = await github_api.validate_token()

            if not is_valid:
                await processing_msg.edit_text(
                    f"❌ <b>Invalid GitHub Token</b>\n"
                    f"Error: <code>{result}</code>\n\n"
                    f"Please check your token and try again.",
                    parse_mode='HTML'
                )
                return

            github_username = result

            # Add API to database
            success = await self.db.add_github_api(user_id, api_name, github_token, github_username)

            if success:
                await processing_msg.edit_text(
                    f"✅ <b>GitHub API Added Successfully</b>\n\n"
                    f"<b>API Name:</b> <code>{api_name}</code>\n"
                    f"<b>GitHub Username:</b> <code>{github_username}</code>\n"
                    f"<b>Status:</b> Ready to use\n\n"
                    f"💡 Use <code>/load_api {api_name}</code> to activate it\n"
                    f"💡 Use <code>/list_repos</code> to see your repositories",
                    parse_mode='HTML'
                )

                # Log action
                await self.db.log_action(user_id, "add_api", api_name, "success")
                logger.info(f"✅ Successfully added API '{api_name}' for user {user_id}")
            else:
                await processing_msg.edit_text(
                    "❌ <b>Failed to Add API</b>\n"
                    "Database error occurred. Please try again.",
                    parse_mode='HTML'
                )

        except Exception as e:
            logger.error(f"❌ Error in add_api_command: {e}")
            await update.message.reply_text(f"❌ <b>Error</b>: <code>{str(e)[:200]}</code>", parse_mode='HTML')

    async def list_apis_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list_apis command - Now with real data"""
        try:
            user_id = update.effective_user.id

            if not self._is_authorized(user_id):
                await update.message.reply_text(
                    "❌ <b>Access Denied</b>\n"
                    "You are not authorized to use this command.",
                    parse_mode='HTML'
                )
                return

            apis = await self.db.get_user_apis(user_id)

            if not apis:
                await update.message.reply_text(
                    "📋 <b>No GitHub APIs Found</b>\n\n"
                    "You haven't added any GitHub APIs yet.\n\n"
                    "💡 Use <code>/add_api &lt;name&gt; &lt;token&gt;</code> to add one\n"
                    "💡 Example: <code>/add_api personal ghp_xxxxxxxxxxxx</code>",
                    parse_mode='HTML'
                )
                return

            api_list = "📋 <b>Your GitHub APIs:</b>\n\n"
            for api in apis:
                status = "🟢 <b>Active</b>" if api['is_active'] else "⚪ Inactive"
                created_date = api['created_at'][:10]
                api_list += f"• <b>{api['api_name']}</b> ({status})\n"
                api_list += f"  👤 Username: <code>{api['github_username']}</code>\n"
                api_list += f"  📅 Added: {created_date}\n\n"

            api_list += "<b>💡 Commands:</b>\n"
            api_list += "• <code>/load_api &lt;name&gt;</code> - Switch to API\n"
            api_list += "• <code>/remove_api &lt;name&gt;</code> - Remove API\n"
            api_list += "• <code>/current_api</code> - Show active API"

            await update.message.reply_text(api_list, parse_mode='HTML')

        except Exception as e:
            logger.error(f"❌ Error in list_apis_command: {e}")
            await update.message.reply_text(f"❌ <b>Error</b>: <code>{str(e)[:200]}</code>", parse_mode='HTML')

    async def load_api_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /load_api command - Now with real switching"""
        try:
            user_id = update.effective_user.id

            if not self._is_authorized(user_id):
                await update.message.reply_text(
                    "❌ <b>Access Denied</b>\n"
                    "You are not authorized to use this command.",
                    parse_mode='HTML'
                )
                return

            if len(context.args) != 1:
                await update.message.reply_text(
                    "❌ <b>Invalid Usage</b>\n"
                    "Usage: <code>/load_api &lt;api_name&gt;</code>\n\n"
                    "💡 Use <code>/list_apis</code> to see available APIs",
                    parse_mode='HTML'
                )
                return

            api_name = context.args[0]

            # Check if API exists
            apis = await self.db.get_user_apis(user_id)
            api_exists = any(api['api_name'] == api_name for api in apis)

            if not api_exists:
                available_apis = [api['api_name'] for api in apis]
                await update.message.reply_text(
                    f"❌ <b>API Not Found</b>\n\n"
                    f"API <code>{api_name}</code> doesn't exist.\n\n"
                    f"<b>Available APIs:</b> {', '.join(available_apis) if available_apis else 'None'}\n\n"
                    f"💡 Use <code>/list_apis</code> to see all your APIs",
                    parse_mode='HTML'
                )
                return

            success = await self.db.set_active_api(user_id, api_name)

            if success:
                # Get the loaded API info
                active_api = await self.db.get_active_api(user_id)
                await update.message.reply_text(
                    f"✅ <b>API Loaded Successfully</b>\n\n"
                    f"<b>Active API:</b> <code>{api_name}</code>\n"
                    f"<b>GitHub Username:</b> <code>{active_api['github_username']}</code>\n\n"
                    f"🚀 <b>Ready to use!</b>\n"
                    f"• <code>/list_repos</code> - See your repositories\n"
                    f"• <code>/public &lt;repo&gt;</code> - Make repo public\n"
                    f"• <code>/private &lt;repo&gt;</code> - Make repo private",
                    parse_mode='HTML'
                )
                await self.db.log_action(user_id, "load_api", api_name, "success")
            else:
                await update.message.reply_text(
                    f"❌ <b>Failed to Load API</b>\n"
                    f"Could not switch to API <code>{api_name}</code>.",
                    parse_mode='HTML'
                )

        except Exception as e:
            logger.error(f"❌ Error in load_api_command: {e}")
            await update.message.reply_text(f"❌ <b>Error</b>: <code>{str(e)[:200]}</code>", parse_mode='HTML')

    async def current_api_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /current_api command - Now with real data"""
        try:
            user_id = update.effective_user.id

            if not self._is_authorized(user_id):
                await update.message.reply_text(
                    "❌ <b>Access Denied</b>\n"
                    "You are not authorized to use this command.",
                    parse_mode='HTML'
                )
                return

            active_api = await self.db.get_active_api(user_id)

            if active_api:
                created_date = active_api['created_at'][:10]
                await update.message.reply_text(
                    f"🔧 <b>Current Active API</b>\n\n"
                    f"<b>Name:</b> <code>{active_api['api_name']}</code>\n"
                    f"<b>GitHub Username:</b> <code>{active_api['github_username']}</code>\n"
                    f"<b>Added:</b> {created_date}\n"
                    f"<b>Status:</b> 🟢 Active\n\n"
                    f"<b>Available Commands:</b>\n"
                    f"• <code>/list_repos</code> - List repositories\n"
                    f"• <code>/public &lt;repo&gt;</code> - Make repo public\n"
                    f"• <code>/private &lt;repo&gt;</code> - Make repo private\n"
                    f"• <code>/repo_status &lt;repo&gt;</code> - Check status",
                    parse_mode='HTML'
                )
            else:
                await update.message.reply_text(
                    "❌ <b>No Active API</b>\n\n"
                    "You don't have any active GitHub API loaded.\n\n"
                    "💡 <b>Next Steps:</b>\n"
                    "1. <code>/list_apis</code> - See your APIs\n"
                    "2. <code>/load_api &lt;name&gt;</code> - Load an API\n"
                    "3. Or <code>/add_api &lt;name&gt; &lt;token&gt;</code> - Add new API",
                    parse_mode='HTML'
                )

        except Exception as e:
            logger.error(f"❌ Error in current_api_command: {e}")
            await update.message.reply_text(f"❌ <b>Error</b>: <code>{str(e)[:200]}</code>", parse_mode='HTML')

    async def remove_api_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /remove_api command - Now with confirmation"""
        try:
            user_id = update.effective_user.id

            if not self._is_authorized(user_id):
                await update.message.reply_text(
                    "❌ <b>Access Denied</b>\n"
                    "You are not authorized to use this command.",
                    parse_mode='HTML'
                )
                return

            if len(context.args) != 1:
                await update.message.reply_text(
                    "❌ <b>Invalid Usage</b>\n"
                    "Usage: <code>/remove_api &lt;api_name&gt;</code>\n\n"
                    "💡 Use <code>/list_apis</code> to see your APIs",
                    parse_mode='HTML'
                )
                return

            api_name = context.args[0]

            # Check if API exists
            apis = await self.db.get_user_apis(user_id)
            api_to_remove = next((api for api in apis if api['api_name'] == api_name), None)

            if not api_to_remove:
                available_apis = [api['api_name'] for api in apis]
                await update.message.reply_text(
                    f"❌ <b>API Not Found</b>\n\n"
                    f"API <code>{api_name}</code> doesn't exist.\n\n"
                    f"<b>Available APIs:</b> {', '.join(available_apis) if available_apis else 'None'}",
                    parse_mode='HTML'
                )
                return

            # Confirmation keyboard
            keyboard = [
                [InlineKeyboardButton("✅ Yes, Remove", callback_data=f"remove_api:{api_name}")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            status = "🟢 Active" if api_to_remove['is_active'] else "⚪ Inactive"

            await update.message.reply_text(
                f"⚠️ <b>Confirm API Removal</b>\n\n"
                f"<b>API Name:</b> <code>{api_name}</code>\n"
                f"<b>GitHub Username:</b> <code>{api_to_remove['github_username']}</code>\n"
                f"<b>Status:</b> {status}\n\n"
                f"Are you sure you want to remove this API?\n"
                f"This action cannot be undone.",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )

        except Exception as e:
            logger.error(f"❌ Error in remove_api_command: {e}")
            await update.message.reply_text(f"❌ <b>Error</b>: <code>{str(e)[:200]}</code>", parse_mode='HTML')

    async def list_repos_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list_repos command - Now with real GitHub API"""
        try:
            user_id = update.effective_user.id

            if not self._is_authorized(user_id):
                await update.message.reply_text(
                    "❌ <b>Access Denied</b>\n"
                    "You are not authorized to use this command.",
                    parse_mode='HTML'
                )
                return

            # Get active API
            active_api = await self.db.get_active_api(user_id)
            if not active_api:
                await update.message.reply_text(
                    "❌ <b>No Active API</b>\n\n"
                    "Please load a GitHub API first:\n"
                    "1. <code>/list_apis</code> - See your APIs\n"
                    "2. <code>/load_api &lt;name&gt;</code> - Load an API\n"
                    "3. Or <code>/add_api &lt;name&gt; &lt;token&gt;</code> - Add new API",
                    parse_mode='HTML'
                )
                return

            # Show loading message
            loading_msg = await update.message.reply_text(
                f"🔍 <b>Fetching repositories...</b>\n"
                f"Loading repos for <code>{active_api['github_username']}</code>...",
                parse_mode='HTML'
            )

            # Fetch repositories
            github_api = GitHubAPI(active_api['github_token'], active_api['github_username'])
            repositories = await github_api.list_repositories()

            if not repositories:
                await loading_msg.edit_text(
                    f"📋 <b>No Repositories Found</b>\n\n"
                    f"No repositories found for <code>{active_api['github_username']}</code>.\n\n"
                    f"This could mean:\n"
                    f"• You don't have any repositories\n"
                    f"• The token doesn't have repository access\n"
                    f"• There was an API error",
                    parse_mode='HTML'
                )
                return

            # Format repository list
            repo_text = format_repository_list(repositories, active_api['github_username'])

            # Send repository list (split if too long)
            if len(repo_text) > 4000:
                await loading_msg.edit_text("📋 <b>Repository List</b> (Part 1)", parse_mode='HTML')
                chunks = [repo_text[i:i+4000] for i in range(0, len(repo_text), 4000)]
                for i, chunk in enumerate(chunks):
                    if i == 0:
                        await loading_msg.edit_text(chunk, parse_mode='Markdown')
                    else:
                        await update.message.reply_text(
                            f"📋 <b>Repository List</b> (Part {i+1})\n\n{chunk}",
                            parse_mode='Markdown'
                        )
            else:
                await loading_msg.edit_text(repo_text, parse_mode='Markdown')

        except Exception as e:
            logger.error(f"❌ Error in list_repos_command: {e}")
            await update.message.reply_text(f"❌ <b>Error</b>: <code>{str(e)[:200]}</code>", parse_mode='HTML')

    async def make_public_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /public command - Now with real GitHub API"""
        try:
            user_id = update.effective_user.id

            if not self._is_authorized(user_id):
                await update.message.reply_text(
                    "❌ <b>Access Denied</b>\n"
                    "You are not authorized to use this command.",
                    parse_mode='HTML'
                )
                return

            if len(context.args) != 1:
                await update.message.reply_text(
                    "❌ <b>Invalid Usage</b>\n\n"
                    "Usage: <code>/public &lt;repository_name&gt;</code>\n\n"
                    "Examples:\n"
                    "• <code>/public my-repo</code>\n"
                    "• <code>/public username/my-repo</code>\n\n"
                    "💡 Use <code>/list_repos</code> to see your repositories",
                    parse_mode='HTML'
                )
                return

            repo_name = context.args[0]
            await self._toggle_repository_visibility(update, context, repo_name, False)

        except Exception as e:
            logger.error(f"❌ Error in make_public_command: {e}")
            await update.message.reply_text(f"❌ <b>Error</b>: <code>{str(e)[:200]}</code>", parse_mode='HTML')

    async def make_private_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /private command - Now with real GitHub API"""
        try:
            user_id = update.effective_user.id

            if not self._is_authorized(user_id):
                await update.message.reply_text(
                    "❌ <b>Access Denied</b>\n"
                    "You are not authorized to use this command.",
                    parse_mode='HTML'
                )
                return

            if len(context.args) != 1:
                await update.message.reply_text(
                    "❌ <b>Invalid Usage</b>\n\n"
                    "Usage: <code>/private &lt;repository_name&gt;</code>\n\n"
                    "Examples:\n"
                    "• <code>/private my-repo</code>\n"
                    "• <code>/private username/my-repo</code>\n\n"
                    "💡 Use <code>/list_repos</code> to see your repositories",
                    parse_mode='HTML'
                )
                return

            repo_name = context.args[0]
            await self._toggle_repository_visibility(update, context, repo_name, True)

        except Exception as e:
            logger.error(f"❌ Error in make_private_command: {e}")
            await update.message.reply_text(f"❌ <b>Error</b>: <code>{str(e)[:200]}</code>", parse_mode='HTML')

    async def _toggle_repository_visibility(self, update: Update, context: ContextTypes.DEFAULT_TYPE, repo_name: str, make_private: bool):
        """Helper method to toggle repository visibility - Now with real GitHub API"""
        try:
            user_id = update.effective_user.id

            # Get active API
            active_api = await self.db.get_active_api(user_id)
            if not active_api:
                await update.message.reply_text(
                    "❌ <b>No Active API</b>\n\n"
                    "Please load a GitHub API first using <code>/load_api &lt;name&gt;</code>",
                    parse_mode='HTML'
                )
                return

            github_api = GitHubAPI(active_api['github_token'], active_api['github_username'])

            # Parse owner/repo
            if '/' in repo_name:
                owner, repo_name = repo_name.split('/', 1)
            else:
                owner = active_api['github_username']

            action = "make_private" if make_private else "make_public"
            visibility = "private" if make_private else "public"

            # Show processing message
            processing_msg = await update.message.reply_text(
                f"🔄 <b>Processing...</b>\n\n"
                f"Making <code>{owner}/{repo_name}</code> {visibility}...\n"
                f"This may take a few seconds.",
                parse_mode='HTML'
            )

            # Toggle repository visibility
            success, message = await github_api.toggle_repository_visibility(owner, repo_name, make_private)

            if success:
                await processing_msg.edit_text(
                    f"✅ <b>Success!</b>\n\n"
                    f"🎉 {message}\n\n"
                    f"Repository <code>{owner}/{repo_name}</code> is now <b>{visibility}</b>.\n\n"
                    f"💡 You can verify this by visiting the repository on GitHub.",
                    parse_mode='HTML'
                )

                # Update database and log
                await self.db.update_repository_status(user_id, repo_name, owner, visibility)
                await self.db.log_action(user_id, action, f"{owner}/{repo_name}", "success")

            else:
                await processing_msg.edit_text(
                    f"❌ <b>Failed!</b>\n\n"
                    f"Could not make <code>{owner}/{repo_name}</code> {visibility}.\n\n"
                    f"<b>Error:</b> {message}\n\n"
                    f"<b>Possible reasons:</b>\n"
                    f"• Repository doesn't exist\n"
                    f"• You don't have permission\n"
                    f"• Token doesn't have repo scope\n"
                    f"• Repository is already {visibility}",
                    parse_mode='HTML'
                )
                await self.db.log_action(user_id, action, f"{owner}/{repo_name}", "failed")

        except Exception as e:
            logger.error(f"❌ Error in _toggle_repository_visibility: {e}")
            await update.message.reply_text(f"❌ <b>Error</b>: <code>{str(e)[:200]}</code>", parse_mode='HTML')

    async def repo_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /repo_status command - Now with real GitHub API"""
        try:
            user_id = update.effective_user.id

            if not self._is_authorized(user_id):
                await update.message.reply_text(
                    "❌ <b>Access Denied</b>\n"
                    "You are not authorized to use this command.",
                    parse_mode='HTML'
                )
                return

            if len(context.args) != 1:
                await update.message.reply_text(
                    "❌ <b>Invalid Usage</b>\n\n"
                    "Usage: <code>/repo_status &lt;repository_name&gt;</code>\n\n"
                    "Examples:\n"
                    "• <code>/repo_status my-repo</code>\n"
                    "• <code>/repo_status username/my-repo</code>",
                    parse_mode='HTML'
                )
                return

            # Get active API
            active_api = await self.db.get_active_api(user_id)
            if not active_api:
                await update.message.reply_text(
                    "❌ <b>No Active API</b>\n\n"
                    "Please load a GitHub API first using <code>/load_api &lt;name&gt;</code>",
                    parse_mode='HTML'
                )
                return

            repo_name = context.args[0]
            github_api = GitHubAPI(active_api['github_token'], active_api['github_username'])

            # Parse owner/repo
            if '/' in repo_name:
                owner, repo_name = repo_name.split('/', 1)
            else:
                owner = active_api['github_username']

            # Show loading message
            loading_msg = await update.message.reply_text(
                f"🔍 <b>Checking repository status...</b>\n"
                f"Repository: <code>{owner}/{repo_name}</code>",
                parse_mode='HTML'
            )

            # Get repository info
            repo_info = await github_api.get_repository(owner, repo_name)

            if repo_info:
                visibility = "🔒 <b>Private</b>" if repo_info['private'] else "🔓 <b>Public</b>"
                size_mb = round(repo_info['size'] / 1024, 2) if repo_info['size'] > 0 else 0

                await loading_msg.edit_text(
                    f"📊 <b>Repository Status</b>\n\n"
                    f"<b>Name:</b> <code>{repo_info['name']}</code>\n"
                    f"<b>Owner:</b> <code>{repo_info['owner']}</code>\n"
                    f"<b>Full Name:</b> <code>{repo_info['full_name']}</code>\n"
                    f"<b>Visibility:</b> {visibility}\n"
                    f"<b>Language:</b> {repo_info['language']}\n"
                    f"<b>Size:</b> {size_mb} MB\n"
                    f"<b>Description:</b> {repo_info['description'] or 'No description'}\n\n"
                    f"<b>🔗 Links:</b>\n"
                    f"<a href='{repo_info['url']}'>View on GitHub</a>\n\n"
                    f"<b>📅 Dates:</b>\n"
                    f"• Created: {repo_info['created_at'][:10]}\n"
                    f"• Updated: {repo_info['updated_at'][:10]}",
                    parse_mode='HTML'
                )
            else:
                await loading_msg.edit_text(
                    f"❌ <b>Repository Not Found</b>\n\n"
                    f"Repository <code>{owner}/{repo_name}</code> not found.\n\n"
                    f"<b>Possible reasons:</b>\n"
                    f"• Repository doesn't exist\n"
                    f"• You don't have access to it\n"
                    f"• Repository name is incorrect\n\n"
                    f"💡 Use <code>/list_repos</code> to see available repositories",
                    parse_mode='HTML'
                )

        except Exception as e:
            logger.error(f"❌ Error in repo_status_command: {e}")
            await update.message.reply_text(f"❌ <b>Error</b>: <code>{str(e)[:200]}</code>", parse_mode='HTML')

    async def batch_toggle_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /batch_toggle command - Full implementation"""
        try:
            user_id = update.effective_user.id

            if not self._is_authorized(user_id):
                await update.message.reply_text(
                    "❌ <b>Access Denied</b>\n"
                    "You are not authorized to use this command.",
                    parse_mode='HTML'
                )
                return

            # Get active API
            active_api = await self.db.get_active_api(user_id)
            if not active_api:
                await update.message.reply_text(
                    "❌ <b>No Active API</b>\n\n"
                    "Please load a GitHub API first:\n"
                    "• <code>/list_apis</code> - See your APIs\n"
                    "• <code>/load_api &lt;name&gt;</code> - Load an API",
                    parse_mode='HTML'
                )
                return

            if len(context.args) < 1:
                await update.message.reply_text(
                    "❌ <b>Invalid Usage</b>\n\n"
                    "<b>Usage:</b>\n"
                    "• <code>/batch_toggle &lt;repo1,repo2,repo3&gt;</code> - Toggle visibility\n"
                    "• <code>/batch_toggle private &lt;repo1,repo2&gt;</code> - Make private\n"
                    "• <code>/batch_toggle public &lt;repo1,repo2&gt;</code> - Make public\n\n"
                    "<b>Examples:</b>\n"
                    "• <code>/batch_toggle my-repo1,my-repo2,my-repo3</code>\n"
                    "• <code>/batch_toggle private repo1,repo2</code>\n"
                    "• <code>/batch_toggle public owner/repo1,repo2</code>",
                    parse_mode='HTML'
                )
                return

            # Parse arguments
            if context.args[0].lower() in ['private', 'public']:
                visibility_action = context.args[0].lower()
                if len(context.args) < 2:
                    await update.message.reply_text(
                        "❌ <b>Missing Repository List</b>\n"
                        "Please provide repository names after visibility option.",
                        parse_mode='HTML'
                    )
                    return
                repos_str = ','.join(context.args[1:])
            else:
                # Default to auto-toggle (make private if public, public if private)
                visibility_action = 'toggle'
                repos_str = ','.join(context.args)

            # Parse repository list
            repo_list = parse_repository_list(repos_str, active_api['github_username'])

            if not repo_list:
                await update.message.reply_text(
                    "❌ <b>Invalid Repository List</b>\n"
                    "Please provide valid repository names separated by commas.",
                    parse_mode='HTML'
                )
                return

            if len(repo_list) > 10:
                await update.message.reply_text(
                    "❌ <b>Too Many Repositories</b>\n"
                    f"You can batch toggle maximum 10 repositories at once.\n"
                    f"You provided {len(repo_list)} repositories.",
                    parse_mode='HTML'
                )
                return

            # Show confirmation
            repo_names = [f"<code>{owner}/{repo_name}</code>" for owner, repo_name in repo_list]
            confirmation_text = (
                f"🔄 <b>Batch Toggle Confirmation</b>\n\n"
                f"<b>Action:</b> {visibility_action.title()}\n"
                f"<b>Repositories ({len(repo_list)}):</b>\n" + 
                '\n'.join(f"• {name}" for name in repo_names) + 
                f"\n\n<b>Continue?</b>"
            )

            keyboard = [
                [InlineKeyboardButton("✅ Yes, Continue", callback_data=f"batch_confirm:{visibility_action}:{repos_str}")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                confirmation_text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )

        except Exception as e:
            logger.error(f"❌ Error in batch_toggle_command: {e}")
            await update.message.reply_text(f"❌ <b>Error</b>: <code>{str(e)[:200]}</code>", parse_mode='HTML')

    async def _execute_batch_toggle(self, update, context, visibility_action: str, repos_str: str):
        """Execute the batch toggle operation"""
        try:
            user_id = update.effective_user.id if hasattr(update, 'effective_user') else update.from_user.id

            # Get active API
            active_api = await self.db.get_active_api(user_id)
            if not active_api:
                await update.edit_message_text(
                    "❌ <b>No Active API</b>\nPlease load a GitHub API first.",
                    parse_mode='HTML'
                )
                return

            github_api = GitHubAPI(active_api['github_token'], active_api['github_username'])

            # Parse repository list
            repo_list = parse_repository_list(repos_str, active_api['github_username'])

            # Show processing message
            await update.edit_message_text(
                f"🔄 <b>Processing Batch Operation...</b>\n\n"
                f"Processing {len(repo_list)} repositories...\n"
                f"This may take a few seconds.",
                parse_mode='HTML'
            )

            results = {}

            if visibility_action == 'toggle':
                # Auto-toggle: check current status first
                for owner, repo_name in repo_list:
                    try:
                        repo_info = await github_api.get_repository(owner, repo_name)
                        if repo_info:
                            # Toggle: if private make public, if public make private
                            make_private = not repo_info['private']
                            success, message = await github_api.toggle_repository_visibility(owner, repo_name, make_private)
                            results[f"{owner}/{repo_name}"] = (success, message, "private" if make_private else "public")
                        else:
                            results[f"{owner}/{repo_name}"] = (False, "Repository not found", "unknown")
                    except Exception as e:
                        results[f"{owner}/{repo_name}"] = (False, str(e), "unknown")

                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.2)

            else:
                # Specific visibility action
                make_private = visibility_action == 'private'

                for owner, repo_name in repo_list:
                    try:
                        success, message = await github_api.toggle_repository_visibility(owner, repo_name, make_private)
                        results[f"{owner}/{repo_name}"] = (success, message, visibility_action)
                    except Exception as e:
                        results[f"{owner}/{repo_name}"] = (False, str(e), visibility_action)

                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.2)

            # Update database and create results
            success_count = 0
            for repo_full_name, (success, message, new_visibility) in results.items():
                owner, repo_name = repo_full_name.split('/', 1)

                if success:
                    success_count += 1
                    await self.db.update_repository_status(user_id, repo_name, owner, new_visibility)
                    await self.db.log_action(user_id, f"batch_{visibility_action}", repo_full_name, "success")
                else:
                    await self.db.log_action(user_id, f"batch_{visibility_action}", repo_full_name, "failed")

            # Format results message
            result_text = (
                f"📊 <b>Batch Operation Results</b>\n\n"
                f"<b>Action:</b> {visibility_action.title()}\n"
                f"<b>Success:</b> {success_count}/{len(results)}\n\n"
            )

            for repo_name, (success, message, new_visibility) in results.items():
                status = "✅" if success else "❌"
                if success:
                    result_text += f"{status} <code>{repo_name}</code> → <b>{new_visibility}</b>\n"
                else:
                    result_text += f"{status} <code>{repo_name}</code> - {message[:50]}{'...' if len(message) > 50 else ''}\n"

            # Split message if too long
            if len(result_text) > 4000:
                chunks = [result_text[i:i+4000] for i in range(0, len(result_text), 4000)]
                for i, chunk in enumerate(chunks):
                    if i == 0:
                        await update.edit_message_text(chunk, parse_mode='HTML')
                    else:
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=f"📊 <b>Results</b> (Part {i+1})\n\n{chunk}",
                            parse_mode='HTML'
                        )
            else:
                await update.edit_message_text(result_text, parse_mode='HTML')

        except Exception as e:
            logger.error(f"❌ Error in _execute_batch_toggle: {e}")
            try:
                await update.edit_message_text(f"❌ <b>Batch operation failed</b>: <code>{str(e)[:200]}</code>", parse_mode='HTML')
            except:
                pass

    async def logs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /logs command - Now with real activity logs"""
        try:
            user_id = update.effective_user.id

            if not self._is_authorized(user_id):
                await update.message.reply_text(
                    "❌ <b>Access Denied</b>\n"
                    "You are not authorized to use this command.",
                    parse_mode='HTML'
                )
                return

            logs = await self.db.get_user_logs(user_id, 20)

            if not logs:
                await update.message.reply_text(
                    "📋 <b>No Activity Logs</b>\n\n"
                    "No recent activity found.\n\n"
                    "Activity will be logged when you:\n"
                    "• Add GitHub APIs\n"
                    "• Load APIs\n"
                    "• Change repository visibility\n"
                    "• Perform other actions",
                    parse_mode='HTML'
                )
                return

            logs_text = format_logs(logs)

            # Add summary
            success_count = sum(1 for log in logs if log['status'] == 'success')
            failed_count = len(logs) - success_count

            header = (
                f"📋 <b>Activity Logs</b> (Last 20)\n\n"
                f"<b>Summary:</b> {success_count} successful, {failed_count} failed\n\n"
            )

            full_text = header + logs_text

            if len(full_text) > 4000:
                await update.message.reply_text(header, parse_mode='HTML')
                await update.message.reply_text(logs_text, parse_mode='Markdown')
            else:
                await update.message.reply_text(full_text, parse_mode='HTML')

        except Exception as e:
            logger.error(f"❌ Error in logs_command: {e}")
            await update.message.reply_text(f"❌ <b>Error</b>: <code>{str(e)[:200]}</code>", parse_mode='HTML')

    async def authorize_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /authorize command - Only for hardcoded admins"""
        try:
            user_id = update.effective_user.id

            if not Config.is_admin(user_id):
                await update.message.reply_text(
                    "❌ <b>Admin Access Required</b>\n"
                    "This command requires administrator privileges.\n\n"
                    f"Your User ID: <code>{user_id}</code>",
                    parse_mode='HTML'
                )
                return

            if len(context.args) != 1:
                await update.message.reply_text(
                    "❌ <b>Invalid Usage</b>\n"
                    "Usage: <code>/authorize &lt;user_id&gt;</code>",
                    parse_mode='HTML'
                )
                return

            try:
                target_user_id = int(context.args[0])
            except ValueError:
                await update.message.reply_text(
                    "❌ <b>Invalid User ID</b>\n"
                    "Please provide a valid numeric user ID.",
                    parse_mode='HTML'
                )
                return

            success = await self.db.authorize_user(target_user_id)

            if success:
                await update.message.reply_text(
                    f"✅ <b>User Authorized</b>\n"
                    f"User ID <code>{target_user_id}</code> has been authorized.\n\n"
                    f"💡 They can now use all bot features.",
                    parse_mode='HTML'
                )
            else:
                await update.message.reply_text(
                    f"❌ <b>Authorization Failed</b>\n"
                    f"Could not authorize user ID <code>{target_user_id}</code>. User may not exist.",
                    parse_mode='HTML'
                )

        except Exception as e:
            logger.error(f"❌ Error in authorize_command: {e}")
            await update.message.reply_text(f"❌ <b>Error</b>: <code>{str(e)[:200]}</code>", parse_mode='HTML')

    async def revoke_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /revoke command - Only for hardcoded admins"""
        try:
            user_id = update.effective_user.id

            if not Config.is_admin(user_id):
                await update.message.reply_text(
                    "❌ <b>Admin Access Required</b>\n"
                    "This command requires administrator privileges.",
                    parse_mode='HTML'
                )
                return

            if len(context.args) != 1:
                await update.message.reply_text(
                    "❌ <b>Invalid Usage</b>\n"
                    "Usage: <code>/revoke &lt;user_id&gt;</code>",
                    parse_mode='HTML'
                )
                return

            try:
                target_user_id = int(context.args[0])
            except ValueError:
                await update.message.reply_text(
                    "❌ <b>Invalid User ID</b>\n"
                    "Please provide a valid numeric user ID.",
                    parse_mode='HTML'
                )
                return

            # Prevent revoking hardcoded admins
            if Config.is_admin(target_user_id):
                await update.message.reply_text(
                    f"❌ <b>Cannot Revoke Admin</b>\n"
                    f"User ID <code>{target_user_id}</code> is a hardcoded administrator and cannot be revoked.",
                    parse_mode='HTML'
                )
                return

            success = await self.db.revoke_user(target_user_id)

            if success:
                await update.message.reply_text(
                    f"✅ <b>User Access Revoked</b>\n"
                    f"User ID <code>{target_user_id}</code> access has been revoked.",
                    parse_mode='HTML'
                )
            else:
                await update.message.reply_text(
                    f"❌ <b>Revocation Failed</b>\n"
                    f"Could not revoke access for user ID <code>{target_user_id}</code>.",
                    parse_mode='HTML'
                )

        except Exception as e:
            logger.error(f"❌ Error in revoke_command: {e}")
            await update.message.reply_text(f"❌ <b>Error</b>: <code>{str(e)[:200]}</code>", parse_mode='HTML')

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command with HTML formatting"""
        help_text = """
🤖 <b>GitHub Repository Visibility Bot</b>

<b>🔑 GitHub API Management:</b>
• <code>/add_api &lt;name&gt; &lt;token&gt;</code> - Add new GitHub API credentials
• <code>/list_apis</code> - Show all your GitHub APIs
• <code>/load_api &lt;name&gt;</code> - Switch to specific GitHub API
• <code>/current_api</code> - Show currently active API
• <code>/remove_api &lt;name&gt;</code> - Remove GitHub API credentials

<b>📁 Repository Management:</b>
• <code>/list_repos</code> - List all repositories from current API
• <code>/public &lt;repo_name&gt;</code> - Make repository public
• <code>/private &lt;repo_name&gt;</code> - Make repository private
• <code>/repo_status &lt;repo_name&gt;</code> - Check current repository visibility
• <code>/batch_toggle &lt;repos&gt;</code> - Batch toggle multiple repositories

<b>📊 Activity &amp; Logs:</b>
• <code>/logs</code> - Show recent activity logs

<b>👤 Admin Commands:</b>
• <code>/authorize &lt;user_id&gt;</code> - Authorize user access
• <code>/revoke &lt;user_id&gt;</code> - Revoke user access

<b>ℹ️ General:</b>
• <code>/start</code> - Initialize and check your status
• <code>/help</code> - Show this help message

<b>💡 Tips:</b>
- Repository names can include owner: <code>owner/repo</code> or just <code>repo</code>
- All operations are logged for audit purposes
- Your GitHub tokens are encrypted and stored securely

<b>🔒 Security:</b>
- GitHub tokens are encrypted before storage
- All actions are logged for audit purposes
- Access control prevents unauthorized usage

<b>🚀 Getting Started:</b>
1. Add your GitHub token: <code>/add_api personal YOUR_TOKEN</code>
2. Load the API: <code>/load_api personal</code>
3. List your repos: <code>/list_repos</code>
4. Manage visibility: <code>/public repo-name</code> or <code>/private repo-name</code>
        """

        try:
            await update.message.reply_text(help_text, parse_mode='HTML')
        except Exception as e:
            logger.error(f"❌ Error in help_command: {e}")
            # Fallback without formatting if there's an issue
            await update.message.reply_text(help_text.replace('<b>', '').replace('</b>', '').replace('<code>', '').replace('</code>', ''))

    # Callback query handlers
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks - Now functional"""
        try:
            query = update.callback_query
            await query.answer()

            if query.data == "cancel":
                await query.edit_message_text("❌ <b>Operation Cancelled</b>", parse_mode='HTML')
                return

            if query.data.startswith("remove_api:"):
                api_name = query.data.split(":", 1)[1]
                user_id = query.from_user.id

                success = await self.db.remove_github_api(user_id, api_name)

                if success:
                    await query.edit_message_text(
                        f"✅ <b>API Removed Successfully</b>\n\n"
                        f"API <code>{api_name}</code> has been removed from your account.\n\n"
                        f"💡 Use <code>/list_apis</code> to see your remaining APIs",
                        parse_mode='HTML'
                    )
                    await self.db.log_action(user_id, "remove_api", api_name, "success")
                else:
                    await query.edit_message_text(
                        f"❌ <b>Failed to Remove API</b>\n\n"
                        f"Could not remove API <code>{api_name}</code>.\n"
                        f"Please try again or contact support.",
                        parse_mode='HTML'
                    )

            elif query.data.startswith("batch_confirm:"):
                # Handle batch toggle confirmation
                parts = query.data.split(":", 2)
                if len(parts) == 3:
                    visibility_action = parts[1]
                    repos_str = parts[2]
                    await self._execute_batch_toggle(query, context, visibility_action, repos_str)
                else:
                    await query.edit_message_text("❌ <b>Invalid confirmation data</b>", parse_mode='HTML')

        except Exception as e:
            logger.error(f"❌ Error in button_callback: {e}")
            try:
                await update.callback_query.edit_message_text(f"❌ <b>Error</b>: <code>{str(e)[:200]}</code>", parse_mode='HTML')
            except:
                pass

    # Error handler
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        logger.error(f"Traceback: {traceback.format_exc()}")

        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ <b>An Error Occurred</b>\n"
                    "Something went wrong. Please try again later or contact support.",
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Could not send error message: {e}")
