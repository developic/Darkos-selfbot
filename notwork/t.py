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
        self.templates_dir = os.path.join(self.conversations_dir, "templates")
        self.state_file = os.path.join(self.data_dir, "conversation_state.json")
        self.config_file = os.path.join(self.data_dir, "config.json")

        # Initialize
        self._ensure_directories()
        self.config = self._load_config()
        self.templates = self._load_templates()
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
        os.makedirs(self.templates_dir, exist_ok=True)

    def _load_config(self) -> Dict:
        """Load configuration with defaults"""
        defaults = {
            "channels": {},
            "typing_delay_min": 8.0,
            "typing_delay_max": 10.0,
            "slowdown_delay": 10,
            "enable_typing_indicator": True,
            "enable_reply_chains": True,
            "reply_chain_break_chance": 0.3,
            "auto_recover_from_ratelimit": True,
            "log_to_terminal": True,
            "show_typing_logs": True,
            "show_message_preview_length": 50,
            "natural_behavior": {
                "enable_random_pauses": True,
                "pause_chance": 0.08,
                "pause_min": 15,
                "pause_max": 45,
                "typing_variance": 0.25,
                "enable_overlap_messages": True,
                "overlap_chance": 0.12,
                "enable_typo_simulation": True,
                "typo_chance": 0.05,
                "enable_typing_interruption": True,
                "typing_interruption_chance": 0.03
            }
        }

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                # Merge natural_behavior separately to preserve nested defaults
                if 'natural_behavior' in loaded:
                    defaults['natural_behavior'].update(loaded['natural_behavior'])
                    loaded['natural_behavior'] = defaults['natural_behavior']
                return {**defaults, **loaded}
        except FileNotFoundError:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(defaults, f, indent=2)
            self._log(f"Created config: {self.config_file}")
            return defaults
        except json.JSONDecodeError:
            self._log(f"Invalid config, using defaults")
            return defaults

    def _load_templates(self) -> Dict[str, List]:
        """Load all template files - supports both arrays and full conversation snippets"""
        templates = {}

        if not os.path.exists(self.templates_dir):
            self._log(f"Templates folder not found: {self.templates_dir}")
            return templates

        for filename in os.listdir(self.templates_dir):
            if not filename.endswith('.json'):
                continue

            name = filename[:-5]
            filepath = os.path.join(self.templates_dir, filename)

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    templates[name] = data

                    # Determine type for logging
                    if isinstance(data, list):
                        if len(data) > 0 and isinstance(data[0], dict):
                            self._log(f"Loaded template: {name} ({len(data)} conversation snippets)")
                        else:
                            self._log(f"Loaded template: {name} ({len(data)} variants)")
                    else:
                        self._log(f"Loaded template: {name}")

            except json.JSONDecodeError:
                self._log(f"Invalid template JSON: {filename}")
            except Exception as e:
                self._log(f"Error loading template {filename}: {e}")

        if templates:
            self._log(f"Total templates: {len(templates)}")
        return templates

    def _load_conversations(self) -> Dict[str, List[Dict]]:
        """Load all conversation files and expand templates"""
        conversations = {}

        if not os.path.exists(self.conversations_dir):
            self._log(f"Folder not found: {self.conversations_dir}")
            return conversations

        for filename in os.listdir(self.conversations_dir):
            if not filename.endswith('.json') or filename.startswith('.'):
                continue

            # Skip templates directory
            filepath = os.path.join(self.conversations_dir, filename)
            if os.path.isdir(filepath):
                continue

            name = filename[:-5]

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Expand templates in conversation
                    expanded_data = self._expand_templates(data)
                    conversations[name] = expanded_data
                    self._log(f"Loaded: {name} ({len(expanded_data)} items)")
            except json.JSONDecodeError:
                self._log(f"Invalid JSON: {filename}")
            except Exception as e:
                self._log(f"Error loading {filename}: {e}")

        self._log(f"Total conversations: {len(conversations)}")
        return conversations

    def _expand_templates(self, conversation: List[Dict]) -> List[Dict]:
        """Expand template references in conversation - supports full conversation templates"""
        expanded = []

        for item in conversation:
            if "template" in item:
                template_name = item["template"]
                if template_name in self.templates:
                    template_data = self.templates[template_name]

                    # Pick a random variant from template
                    if isinstance(template_data, list) and len(template_data) > 0:
                        variant = random.choice(template_data)

                        # Check if variant is a full conversation snippet (list of dicts)
                        if isinstance(variant, list):
                            # It's a conversation snippet, expand it
                            for snippet_item in variant:
                                expanded.append(snippet_item)
                        elif isinstance(variant, dict):
                            # It's a single action dict, merge with item
                            new_item = {**item}
                            del new_item["template"]
                            new_item.update(variant)
                            expanded.append(new_item)
                        else:
                            # It's a string, treat as message
                            new_item = {**item}
                            del new_item["template"]
                            new_item["msg"] = variant
                            expanded.append(new_item)
                    else:
                        self._log(f"Warning: Template '{template_name}' is not a list")
                        expanded.append(item)
                else:
                    self._log(f"Warning: Template '{template_name}' not found")
                    expanded.append(item)
            else:
                expanded.append(item)

        return expanded

    def _save_config(self, config: Dict) -> bool:
        """Save configuration"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            self._log(f"Save error: {e}")
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
            self._log(f"State save error: {e}")
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
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] {message}")

    def _calculate_typing_delay(self, message: str, config: Dict) -> float:
        """Calculate realistic typing delay based on message length"""
        min_d = config.get("typing_delay_min", 8.0)
        max_d = config.get("typing_delay_max", 10.0)

        # Base delay from config range
        base_delay = random.uniform(min_d, max_d)

        # Apply natural variance based on message length
        natural_config = config.get("natural_behavior", {})
        variance = natural_config.get("typing_variance", 0.25)

        msg_len = len(message)

        # Adjust for very short messages (reactions like "lol", "fr")
        if msg_len < 5:
            base_delay *= random.uniform(0.2, 0.4)
        # Adjust for short messages
        elif msg_len < 20:
            base_delay *= random.uniform(0.4, 0.7)
        # Medium messages
        elif msg_len < 50:
            base_delay *= random.uniform(0.7, 1.0)
        # Long messages get slightly longer delay
        else:
            base_delay *= random.uniform(1.0, 1.0 + variance)

        # Ensure minimum delay of 1 second, max of max_d * 1.5
        return max(1.0, min(base_delay, max_d * 1.5))

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

        self._log("Usage: !channel add/remove/list")

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
            self._log("Invalid channel")
            return

        config = self._load_config()
        if "channels" not in config:
            config["channels"] = {}

        config["channels"][name] = target.id

        if self._save_config(config):
            self._log(f"Added '{name}' -> #{target.name} (ID: {target.id})")
        else:
            self._log("Failed to add channel")

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
            self._log(f"Channel '{name}' not found")
            return

        del config["channels"][name]
        self._save_config(config)
        self._log(f"Removed '{name}'")

    @channel_group.command(name="list")
    async def channel_list(self, ctx):
        """
        List all channels
        Usage: !channel list
        """
        config = self._load_config()
        channels = config.get("channels", {})

        if not channels:
            self._log("No channels configured")
            self._log("Use: !channel add <name> <#channel>")
            return

        self._log("\nConfigured Channels:")
        for name, channel_id in channels.items():
            channel = self.bot.get_channel(channel_id)
            ch_name = f"#{channel.name}" if channel else f"ID:{channel_id}"
            self._log(f"  {name} -> {ch_name}")
        self._log("")

    # ==================== CONVERSATION COMMANDS ====================

    @commands.group(name="conv", invoke_without_command=True)
    async def conv_group(self, ctx):
        """Conversation management commands"""
        if not self._is_primary_bot():
            return

        self._log("Usage: !conv start/stop/list/reload/status")

    @conv_group.command(name="list")
    async def conv_list(self, ctx):
        """
        List available conversations
        Usage: !conv list
        """
        if not self.conversations:
            self._log("No conversations found")
            self._log(f"Add JSON files to '{self.conversations_dir}/'")
            return

        self._log(f"\nConversations ({self.conversations_dir}/):")
        for name, items in self.conversations.items():
            self._log(f"  {name} ({len(items)} items)")
        self._log("")

    @conv_group.command(name="reload")
    async def conv_reload(self, ctx):
        """
        Reload conversations and templates
        Usage: !conv reload
        """
        if not self._is_primary_bot():
            return

        self.templates = self._load_templates()
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
            self._log(f"Conversation '{conversation_name}' not found")
            avail = ', '.join(self.conversations.keys())
            self._log(f"Available: {avail}")
            return

        # Check channel exists
        config = self._load_config()
        channels = config.get("channels", {})

        if channel_name not in channels:
            self._log(f"Channel '{channel_name}' not configured")
            self._log("Use: !channel list")
            return

        channel_id = channels[channel_name]

        # Check if already running
        state = self._load_state()
        if state and state.get("active"):
            self._log("Conversation already running (!conv stop first)")
            return

        # Start conversation
        conv = self.conversations[conversation_name]
        state = {
            "active": True,
            "channel_name": channel_name,
            "channel_id": channel_id,
            "conversation_name": conversation_name,
            "current_index": 0,
            "next_bot": self._get_first_bot(conv),
            "last_message_id": None,
            "total_items": len(conv),
            "started_at": datetime.now().isoformat(),
            "paused_until": None
        }

        if self._save_state(state):
            channel = self.bot.get_channel(channel_id)
            ch_display = f"#{channel.name}" if channel else channel_name
            self._log(f"Starting '{conversation_name}' in {ch_display} ({len(conv)} items)")
        else:
            self._log("Failed to start conversation")

    def _get_first_bot(self, conv: List[Dict]) -> int:
        """Get the bot number of first message action"""
        for item in conv:
            if item.get("action") not in ["pause", "typing_only"]:
                return item.get("bot", 1)
        return 1

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
            self._log("No active conversation")
            return

        self._clear_state()
        self.slowdown_active = False
        self._log("Conversation stopped")

    @conv_group.command(name="status")
    async def conv_status(self, ctx):
        """
        Show conversation status
        Usage: !conv status
        """
        state = self._load_state()
        if not state or not state.get("active"):
            self._log("No active conversation")
            return

        current = state.get("current_index", 0)
        total = state.get("total_items", 0)
        conv_name = state.get("conversation_name", "Unknown")

        self._log(f"Status: '{conv_name}' - {current}/{total} items")

    # ==================== CONFIG COMMANDS ====================

    @commands.command(name="reloadconfig")
    async def reload_config(self, ctx):
        """Reload config"""
        self.config = self._load_config()
        self._log(f"Bot {self._get_bot_number()}: Config reloaded")

    @commands.command(name="showconfig")
    async def show_config(self, ctx):
        """Show configuration"""
        config = self._load_config()
        bot_num = self._get_bot_number()

        self._log(f"\nBot {bot_num} Configuration:")
        self._log(f"Config: {self.config_file}")
        self._log(f"Conversations: {self.conversations_dir}/")
        self._log(f"Templates: {self.templates_dir}/")

        channels = config.get('channels', {})
        self._log(f"Channels: {len(channels)}")
        self._log(f"Templates loaded: {len(self.templates)}")

        self._log(f"Typing: {config.get('typing_delay_min')}-{config.get('typing_delay_max')}s")
        self._log(f"Typing Indicator: {'ON' if config.get('enable_typing_indicator') else 'OFF'}")
        self._log(f"Reply Chains: {'ON' if config.get('enable_reply_chains') else 'OFF'}")

        natural = config.get('natural_behavior', {})
        self._log(f"Typo Simulation: {'ON' if natural.get('enable_typo_simulation') else 'OFF'}")
        self._log(f"Typing Interruption: {'ON' if natural.get('enable_typing_interruption') else 'OFF'}")
        self._log("")

    # ==================== MONITOR ====================

    async def _handle_ratelimit(self, config: Dict):
        """Handle rate limit"""
        if not self.slowdown_active and config.get("auto_recover_from_ratelimit", True):
            self.slowdown_active = True
            delay = config.get("slowdown_delay", 10)
            self._log(f"Rate limited! Waiting {delay}s...")
            await asyncio.sleep(delay)

    async def _handle_pause_action(self, pause_item: Dict, state: Dict, config: Dict):
        """Handle pause action in conversation"""
        duration = pause_item.get("duration", [15, 45])

        if isinstance(duration, list) and len(duration) == 2:
            pause_time = random.uniform(duration[0], duration[1])
        else:
            pause_time = duration if isinstance(duration, (int, float)) else 30

        # Set pause end time in state
        pause_until = datetime.now().timestamp() + pause_time
        state["paused_until"] = pause_until
        self._save_state(state)

        reason = pause_item.get("reason", "pausing")
        self._log(f"Pausing ({reason}) for {pause_time:.1f}s...")

    async def _handle_react_action(self, react_item: Dict, state: Dict, channel):
        """Handle reaction action"""
        emoji = react_item.get("emoji", "👍")

        if not state.get("last_message_id"):
            self._log("No previous message to react to")
            return False

        try:
            msg = await channel.fetch_message(state["last_message_id"])
            await msg.add_reaction(emoji)
            self._log(f"Reacted with {emoji}")
            return True
        except discord.NotFound:
            self._log("Previous message not found for reaction")
            return False
        except discord.HTTPException as e:
            self._log(f"Failed to add reaction: {e}")
            return False

    async def _handle_sticker_action(self, sticker_item: Dict, state: Dict, channel, config: Dict, my_bot: int):
        """Handle sticker action"""
        sticker_id = sticker_item.get("sticker_id")

        if not sticker_id:
            self._log("No sticker_id provided")
            return None

        try:
            # Show typing first
            if config.get("enable_typing_indicator", True):
                delay = random.uniform(2, 4)
                async with channel.typing():
                    await asyncio.sleep(delay)

            sticker = await self.bot.fetch_sticker(sticker_id)
            sent_msg = await channel.send(stickers=[sticker])
            self._log(f"Bot {my_bot}: Sent sticker")
            return sent_msg
        except discord.NotFound:
            self._log(f"Sticker {sticker_id} not found")
            return None
        except discord.HTTPException as e:
            self._log(f"Failed to send sticker: {e}")
            return None

    async def _handle_typing_only_action(self, typing_item: Dict, config: Dict, channel, my_bot: int):
        """Handle typing-only action (typing interruption)"""
        duration = typing_item.get("duration", [3, 6])

        if isinstance(duration, list) and len(duration) == 2:
            typing_time = random.uniform(duration[0], duration[1])
        else:
            typing_time = duration if isinstance(duration, (int, float)) else 4

        self._log(f"Bot {my_bot}: Typing for {typing_time:.1f}s (no message)")

        async with channel.typing():
            await asyncio.sleep(typing_time)

        return True

    async def _send_message_with_natural_behavior(
        self, 
        channel, 
        message_text: str, 
        current_item: Dict,
        state: Dict, 
        config: Dict, 
        my_bot: int
    ):
        """Send message with natural human-like behavior including typo simulation"""

        # Calculate typing delay based on message length
        typing_delay = self._calculate_typing_delay(message_text, config)

        # Override with custom delay if specified in conversation item
        if "delay" in current_item:
            custom_delay = current_item["delay"]
            if isinstance(custom_delay, list) and len(custom_delay) == 2:
                typing_delay = random.uniform(custom_delay[0], custom_delay[1])
            elif isinstance(custom_delay, (int, float)):
                typing_delay = custom_delay

        # Check if this message should have a typo
        natural_config = config.get("natural_behavior", {})
        has_typo = False
        typo_msg = message_text
        corrected_msg = message_text

        if (current_item.get("edit_after") is not None and 
            current_item.get("edit_to") is not None):
            # Explicit typo defined in conversation
            has_typo = True
            typo_msg = current_item.get("msg", message_text)
            corrected_msg = current_item.get("edit_to")
        elif (natural_config.get("enable_typo_simulation", True) and 
              random.random() < natural_config.get("typo_chance", 0.05) and
              len(message_text) > 10):
            # Random typo simulation (simple version)
            has_typo = True
            typo_msg = message_text
            # No auto-correction for random typos (can be enhanced later)

        # Show typing indicator
        if config.get("enable_typing_indicator", True):
            if config.get("show_typing_logs", True):
                self._log(f"Bot {my_bot} typing for {typing_delay:.1f}s...")

            # Split typing into chunks to allow interruption
            chunks = int(typing_delay)
            remainder = typing_delay - chunks

            async with channel.typing():
                for _ in range(chunks):
                    state = self._load_state()
                    if not state or not state.get("active"):
                        self._log(f"Bot {my_bot}: Stopped during typing")
                        return None
                    await asyncio.sleep(1)

                if remainder > 0:
                    await asyncio.sleep(remainder)

        # Final state check
        state = self._load_state()
        if not state or not state.get("active"):
            self._log(f"Bot {my_bot}: Stopped before sending")
            return None

        # Determine if should reply or send new message
        should_reply = config.get("enable_reply_chains", True)

        # Randomly break reply chains for more natural flow
        if should_reply and random.random() < config.get("reply_chain_break_chance", 0.3):
            should_reply = False

        # Send message (with typo if applicable)
        send_text = typo_msg if has_typo else message_text
        sent_msg = None

        if should_reply and state.get("last_message_id"):
            try:
                prev_msg = await channel.fetch_message(state["last_message_id"])
                sent_msg = await prev_msg.reply(send_text)
            except discord.NotFound:
                sent_msg = await channel.send(send_text)
        else:
            sent_msg = await channel.send(send_text)

        # Log message
        preview_len = config.get("show_message_preview_length", 50)
        preview = send_text[:preview_len]
        if len(send_text) > preview_len:
            preview += '...'
        self._log(f"Bot {my_bot}: {preview}")

        # Handle typo correction
        if has_typo and corrected_msg != typo_msg:
            edit_delay = current_item.get("edit_after", [2, 5])

            if isinstance(edit_delay, list) and len(edit_delay) == 2:
                delay_time = random.uniform(edit_delay[0], edit_delay[1])
            else:
                delay_time = edit_delay if isinstance(edit_delay, (int, float)) else 3

            await asyncio.sleep(delay_time)

            # Check state before editing
            state = self._load_state()
            if state and state.get("active"):
                await sent_msg.edit(content=corrected_msg)
                self._log(f"Bot {my_bot}: Edited message (typo correction)")

        return sent_msg

    @tasks.loop(seconds=1)
    async def conversation_monitor(self):
        """Main conversation loop with natural behavior"""
        try:
            await self.bot.wait_until_ready()

            # Add small random variance to loop timing
            await asyncio.sleep(random.uniform(0, 0.5))

            # Load fresh state
            state = self._load_state()
            if not state or not state.get("active"):
                return

            # Check if paused
            if state.get("paused_until"):
                if datetime.now().timestamp() < state["paused_until"]:
                    return  # Still paused
                else:
                    # Pause ended
                    state["paused_until"] = None
                    self._save_state(state)
                    self._log("Resuming conversation...")

            my_bot = self._get_bot_number()

            # Check turn
            if state.get("next_bot") != my_bot:
                return

            # Load conversation
            conv_name = state.get("conversation_name")
            if conv_name not in self.conversations:
                self._log(f"Conversation '{conv_name}' not found")
                self._clear_state()
                return

            conv = self.conversations[conv_name]
            index = state.get("current_index", 0)

            # Check if conversation ended
            if index >= len(conv):
                total = len(conv)
                self._clear_state()
                self.slowdown_active = False
                self._log(f"Completed '{conv_name}' ({total} items)")
                return

            current = conv[index]

            # Get channel
            config = self._load_config()
            channel_id = state.get("channel_id")

            if not channel_id:
                self._clear_state()
                self._log(f"Bot {my_bot}: No channel configured")
                return

            channel = self.bot.get_channel(channel_id)
            if not channel:
                self._clear_state()
                self._log(f"Bot {my_bot}: Channel not found")
                return

            # Handle different action types
            action = current.get("action", "send")

            try:
                # PAUSE ACTION
                if action == "pause":
                    await self._handle_pause_action(current, state, config)

                    # Move to next item
                    next_index = index + 1
                    if next_index >= len(conv):
                        state["current_index"] = next_index
                        self._save_state(state)
                        return

                    next_bot = self._get_next_bot(conv, next_index)
                    state.update({
                        "current_index": next_index,
                        "next_bot": next_bot
                    })
                    self._save_state(state)
                    return

                # REACT ACTION
                elif action == "react":
                    # Only process if it's this bot's turn
                    if current.get("bot") != my_bot:
                        # Move to next
                        next_index = index + 1
                        if next_index < len(conv):
                            next_bot = self._get_next_bot(conv, next_index)
                            state.update({
                                "current_index": next_index,
                                "next_bot": next_bot
                            })
                            self._save_state(state)
                        return

                    await self._handle_react_action(current, state, channel)

                    # Move to next item
                    next_index = index + 1
                    if next_index >= len(conv):
                        state["current_index"] = next_index
                        self._save_state(state)
                        return

                    next_bot = self._get_next_bot(conv, next_index)
                    state.update({
                        "current_index": next_index,
                        "next_bot": next_bot
                    })
                    self._save_state(state)
                    return

                # STICKER ACTION
                elif action == "sticker":
                    if current.get("bot") != my_bot:
                        next_index = index + 1
                        if next_index < len(conv):
                            next_bot = self._get_next_bot(conv, next_index)
                            state.update({
                                "current_index": next_index,
                                "next_bot": next_bot
                            })
                            self._save_state(state)
                        return

                    sent_msg = await self._handle_sticker_action(current, state, channel, config, my_bot)

                    next_index = index + 1
                    if next_index >= len(conv):
                        self._clear_state()
                        self.slowdown_active = False
                        self._log(f"Bot {my_bot}: Finished '{conv_name}'")
                        return

                    next_bot = self._get_next_bot(conv, next_index)
                    state.update({
                        "current_index": next_index,
                        "next_bot": next_bot,
                        "last_message_id": sent_msg.id if sent_msg else state.get("last_message_id")
                    })
                    self._save_state(state)
                    return

                # TYPING ONLY ACTION
                elif action == "typing_only":
                    if current.get("bot") != my_bot:
                        next_index = index + 1
                        if next_index < len(conv):
                            next_bot = self._get_next_bot(conv, next_index)
                            state.update({
                                "current_index": next_index,
                                "next_bot": next_bot
                            })
                            self._save_state(state)
                        return

                    await self._handle_typing_only_action(current, config, channel, my_bot)

                    next_index = index + 1
                    if next_index >= len(conv):
                        state["current_index"] = next_index
                        self._save_state(state)
                        return

                    next_bot = self._get_next_bot(conv, next_index)
                    state.update({
                        "current_index": next_index,
                        "next_bot": next_bot
                    })
                    self._save_state(state)
                    return

                # SEND MESSAGE ACTION (default)
                else:
                    # Check if it's this bot's message
                    if current.get("bot") != my_bot:
                        # Not our turn, move to next
                        next_index = index + 1
                        if next_index < len(conv):
                            next_bot = self._get_next_bot(conv, next_index)
                            state.update({
                                "current_index": next_index,
                                "next_bot": next_bot
                            })
                            self._save_state(state)
                        return

                    message_text = current.get("msg", "")
                    if not message_text:
                        self._log(f"Bot {my_bot}: Empty message, skipping")
                        next_index = index + 1
                        if next_index < len(conv):
                            next_bot = self._get_next_bot(conv, next_index)
                            state.update({
                                "current_index": next_index,
                                "next_bot": next_bot
                            })
                            self._save_state(state)
                        return

                    # Send message with natural behavior
                    sent_msg = await self._send_message_with_natural_behavior(
                        channel, message_text, current, state, config, my_bot
                    )

                    if not sent_msg:
                        return  # Stopped during sending

                    # Update state for next message
                    next_index = index + 1

                    if next_index >= len(conv):
                        # Conversation complete
                        self._clear_state()
                        self.slowdown_active = False
                        self._log(f"Bot {my_bot}: Finished '{conv_name}'")
                        return

                    next_bot = self._get_next_bot(conv, next_index)

                    state.update({
                        "current_index": next_index,
                        "next_bot": next_bot,
                        "last_message_id": sent_msg.id
                    })

                    if not self._save_state(state):
                        self._log("Failed to save state")
                        return

                    if self.slowdown_active:
                        self.slowdown_active = False
                        self._log("Recovered from rate limit")

            except discord.HTTPException as e:
                if e.status == 429 or e.code == 50035:
                    self._log(f"Rate limit ({e.status or e.code})")
                    await self._handle_ratelimit(config)
                else:
                    self._log(f"HTTP Error: {e}")
                    self._clear_state()
            except discord.Forbidden:
                self._clear_state()
                self._log("Missing permissions")
            except Exception as e:
                self._log(f"Error: {e}")
                await asyncio.sleep(5)

        except Exception as e:
            self._log(f"Monitor error: {e}")

    def _get_next_bot(self, conv: List[Dict], start_index: int) -> int:
        """Get the next bot number from conversation items"""
        for i in range(start_index, len(conv)):
            item = conv[i]
            if item.get("action") not in ["pause", "typing_only"]:
                return item.get("bot", 1)
        return 1  # Default to bot 1 if no more items

    @conversation_monitor.before_loop
    async def before_monitor(self):
        """Wait for bot ready"""
        await self.bot.wait_until_ready()



async def setup(bot):
    await bot.add_cog(AutoConversation(bot))
