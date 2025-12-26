import discord
from discord.ext import commands
import re
import asyncio
import json
import os
import random
from typing import Optional, Tuple
from datetime import datetime


CONFIG_FILE = "tracked_bots.json"
PROCESS_FILE = "process_mode.json"


class AutoButtonClick(commands.Cog):
    """
    Auto-click Discord buttons from tracked bots with two operational modes.
    Process 1: Bot 1 skips buttons after name changes, Bot 2 clicks skipped + random extras
    Process 2: Both bots click all buttons together
    """
    
    # Shared class variables between both bot instances
    skipped_buttons = []
    current_process = 1
    
    # Configuration constants
    BOT1_MIN_DELAY = 8.0  # EDIT: Bot 1 minimum delay
    BOT1_MAX_DELAY = 10.0  # EDIT: Bot 1 maximum delay
    BOT2_MIN_DELAY = 10.0  # EDIT: Bot 2 minimum delay
    BOT2_MAX_DELAY = 13.0  # EDIT: Bot 2 maximum delay
    RANDOM_CLICK_CHANCE = 0.15  # 15% chance for Bot 2 to click random extras
    DEFAULT_SKIP_COUNT = 3  # Number of buttons to skip after name change
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.is_primary = getattr(bot, '_is_primary', True)
        self.bot_name = getattr(bot, '_bot_name', 'Bot')
        self.tracked_bots = {}
        self.clicked_messages = set()
        self.skip_count = 0
        
        # Load persistent data
        self.load_config()
        self.load_process_mode()
        
        self._log(f"Initialized {'Primary (Bot 1)' if self.is_primary else 'Secondary (Bot 2)'}")


    def _log(self, message: str, level: str = "INFO") -> None:
        """Centralized logging with timestamps"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{self.bot_name}] [{level}] {message}")


    def parse_channel_link(self, channel_link: str) -> Tuple[Optional[int], Optional[int]]:
        """Parse Discord channel link to extract guild_id and channel_id"""
        match = re.match(r"https?://discord\.com/channels/(\d+)/(\d+)", channel_link)
        if not match:
            return None, None
        guild_id, channel_id = match.groups()
        return int(guild_id), int(channel_id)


    def save_config(self) -> None:
        """Save tracked bots configuration to JSON file with error handling"""
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.tracked_bots, f, indent=4)
            self._log(f"Configuration saved ({len(self.tracked_bots)} channels)")
        except IOError as e:
            self._log(f"Failed to save config: {e}", "ERROR")


    def load_config(self) -> None:
        """Load tracked bots configuration from JSON file"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    self.tracked_bots = {int(k): int(v) for k, v in data.items()}
                    if self.tracked_bots:
                        self._log(f"Loaded {len(self.tracked_bots)} tracked channels")
        except (IOError, json.JSONDecodeError) as e:
            self._log(f"Failed to load config: {e}", "ERROR")
            self.tracked_bots = {}


    def load_process_mode(self) -> None:
        """Load the current process mode from file"""
        try:
            if os.path.exists(PROCESS_FILE):
                with open(PROCESS_FILE, "r") as f:
                    data = json.load(f)
                    AutoButtonClick.current_process = data.get("process", 1)
                    self._log(f"Process mode: {AutoButtonClick.current_process}")
            else:
                self.save_process_mode()
        except (IOError, json.JSONDecodeError) as e:
            self._log(f"Failed to load process mode: {e}", "ERROR")


    def save_process_mode(self) -> None:
        """Save the current process mode to file"""
        try:
            with open(PROCESS_FILE, "w") as f:
                json.dump({"process": AutoButtonClick.current_process}, f, indent=4)
        except IOError as e:
            self._log(f"Failed to save process mode: {e}", "ERROR")


    def get_delay(self) -> float:
        """Get random delay based on bot type"""
        if self.is_primary:
            return random.uniform(self.BOT1_MIN_DELAY, self.BOT1_MAX_DELAY)
        else:
            return random.uniform(self.BOT2_MIN_DELAY, self.BOT2_MAX_DELAY)


    @commands.command(name="process", help="Change process mode. Usage: !process <1 or 2>")
    async def change_process(self, ctx: commands.Context, mode: int) -> None:
        """Switch between Process 1 and Process 2 modes"""
        if mode not in [1, 2]:
            self._log("Invalid process mode", "WARN")
            return
        
        AutoButtonClick.current_process = mode
        self.save_process_mode()
        
        # Reset state when switching modes
        AutoButtonClick.skipped_buttons.clear()
        self.skip_count = 0
        self.clicked_messages.clear()
        
        self._log("=" * 50)
        if mode == 1:
            self._log("✓ Switched to Process 1")
            self._log("  → Bot 1: Skips 3 buttons after name change")
            self._log(f"  → Bot 1: Delay {self.BOT1_MIN_DELAY}s-{self.BOT1_MAX_DELAY}s")
            self._log("  → Bot 2: Clicks skipped + random extras")
            self._log(f"  → Bot 2: Delay {self.BOT2_MIN_DELAY}s-{self.BOT2_MAX_DELAY}s")
        else:
            self._log("✓ Switched to Process 2")
            self._log("  → Both bots click all buttons")
            self._log(f"  → Bot 1: Delay {self.BOT1_MIN_DELAY}s-{self.BOT1_MAX_DELAY}s")
            self._log(f"  → Bot 2: Delay {self.BOT2_MIN_DELAY}s-{self.BOT2_MAX_DELAY}s")
        self._log("=" * 50)


    @commands.command(name="stopbot", help="Stop a specific bot. Usage: !stopbot <1 or 2>")
    async def stop_bot(self, ctx: commands.Context, bot_number: int) -> None:
        """Gracefully stop a specific bot instance"""
        if bot_number not in [1, 2]:
            self._log("Invalid bot number", "WARN")
            return
        
        if (bot_number == 1 and self.is_primary) or (bot_number == 2 and not self.is_primary):
            self._log(f"🛑 Shutting down Bot {bot_number}...")
            await self.bot.close()
        else:
            self._log(f"Cannot stop Bot {bot_number} from this instance", "WARN")


    @commands.command(name="status", help="Show current bot status and configuration")
    async def show_status(self, ctx: commands.Context) -> None:
        """Display comprehensive bot status"""
        mode_desc = "Bot 1 skips, Bot 2 clicks skipped + extras" if AutoButtonClick.current_process == 1 else "Both bots click together"
        
        self._log("=" * 50)
        self._log(f"Process Mode: {AutoButtonClick.current_process} ({mode_desc})")
        self._log(f"Bot Type: {'Primary (Bot 1)' if self.is_primary else 'Secondary (Bot 2)'}")
        self._log(f"Delay Range: {self.get_delay():.2f}s (avg)")
        self._log(f"Tracked Channels: {len(self.tracked_bots)}")
        self._log(f"Clicked Messages: {len(self.clicked_messages)}")
        self._log(f"Skipped Queue: {len(AutoButtonClick.skipped_buttons)}")
        if self.is_primary:
            self._log(f"Remaining Skips: {self.skip_count}")
        self._log("=" * 50)


    @commands.command(name="click", help="Track a bot. Usage: !click <bot_id> <channel_link>")
    async def track_bot(self, ctx: commands.Context, bot_id: int, channel_link: str) -> None:
        """Start tracking a bot in a specific channel"""
        guild_id, channel_id = self.parse_channel_link(channel_link)
        
        if not guild_id or not channel_id:
            self._log("Invalid channel link format", "ERROR")
            return

        guild = self.bot.get_guild(guild_id)
        if not guild:
            self._log(f"Guild not found (ID: {guild_id})", "ERROR")
            return

        channel = guild.get_channel(channel_id)
        if not channel:
            self._log(f"Channel not found (ID: {channel_id})", "ERROR")
            return

        self.tracked_bots[channel_id] = bot_id
        self.save_config()
        self._log(f"✓ Tracking bot {bot_id} in #{channel.name} ({guild.name})")


    @commands.command(name="untrack", help="Stop tracking. Usage: !untrack <channel_link>")
    async def untrack_bot(self, ctx: commands.Context, channel_link: str) -> None:
        """Stop tracking a bot in a specific channel"""
        guild_id, channel_id = self.parse_channel_link(channel_link)
        
        if not guild_id or not channel_id:
            self._log("Invalid channel link format", "ERROR")
            return

        if channel_id in self.tracked_bots:
            bot_id = self.tracked_bots[channel_id]
            del self.tracked_bots[channel_id]
            self.save_config()
            self._log(f"✓ Stopped tracking bot {bot_id} in channel {channel_id}")
        else:
            self._log(f"No bot tracked in channel {channel_id}", "WARN")


    @commands.command(name="clear", help="Clear clicked messages cache")
    async def clear_cache(self, ctx: commands.Context) -> None:
        """Clear the clicked messages cache"""
        count = len(self.clicked_messages)
        self.clicked_messages.clear()
        self._log(f"✓ Cleared {count} clicked messages from cache")


    def skip_next_buttons(self, count: int = None) -> None:
        """Set how many buttons to skip (called by AutoProfileChanger)"""
        if count is None:
            count = self.DEFAULT_SKIP_COUNT
        self.skip_count = count
        self._log(f"⏭️  Will skip next {count} buttons")


    async def click_button(self, button: discord.Button, reason: str = "") -> bool:
        """Execute button click with delay and error handling"""
        delay = self.get_delay()
        self._log(f"⏳ Waiting {delay:.2f}s{reason}...")
        
        try:
            await asyncio.sleep(delay)
            result = await button.click()
            
            if isinstance(result, str):
                self._log(f"✓ Clicked button → {result[:60]}...")
            else:
                self._log("✓ Clicked button successfully")
            return True
            
        except discord.errors.HTTPException as e:
            if e.status == 429:  # Rate limit
                self._log(f"⚠️  Rate limited! Retry after: {e.retry_after}s", "WARN")
            else:
                self._log(f"HTTP error: {e}", "ERROR")
            return False
            
        except discord.errors.NotFound:
            self._log("Button not found (message deleted?)", "WARN")
            return False
            
        except Exception as e:
            self._log(f"Unexpected error: {type(e).__name__}: {e}", "ERROR")
            return False


    def extract_buttons(self, message: discord.Message) -> list:
        """Extract all buttons from message components"""
        buttons = []
        if not message.components:
            return buttons
            
        for row in message.components:
            if hasattr(row, 'children'):
                for component in row.children:
                    if component.type == discord.ComponentType.button:
                        buttons.append(component)
        return buttons


    async def process_buttons(self, message: discord.Message) -> None:
        """Main button processing logic with mode-specific behavior"""
        # Prevent duplicate clicks
        if message.id in self.clicked_messages:
            return

        buttons = self.extract_buttons(message)
        if not buttons:
            return

        # ============ PROCESS 1 MODE ============
        if AutoButtonClick.current_process == 1:
            
            if self.is_primary:
                # Bot 1: Skip buttons if needed
                if self.skip_count > 0:
                    self.skip_count -= 1
                    AutoButtonClick.skipped_buttons.append(message)
                    self.clicked_messages.add(message.id)
                    self._log(f"⏭️  Skipped (remaining: {self.skip_count})")
                    return
                
                # Bot 1: Normal click
                self.clicked_messages.add(message.id)
                await self.click_button(buttons[0])
            
            else:
                # Bot 2: Check if should click
                should_click = False
                reason = ""
                
                if message in AutoButtonClick.skipped_buttons:
                    should_click = True
                    reason = " (skipped from Bot 1)"
                    AutoButtonClick.skipped_buttons.remove(message)
                elif random.random() < self.RANDOM_CLICK_CHANCE:
                    should_click = True
                    reason = " (random extra)"
                
                if should_click:
                    self.clicked_messages.add(message.id)
                    await self.click_button(buttons[0], reason)

        # ============ PROCESS 2 MODE ============
        elif AutoButtonClick.current_process == 2:
            # Both bots click all buttons
            self.clicked_messages.add(message.id)
            await self.click_button(buttons[0])


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Handle new messages from tracked bots"""
        if message.channel.id not in self.tracked_bots:
            return

        if message.author.id != self.tracked_bots[message.channel.id]:
            return

        await self.process_buttons(message)


    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        """Handle message edits (for updated buttons)"""
        if after.channel.id not in self.tracked_bots:
            return

        if after.author.id != self.tracked_bots[after.channel.id]:
            return

        await self.process_buttons(after)


    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        """Global error handler for commands"""
        if isinstance(error, commands.MissingRequiredArgument):
            self._log(f"Missing argument: {error.param.name}", "ERROR")
        elif isinstance(error, commands.BadArgument):
            self._log(f"Invalid argument type: {error}", "ERROR")
        elif isinstance(error, commands.CommandNotFound):
            pass  # Ignore unknown commands
        else:
            self._log(f"Command error: {type(error).__name__}: {error}", "ERROR")


async def setup(bot: commands.Bot) -> None:
    """Setup function for loading the cog"""
    await bot.add_cog(AutoButtonClick(bot))
