import discord
from discord.ext import commands, tasks
import json
import asyncio
import os
from datetime import datetime
import random
from typing import Optional, Dict, List

class AutoConversation(commands.Cog):
    """Automated conversation system with multiple channels"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
        # Paths
        self.data_dir = "data"
        self.conversations_dir = "conversations"
        self.state_file = os.path.join(self.data_dir, "conversation_state.json")
        self.config_file = os.path.join(self.data_dir, "config.json")
        
        # Initialize
        self._ensure_directories()
        self.config = self._load_config()
        self.conversations = self._load_conversations()
        self.slowdown_active = False
        
        # Start monitor
        self.conversation_monitor.start()
    
    def cog_unload(self):
        """Cleanup when cog unloads"""
        self.conversation_monitor.cancel()
    
    # ==================== SETUP & CONFIGURATION ====================
    
    def _ensure_directories(self):
        """Create required directories"""
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.conversations_dir, exist_ok=True)
    
    def _load_config(self) -> Dict:
        """Load configuration with defaults"""
        defaults = {
            "channels": {},
            "typing_delay_min": 2.0,
            "typing_delay_max": 5.0,
            "slowdown_delay": 10,
            "enable_typing_indicator": True,
            "enable_reply_chains": True,
            "auto_recover_from_ratelimit": True,
            "log_to_terminal": True,
            "show_typing_logs": True,
            "show_message_preview_length": 50
        }
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return {**defaults, **json.load(f)}
        except FileNotFoundError:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(defaults, f, indent=2)
            self._log(f"✅ Created config: {self.config_file}")
            return defaults
        except json.JSONDecodeError:
            self._log(f"⚠️ Invalid config, using defaults")
            return defaults
    
    def _load_conversations(self) -> Dict[str, List[Dict]]:
        """Load all conversation files"""
        conversations = {}
        
        if not os.path.exists(self.conversations_dir):
            self._log(f"⚠️ Folder not found: {self.conversations_dir}")
            return conversations
        
        for filename in os.listdir(self.conversations_dir):
            if not filename.endswith('.json'):
                continue
                
            name = filename[:-5]
            filepath = os.path.join(self.conversations_dir, filename)
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    conversations[name] = data
                    self._log(f"✅ Loaded: {name} ({len(data)} messages)")
            except json.JSONDecodeError:
                self._log(f"❌ Invalid JSON: {filename}")
            except Exception as e:
                self._log(f"❌ Error: {filename} - {e}")
        
        self._log(f"📚 Total conversations: {len(conversations)}")
        return conversations
    
    def _save_config(self, config: Dict) -> bool:
        """Save configuration"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            self._log(f"❌ Save error: {e}")
            return False
    
    # ==================== STATE MANAGEMENT ====================
    
    def _load_state(self) -> Optional[Dict]:
        """Load conversation state"""
        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None
    
    def _save_state(self, state: Dict) -> bool:
        """Save conversation state"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
            return True
        except Exception as e:
            self._log(f"❌ State save error: {e}")
            return False
    
    def _clear_state(self):
        """Remove state file"""
        if os.path.exists(self.state_file):
            os.remove(self.state_file)
    
    # ==================== UTILITY ====================
    
    def _is_primary_bot(self) -> bool:
        """Check if Bot 1"""
        return getattr(self.bot, '_is_primary', False)
    
    def _get_bot_number(self) -> int:
        """Get bot number"""
        return 1 if self._is_primary_bot() else 2
    
    def _log(self, message: str):
        """Log to terminal"""
        config = self._load_config()
        if config.get("log_to_terminal", True):
            print(message)
    
    def _calculate_typing_delay(self, config: Dict) -> float:
        """Calculate random typing delay"""
        min_d = config.get("typing_delay_min", 2.0)
        max_d = config.get("typing_delay_max", 5.0)
        return random.uniform(min_d, max_d)
    
    async def _parse_channel(self, ctx, channel_input: Optional[str]) -> Optional[discord.TextChannel]:
        """Parse channel from various formats"""
        if not channel_input:
            return ctx.channel
        
        channel_str = channel_input.strip('<>#')
        
        try:
            channel_id = int(channel_str.split('/')[-1])
            channel = self.bot.get_channel(channel_id)
            if channel:
                return channel
        except (ValueError, AttributeError):
            pass
        
        try:
            return await commands.TextChannelConverter().convert(ctx, channel_input)
        except commands.BadArgument:
            return None
    
    # ==================== CHANNEL COMMANDS ====================
    
    @commands.group(name="channel", invoke_without_command=True)
    async def channel_group(self, ctx):
        """Channel management commands"""
        if not self._is_primary_bot():
            return
        
        self._log("💡 Usage: !channel add/remove/list")
    
    @channel_group.command(name="add")
    async def channel_add(self, ctx, name: str, channel: Optional[str] = None):
        """
        Add a channel
        Usage: !channel add general #channel
        """
        if not self._is_primary_bot():
            return
        
        target = await self._parse_channel(ctx, channel)
        if not target:
            self._log("❌ Invalid channel")
            return
        
        config = self._load_config()
        if "channels" not in config:
            config["channels"] = {}
        
        config["channels"][name] = target.id
        
        if self._save_config(config):
            self._log(f"✅ Added '{name}' → #{target.name} (ID: {target.id})")
        else:
            self._log("❌ Failed to add")
    
    @channel_group.command(name="remove")
    async def channel_remove(self, ctx, name: str):
        """
        Remove a channel
        Usage: !channel remove general
        """
        if not self._is_primary_bot():
            return
        
        config = self._load_config()
        channels = config.get("channels", {})
        
        if name not in channels:
            self._log(f"❌ Channel '{name}' not found")
            return
        
        del config["channels"][name]
        self._save_config(config)
        self._log(f"✅ Removed '{name}'")
    
    @channel_group.command(name="list")
    async def channel_list(self, ctx):
        """
        List all channels
        Usage: !channel list
        """
        config = self._load_config()
        channels = config.get("channels", {})
        
        if not channels:
            self._log("📭 No channels configured")
            self._log("💡 Use: !channel add <name> <#channel>")
            return
        
        self._log("\n📺 Configured Channels:")
        for name, channel_id in channels.items():
            channel = self.bot.get_channel(channel_id)
            ch_name = f"#{channel.name}" if channel else f"ID:{channel_id}"
            self._log(f"  • {name} → {ch_name}")
        self._log("")
    
    # ==================== CONVERSATION COMMANDS ====================
    
    @commands.group(name="conv", invoke_without_command=True)
    async def conv_group(self, ctx):
        """Conversation management commands"""
        if not self._is_primary_bot():
            return
        
        self._log("💡 Usage: !conv start/stop/list/reload")
    
    @conv_group.command(name="list")
    async def conv_list(self, ctx):
        """
        List available conversations
        Usage: !conv list
        """
        if not self.conversations:
            self._log("📭 No conversations")
            self._log(f"💡 Add JSON files to '{self.conversations_dir}/'")
            return
        
        self._log(f"\n📚 Conversations ({self.conversations_dir}/):")
        for name, messages in self.conversations.items():
            self._log(f"  • {name} ({len(messages)} messages)")
        self._log("")
    
    @conv_group.command(name="reload")
    async def conv_reload(self, ctx):
        """
        Reload conversations
        Usage: !conv reload
        """
        if not self._is_primary_bot():
            return
        
        self.conversations = self._load_conversations()
    
    @conv_group.command(name="start")
    async def conv_start(self, ctx, channel_name: str, conversation_name: str):
        """
        Start conversation in channel
        Usage: !conv start general casual
        """
        if not self._is_primary_bot():
            return
        
        # Check conversation exists
        if conversation_name not in self.conversations:
            self._log(f"❌ Conversation '{conversation_name}' not found")
            avail = ', '.join(self.conversations.keys())
            self._log(f"💡 Available: {avail}")
            return
        
        # Check channel exists
        config = self._load_config()
        channels = config.get("channels", {})
        
        if channel_name not in channels:
            self._log(f"❌ Channel '{channel_name}' not configured")
            self._log("💡 Use: !channel list")
            return
        
        channel_id = channels[channel_name]
        
        # Check if already running
        state = self._load_state()
        if state and state.get("active"):
            self._log("⚠️ Conversation running (!conv stop first)")
            return
        
        # Start conversation
        conv = self.conversations[conversation_name]
        state = {
            "active": True,
            "channel_name": channel_name,
            "channel_id": channel_id,
            "conversation_name": conversation_name,
            "current_index": 0,
            "next_bot": conv[0]["bot"],
            "last_message_id": None,
            "total_messages": len(conv),
            "started_at": datetime.now().isoformat()
        }
        
        if self._save_state(state):
            channel = self.bot.get_channel(channel_id)
            ch_display = f"#{channel.name}" if channel else channel_name
            self._log(f"🎬 Starting '{conversation_name}' in {ch_display} ({len(conv)} messages)")
        else:
            self._log("❌ Failed to start")
    
    @conv_group.command(name="stop")
    async def conv_stop(self, ctx):
        """
        Stop current conversation
        Usage: !conv stop
        """
        if not self._is_primary_bot():
            return
        
        state = self._load_state()
        if not state or not state.get("active"):
            self._log("⚠️ No active conversation")
            return
        
        self._clear_state()
        self.slowdown_active = False
        self._log("⏹️ Stopped")
    
    # ==================== CONFIG COMMANDS ====================
    
    @commands.command(name="reloadconfig")
    async def reload_config(self, ctx):
        """Reload config"""
        self.config = self._load_config()
        self._log(f"🔄 Bot {self._get_bot_number()}: Config reloaded")
    
    @commands.command(name="showconfig")
    async def show_config(self, ctx):
        """Show configuration"""
        config = self._load_config()
        bot_num = self._get_bot_number()
        
        self._log(f"\n⚙️ Bot {bot_num} Config:")
        self._log(f"📁 Config: {self.config_file}")
        self._log(f"📂 Conversations: {self.conversations_dir}/")
        
        channels = config.get('channels', {})
        self._log(f"📺 Channels: {len(channels)}")
        
        self._log(f"⏱️ Typing: {config.get('typing_delay_min')}-{config.get('typing_delay_max')}s")
        self._log(f"⌨️ Indicator: {'ON' if config.get('enable_typing_indicator') else 'OFF'}")
        self._log(f"↪️ Replies: {'ON' if config.get('enable_reply_chains') else 'OFF'}")
        self._log("")
    
    # ==================== MONITOR ====================
    
    async def _handle_ratelimit(self, config: Dict):
        """Handle rate limit"""
        if not self.slowdown_active and config.get("auto_recover_from_ratelimit", True):
            self.slowdown_active = True
            delay = config.get("slowdown_delay", 10)
            self._log(f"⚠️ Rate limited! Waiting {delay}s...")
            await asyncio.sleep(delay)
    
    @tasks.loop(seconds=1)
    async def conversation_monitor(self):
        """Main conversation loop"""
        try:
            await self.bot.wait_until_ready()
            
            # Load fresh state
            state = self._load_state()
            if not state or not state.get("active"):
                return
            
            my_bot = self._get_bot_number()
            
            # Check turn
            if state.get("next_bot") != my_bot:
                return
            
            # Load conversation
            conv_name = state.get("conversation_name")
            if conv_name not in self.conversations:
                self._log(f"❌ Conversation '{conv_name}' not found")
                self._clear_state()
                return
            
            conv = self.conversations[conv_name]
            index = state.get("current_index", 0)
            
            # Check if conversation ended
            if index >= len(conv):
                self._clear_state()
                self.slowdown_active = False
                self._log(f"✅ Completed '{conv_name}' ({len(conv)} messages)")
                return
            
            current = conv[index]
            if current["bot"] != my_bot:
                state["current_index"] = index + 1
                self._save_state(state)
                return
            
            # Get channel
            config = self._load_config()
            channel_id = state.get("channel_id")
            
            if not channel_id:
                self._clear_state()
                self._log(f"❌ Bot {my_bot}: No channel")
                return
            
            channel = self.bot.get_channel(channel_id)
            if not channel:
                self._clear_state()
                self._log(f"❌ Bot {my_bot}: Channel not found")
                return
            
            # Send message
            try:
                # Check state before typing
                state = self._load_state()
                if not state or not state.get("active"):
                    return
                
                # Typing indicator
                if config.get("enable_typing_indicator", True):
                    delay = self._calculate_typing_delay(config)
                    
                    if config.get("show_typing_logs", True):
                        self._log(f"⌨️ Bot {my_bot} typing {delay:.1f}s...")
                    
                    # Check during typing
                    chunks = int(delay)
                    remainder = delay - chunks
                    
                    async with channel.typing():
                        for _ in range(chunks):
                            state = self._load_state()
                            if not state or not state.get("active"):
                                self._log(f"⏹️ Bot {my_bot}: Stopped during typing")
                                return
                            await asyncio.sleep(1)
                        
                        if remainder > 0:
                            await asyncio.sleep(remainder)
                
                # Final check
                state = self._load_state()
                if not state or not state.get("active"):
                    self._log(f"⏹️ Bot {my_bot}: Stopped before send")
                    return
                
                # Send
                if state.get("last_message_id") and config.get("enable_reply_chains", True):
                    try:
                        prev_msg = await channel.fetch_message(state["last_message_id"])
                        sent_msg = await prev_msg.reply(current["msg"])
                    except discord.NotFound:
                        sent_msg = await channel.send(current["msg"])
                else:
                    sent_msg = await channel.send(current["msg"])
                
                # Log
                preview_len = config.get("show_message_preview_length", 50)
                preview = current['msg'][:preview_len]
                if len(current['msg']) > preview_len:
                    preview += '...'
                self._log(f"✅ Bot {my_bot}: {preview}")
                
                # Update state
                next_index = index + 1
                next_bot = conv[next_index]["bot"] if next_index < len(conv) else None
                
                state.update({
                    "current_index": next_index,
                    "next_bot": next_bot,
                    "last_message_id": sent_msg.id
                })
                
                if not self._save_state(state):
                    self._log(f"❌ Failed to save state")
                    return
                
                if self.slowdown_active:
                    self.slowdown_active = False
                    self._log("✅ Recovered from rate limit")
                
            except discord.HTTPException as e:
                if e.status == 429 or e.code == 50035:
                    self._log(f"⚠️ Rate limit ({e.status or e.code})")
                    await self._handle_ratelimit(config)
                else:
                    self._log(f"❌ HTTP Error: {e}")
                    self._clear_state()
            except discord.Forbidden:
                self._clear_state()
                self._log("❌ Missing permissions")
            except Exception as e:
                self._log(f"❌ Error: {e}")
                await asyncio.sleep(5)
        
        except Exception as e:
            self._log(f"❌ Monitor error: {e}")
    
    @conversation_monitor.before_loop
    async def before_monitor(self):
        """Wait for bot ready"""
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(AutoConversation(bot))
