import discord
from discord.ext import commands, tasks
from datetime import datetime
import asyncio

class AutoRead(commands.Cog):
    """
    Automatically mark all messages as read in background.
    No commands needed - runs automatically on startup.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot_name = getattr(bot, '_bot_name', 'Bot')
        
        # Loop settings
        self.loop_interval = 30  # seconds between checks
        
        # Stats
        self.total_marked = 0
        self.last_run = None
        
        self._log("AutoRead initialized - will start on ready")

    def _log(self, msg: str, level: str = "INFO") -> None:
        """Centralized logging"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{self.bot_name}] [AutoRead] [{level}] {msg}")

    @tasks.loop(seconds=30)
    async def auto_read_loop(self):
        """Background loop to mark messages as read"""
        try:
            marked_count = 0
            
            # Mark all DM channels as read
            for channel in self.bot.private_channels:
                if isinstance(channel, discord.DMChannel):
                    try:
                        await channel.read_state.ack()
                        marked_count += 1
                    except:
                        pass
            
            # Mark all guild channels as read
            for guild in self.bot.guilds:
                for channel in guild.text_channels:
                    try:
                        # Check if there are unread messages
                        last_message_id = channel.last_message_id
                        if last_message_id:
                            await channel.read_state.ack(last_message_id)
                            marked_count += 1
                    except:
                        pass  # Silent fail for rate limits
                    
                    # Small delay to avoid rate limits
                    await asyncio.sleep(0.05)
            
            self.total_marked += marked_count
            self.last_run = datetime.now()
            
            if marked_count > 0:
                self._log(f"✓ Marked {marked_count} channels as read (Total: {self.total_marked})")
            
        except Exception as e:
            self._log(f"Loop error: {e}", "ERROR")

    @auto_read_loop.before_loop
    async def before_auto_read(self):
        """Wait until bot is ready"""
        await self.bot.wait_until_ready()
        self._log("Starting auto-read loop...")

    def cog_unload(self):
        """Stop loop when unloading"""
        self.auto_read_loop.stop()
        self._log("Auto-read loop stopped")

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Auto-start loop when bot is ready"""
        if not self.auto_read_loop.is_running():
            self.auto_read_loop.start()
            self._log("✓ AutoRead started automatically")
            self._log(f"   Interval: {self.loop_interval}s")
            self._log(f"   Guilds: {len(self.bot.guilds)}")

async def setup(bot: commands.Bot) -> None:
    """Setup cog"""
    await bot.add_cog(AutoRead(bot))
