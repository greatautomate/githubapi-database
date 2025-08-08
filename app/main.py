import asyncio
import logging
import signal
import sys
import traceback
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from app.config import Config
from app.handlers import BotHandlers
from app.database import Database

# Configure detailed logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # Changed to DEBUG for more details
)
logger = logging.getLogger(__name__)

class GitHubVisibilityBot:
    def __init__(self):
        logger.info("=== Initializing GitHubVisibilityBot ===")

        try:
            # Validate configuration
            logger.info("Validating configuration...")
            Config.validate()

            # Log configuration status (safely)
            logger.info("Configuration Status:")
            logger.info(f"  - Telegram Bot Token: {'✅ SET' if Config.TELEGRAM_BOT_TOKEN else '❌ NOT SET'}")
            logger.info(f"  - Database URL: {'✅ SET' if Config.DATABASE_URL else '❌ NOT SET'}")
            logger.info(f"  - Encryption Key: {'✅ SET' if Config.ENCRYPTION_KEY else '❌ NOT SET'}")
            logger.info(f"  - Admin User IDs: {Config.ADMIN_USER_IDS}")
            logger.info("✅ Configuration validated successfully")

        except Exception as e:
            logger.error(f"❌ Configuration validation failed: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

        try:
            # Test database connection
            logger.info("Testing Render PostgreSQL connection...")
            db = Database()
            logger.info("✅ Render PostgreSQL database initialized successfully")

        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

        try:
            # Initialize handlers
            logger.info("Creating bot handlers...")
            self.handlers = BotHandlers()
            logger.info("✅ Bot handlers created successfully")

        except Exception as e:
            logger.error(f"❌ Failed to create bot handlers: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

        self.application = None
        self._running = False
        logger.info("✅ GitHubVisibilityBot initialization completed")

    def setup_handlers(self):
        """Setup bot command handlers"""
        logger.info("Setting up command handlers...")

        try:
            # Basic commands
            logger.debug("Adding basic command handlers...")
            self.application.add_handler(CommandHandler("start", self.handlers.start_command))
            self.application.add_handler(CommandHandler("help", self.handlers.help_command))

            # GitHub API management
            logger.debug("Adding GitHub API management handlers...")
            self.application.add_handler(CommandHandler("add_api", self.handlers.add_api_command))
            self.application.add_handler(CommandHandler("list_apis", self.handlers.list_apis_command))
            self.application.add_handler(CommandHandler("load_api", self.handlers.load_api_command))
            self.application.add_handler(CommandHandler("current_api", self.handlers.current_api_command))
            self.application.add_handler(CommandHandler("remove_api", self.handlers.remove_api_command))

            # Repository management
            logger.debug("Adding repository management handlers...")
            self.application.add_handler(CommandHandler("list_repos", self.handlers.list_repos_command))
            self.application.add_handler(CommandHandler("public", self.handlers.make_public_command))
            self.application.add_handler(CommandHandler("private", self.handlers.make_private_command))
            self.application.add_handler(CommandHandler("repo_status", self.handlers.repo_status_command))
            self.application.add_handler(CommandHandler("batch_toggle", self.handlers.batch_toggle_command))

            # Activity logs
            logger.debug("Adding activity log handlers...")
            self.application.add_handler(CommandHandler("logs", self.handlers.logs_command))

            # Admin commands
            logger.debug("Adding admin command handlers...")
            self.application.add_handler(CommandHandler("authorize", self.handlers.authorize_command))
            self.application.add_handler(CommandHandler("revoke", self.handlers.revoke_command))

            # Callback query handler
            logger.debug("Adding callback query handler...")
            self.application.add_handler(CallbackQueryHandler(self.handlers.button_callback))

            # Enhanced error handler
            logger.debug("Adding enhanced error handler...")
            async def enhanced_error_handler(update, context):
                error_message = str(context.error)
                error_type = type(context.error).__name__

                logger.error(f"=== TELEGRAM BOT ERROR ===")
                logger.error(f"Update: {update}")
                logger.error(f"Error Type: {error_type}")
                logger.error(f"Error Message: {error_message}")
                logger.error(f"Full Error: {context.error}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                logger.error("========================")

                if update and update.effective_message:
                    try:
                        await update.effective_message.reply_text(
                            f"❌ **Detailed Error Information**\n\n"
                            f"**Error Type:** `{error_type}`\n"
                            f"**Error:** `{error_message[:200]}{'...' if len(error_message) > 200 else ''}`\n\n"
                            f"**Debug Info:**\n"
                            f"• User ID: `{update.effective_user.id if update.effective_user else 'Unknown'}`\n"
                            f"• Chat ID: `{update.effective_chat.id if update.effective_chat else 'Unknown'}`\n"
                            f"• Message: `{update.effective_message.text[:50] if update.effective_message and update.effective_message.text else 'No text'}{'...' if update.effective_message and update.effective_message.text and len(update.effective_message.text) > 50 else ''}`\n\n"
                            f"Please report this error to the administrator.",
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        logger.error(f"Failed to send error message to user: {e}")

            self.application.add_error_handler(enhanced_error_handler)

            logger.info("✅ All command handlers set up successfully")

        except Exception as e:
            logger.error(f"❌ Failed to setup handlers: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    async def initialize(self):
        """Initialize the bot"""
        logger.info("Initializing Telegram application...")

        try:
            # Create application
            logger.debug(f"Creating application with token: {Config.TELEGRAM_BOT_TOKEN[:10]}...")
            self.application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
            logger.info("✅ Telegram application created successfully")

            # Setup handlers
            self.setup_handlers()
            logger.info("✅ Bot initialization completed successfully!")

        except Exception as e:
            logger.error(f"❌ Bot initialization failed: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    async def start(self):
        """Start the bot"""
        if self._running:
            logger.warning("⚠️ Bot is already running!")
            return

        try:
            await self.initialize()

            logger.info("Starting Telegram bot polling...")
            self._running = True

            # Initialize the application
            logger.debug("Initializing Telegram application...")
            await self.application.initialize()
            logger.info("✅ Application initialized")

            # Start polling
            logger.debug("Starting application...")
            await self.application.start()
            logger.info("✅ Application started")

            # Run polling
            logger.debug("Starting updater polling...")
            await self.application.updater.start_polling(
                allowed_updates=['message', 'callback_query'],
                drop_pending_updates=True
            )
            logger.info("🎉 Bot is now running and polling for updates!")
            logger.info("📱 Send /start to test the bot")

            # Keep the bot running
            while self._running:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"❌ Error during bot execution: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
        finally:
            await self.stop()

    async def stop(self):
        """Stop the bot gracefully"""
        if not self._running:
            logger.debug("Bot is not running, skipping stop")
            return

        logger.info("🛑 Stopping bot gracefully...")
        self._running = False

        try:
            if self.application:
                # Stop polling
                if hasattr(self.application, 'updater') and self.application.updater and self.application.updater.running:
                    logger.debug("Stopping updater...")
                    await self.application.updater.stop()
                    logger.info("✅ Updater stopped")

                # Stop application
                if self.application.running:
                    logger.debug("Stopping application...")
                    await self.application.stop()
                    logger.info("✅ Application stopped")

                # Shutdown
                logger.debug("Shutting down application...")
                await self.application.shutdown()
                logger.info("✅ Application shutdown completed")

            logger.info("✅ Bot stopped successfully!")

        except Exception as e:
            logger.error(f"❌ Error during bot shutdown: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        logger.debug("Setting up signal handlers...")

        def signal_handler(signum, frame):
            signal_name = signal.Signals(signum).name
            logger.info(f"📡 Received signal {signal_name} ({signum}), initiating shutdown...")
            self._running = False

        try:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            logger.debug("✅ Signal handlers set up successfully")
        except Exception as e:
            logger.warning(f"⚠️ Could not set up signal handlers: {e}")

def get_event_loop():
    """Get or create event loop safely"""
    logger.debug("Checking event loop status...")

    try:
        # Try to get existing event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            logger.info("📍 Event loop is already running (deployment environment)")
            return loop, True
        else:
            logger.info("📍 Event loop exists but not running")
            return loop, False
    except RuntimeError as e:
        logger.info(f"📍 No event loop exists, creating new one: {e}")
        # No event loop exists, create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop, False

async def run_bot():
    """Run the bot async"""
    logger.info("🚀 Starting bot runner...")

    try:
        bot = GitHubVisibilityBot()
        bot.setup_signal_handlers()

        logger.info("🎯 Bot instance created, starting execution...")
        await bot.start()

    except KeyboardInterrupt:
        logger.info("⌨️ Bot stopped by user (KeyboardInterrupt)")
    except Exception as e:
        logger.error(f"💥 Bot crashed in run_bot(): {e}")
        logger.error(f"Error Type: {type(e).__name__}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise
    finally:
        logger.info("🏁 Bot runner finished")

def main():
    """Main entry point"""
    logger.info("=" * 50)
    logger.info("🤖 GITHUB VISIBILITY BOT STARTING")
    logger.info("=" * 50)

    try:
        loop, is_running = get_event_loop()

        if is_running:
            # Event loop is already running (e.g., in deployment environment)
            logger.info("🔄 Using existing event loop")
            task = asyncio.create_task(run_bot())

            # Keep the main thread alive
            try:
                loop.run_until_complete(task)
            except RuntimeError as e:
                if "This event loop is already running" in str(e):
                    # Handle the case where we can't wait for the task
                    logger.info("🔄 Event loop already running, using alternative wait method")

                    # Create a simple blocking wait
                    import time
                    try:
                        logger.info("⏳ Keeping main thread alive...")
                        while not task.done():
                            time.sleep(1)
                    except KeyboardInterrupt:
                        logger.info("⌨️ Received interrupt signal in main thread")
                        task.cancel()
                else:
                    logger.error(f"❌ Unexpected RuntimeError: {e}")
                    raise
        else:
            # No event loop running, safe to use asyncio.run()
            logger.info("🆕 Creating new event loop")
            asyncio.run(run_bot())

        logger.info("✅ Main execution completed successfully")

    except KeyboardInterrupt:
        logger.info("⌨️ Bot stopped by user in main()")
    except Exception as e:
        logger.error(f"💥 FATAL ERROR in main(): {e}")
        logger.error(f"Error Type: {type(e).__name__}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)
    finally:
        logger.info("=" * 50)
        logger.info("🏁 GITHUB VISIBILITY BOT SHUTDOWN")
        logger.info("=" * 50)

if __name__ == "__main__":
    main()
