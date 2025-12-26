import discord
from discord.ext import commands
import aiohttp
import subprocess
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Set
import asyncio
import re

class MentionWebhook(commands.Cog):
    """
    Fast mention handler with keyboard shortcuts and keyword detection.
    Shortcuts: Alt+S = Skip | Alt+T = Templates | Alt+W = Ignore Bots | Alt+H = History | ESC = Cancel
    """
    
    WEBHOOK_URL = "https://discord.com/api/webhooks/1448944847573487708/eBWo5qsVyp2UW1Zp3qqnIrpwcGMo8HjJ88sxAZlsiGEyY-lVFwvDTP_6VrI_LdTtMyDt"
    
    # Custom keywords to detect (case-insensitive, whole words only)
    KEYWORDS = ["john", "dev"]
    
    # Quick reply templates
    TEMPLATES = {
        "👍 OK": "Okay",
        "✅ Yes": "Yes, sure",
        "❌ No": "No, sorry",
        "⏰ Busy": "I'm busy right now",
        "🔄 Later": "Will check later",
        "💤 AFK": "AFK right now",
        "📝 Noted": "Noted",
        "❓ What": "What?",
    }
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot_name = getattr(bot, '_bot_name', 'Bot')
        self.queue: List[Dict] = []
        self.is_processing = False
        
        # Unreplied mentions tracking
        self.unreplied_mentions: List[Dict] = []
        
        # Get Bot 1 and Bot 2 user IDs
        self.bot1_id = None
        self.bot2_id = None
        self._get_bot_ids()
        
        # In-memory ignore list for when OTHER people mention these bots
        self.ignored_bot_mentions: Set[int] = set()
        
        # Start cleanup task
        self.cleanup_task = asyncio.create_task(self._cleanup_old_mentions())
        
        self._log("Mention handler initialized")
        self._log(f"Keywords: {', '.join(self.KEYWORDS)}")
    
    def cog_unload(self):
        """Cleanup when unloading"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
    
    async def _cleanup_old_mentions(self):
        """Auto-cleanup unreplied mentions after 1 minute"""
        await self.bot.wait_until_ready()
        
        while True:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds
                
                now = datetime.now()
                initial_count = len(self.unreplied_mentions)
                
                # Remove mentions older than 1 minute
                self.unreplied_mentions = [
                    m for m in self.unreplied_mentions
                    if (now - m['timestamp']) < timedelta(minutes=1)
                ]
                
                removed = initial_count - len(self.unreplied_mentions)
                if removed > 0:
                    self._log(f"🧹 Cleaned {removed} old mention(s)")
                
            except Exception as e:
                self._log(f"Cleanup error: {e}", "ERROR")
    
    def _add_unreplied(self, message: discord.Message, trigger_type: str, keyword: Optional[str] = None):
        """Add mention to unreplied list"""
        self.unreplied_mentions.append({
            'message': message,
            'type': trigger_type,
            'keyword': keyword,
            'timestamp': datetime.now(),
            'author': message.author.name,
            'server': message.guild.name if message.guild else 'DM',
            'channel': f"#{message.channel.name}" if message.guild else 'DM',
            'preview': message.content[:50].replace('\n', ' ')
        })
    
    def _remove_unreplied(self, message: discord.Message):
        """Remove mention from unreplied list (when replied)"""
        self.unreplied_mentions = [
            m for m in self.unreplied_mentions
            if m['message'].id != message.id
        ]
    
    def _get_bot_ids(self) -> None:
        """Get Bot 1 and Bot 2 user IDs from linked bots"""
        # Get Bot 1 ID
        bot1_user_id = getattr(self.bot, '_bot1_user_id', None)
        if bot1_user_id:
            self.bot1_id = bot1_user_id
        
        # Get Bot 2 ID
        bot2_user_id = getattr(self.bot, '_bot2_user_id', None)
        if bot2_user_id:
            self.bot2_id = bot2_user_id
        
        # If current bot is Bot 1 or Bot 2, get its own ID
        if self.bot.user:
            if getattr(self.bot, '_is_primary', False):
                self.bot1_id = self.bot.user.id
            elif getattr(self.bot, '_is_secondary_bot', False):
                self.bot2_id = self.bot.user.id
        
        if self.bot1_id or self.bot2_id:
            self._log(f"Conversation bots: Bot1={self.bot1_id}, Bot2={self.bot2_id}")
    
    def _is_conversation_bot(self, user_id: int) -> bool:
        """Check if user is Bot 1 or Bot 2"""
        if self.bot1_id and user_id == self.bot1_id:
            return True
        if self.bot2_id and user_id == self.bot2_id:
            return True
        return False
    
    def _message_mentions_ignored_bot(self, message: discord.Message) -> bool:
        """Check if message mentions any ignored bot (from OTHER people)"""
        for user in message.mentions:
            if user.id in self.ignored_bot_mentions:
                return True
        return False
    
    def _contains_keyword(self, text: str) -> Optional[str]:
        """Check if text contains any keyword as whole word (case-insensitive)"""
        for keyword in self.KEYWORDS:
            # Use word boundary \b to match whole words only
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                return keyword
        return None
    
    def _log(self, msg: str, level: str = "INFO") -> None:
        """Centralized logging"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{self.bot_name}] [{level}] {msg}")
    
    def notify(self, title: str, body: str) -> None:
        """Send desktop notification"""
        try:
            subprocess.run(
                ['notify-send', '-a', 'Discord', '-i', 'discord', title, body],
                timeout=2,
                check=False
            )
        except Exception as e:
            self._log(f"Notification failed: {e}", "WARNING")
    
    def rofi_input(self, prompt: str, info: str = "") -> tuple[Optional[str], int]:
        """
        Show Rofi input with keyboard shortcuts.
        Returns (text, exit_code)
        Exit codes: 0=Enter, 1=ESC, 10=Alt+S, 11=Alt+T, 12=Alt+W, 13=Alt+H
        """
        try:
            cmd = [
                'rofi',
                '-dmenu',
                '-p', prompt,
                '-theme-str', 'window {width: 55%;}',
                '-theme-str', 'listview {enabled: false;}',
                '-theme-str', 'entry {placeholder: "Type reply or use shortcuts...";}',
                '-l', '0',
                '-format', 's',
                # Custom keybinds
                '-kb-custom-1', 'Alt+s',  # Skip
                '-kb-custom-2', 'Alt+t',  # Templates
                '-kb-custom-3', 'Alt+w',  # Ignore bots
                '-kb-custom-4', 'Alt+h',  # History
            ]
            
            if info:
                cmd.extend(['-mesg', info])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            text = result.stdout.strip()
            return (text if text else None, result.returncode)
                
        except subprocess.TimeoutExpired:
            self._log("Rofi timeout", "WARNING")
            return (None, 1)
        except FileNotFoundError:
            self._log("Rofi not installed", "ERROR")
            return (None, 1)
        except Exception as e:
            self._log(f"Rofi error: {e}", "ERROR")
            return (None, 1)
    
    def rofi_select(self, prompt: str, options: List[str], info: str = "") -> tuple[Optional[str], int]:
        """
        Show Rofi selection with shortcuts.
        Returns (selected, exit_code)
        """
        try:
            cmd = [
                'rofi',
                '-dmenu',
                '-i',
                '-p', prompt,
                '-theme-str', 'window {width: 50%;}',
                '-theme-str', 'listview {lines: 8;}',
                '-format', 's',
                '-no-custom',
                # Custom keybind
                '-kb-custom-1', 'Alt+s',  # Skip
            ]
            
            if info:
                cmd.extend(['-mesg', info])
            
            result = subprocess.run(
                cmd,
                input='\n'.join(options),
                capture_output=True,
                text=True,
                timeout=60
            )
            
            selected = result.stdout.strip()
            return (selected if selected in options else None, result.returncode)
                
        except subprocess.TimeoutExpired:
            self._log("Rofi timeout", "WARNING")
            return (None, 1)
        except Exception as e:
            self._log(f"Rofi error: {e}", "ERROR")
            return (None, 1)
    
    async def show_unreplied_history(self) -> None:
        """Show unreplied mentions history"""
        if not self.unreplied_mentions:
            self._log("📭 No unreplied mentions")
            return
        
        # Build options
        options = []
        for idx, mention in enumerate(self.unreplied_mentions):
            age_seconds = (datetime.now() - mention['timestamp']).total_seconds()
            age_str = f"{int(age_seconds)}s ago"
            
            # Icon based on type
            if mention['type'] == 'everyone':
                icon = "🚨"
            elif mention['type'] == 'keyword':
                icon = f"🔑"
            else:
                icon = "🔔"
            
            # Format: "🔔 Alice | 15s ago | Hey can you help?"
            option = f"{icon} {mention['author']} | {age_str} | {mention['preview']}"
            options.append(option)
        
        options.append("🔄 Refresh")
        options.append("❌ Close")
        
        info = f"<b>Unreplied Mentions ({len(self.unreplied_mentions)})</b>\n<i>Auto-cleanup after 1 minute</i>"
        
        loop = asyncio.get_event_loop()
        selected, exit_code = await loop.run_in_executor(
            None,
            self.rofi_select,
            "History",
            options,
            info
        )
        
        if exit_code != 0 or not selected:
            return
        
        if selected == "❌ Close":
            return
        
        elif selected == "🔄 Refresh":
            await self.show_unreplied_history()
            return
        
        # Find selected mention
        for idx, option in enumerate(options[:-2]):  # Exclude Refresh and Close
            if option == selected:
                mention = self.unreplied_mentions[idx]
                await self.reply_to_unreplied(mention)
                break
    
    async def reply_to_unreplied(self, mention: Dict) -> None:
        """Reply to an unreplied mention from history"""
        message = mention['message']
        author = mention['author']
        
        info = (
            f"📜 <b>From History</b>\n"
            f"👤 {author} | 🏠 {mention['server']} | 💬 {mention['channel']}\n"
            f"📝 {mention['preview']}"
        )
        
        loop = asyncio.get_event_loop()
        
        # Show input
        reply, exit_code = await loop.run_in_executor(
            None,
            self.rofi_input,
            "Reply",
            info
        )
        
        if exit_code == 11:  # Alt+T - templates
            await self.show_templates(message, author, info)
            return
        
        elif exit_code == 0 and reply:
            try:
                await message.reply(reply, mention_author=True)
                self._log(f"✓ Replied to {author} (from history): {reply[:40]}")
                self._remove_unreplied(message)
                return
            except discord.HTTPException as e:
                self._log(f"❌ Reply failed: {e}", "ERROR")
                return
        
        # Show templates if empty
        await self.show_templates(message, author, info)
    
    async def show_ignore_menu(self) -> None:
        """Show menu to ignore when OTHER people mention bots"""
        options = []
        
        # Build options
        if self.bot1_id:
            status = "✓" if self.bot1_id in self.ignored_bot_mentions else " "
            options.append(f"[{status}] Ignore @Bot1 mentions")
        
        if self.bot2_id:
            status = "✓" if self.bot2_id in self.ignored_bot_mentions else " "
            options.append(f"[{status}] Ignore @Bot2 mentions")
        
        if self.bot1_id and self.bot2_id:
            both_ignored = self.bot1_id in self.ignored_bot_mentions and self.bot2_id in self.ignored_bot_mentions
            status = "✓" if both_ignored else " "
            options.append(f"[{status}] Ignore Both mentions")
        
        options.append("🔄 Clear All")
        options.append("❌ Cancel")
        
        if not options or len(options) <= 2:
            self._log("No conversation bots detected", "WARNING")
            return
        
        # Show current status
        status_text = "Will notify when others mention bots"
        if self.ignored_bot_mentions:
            ignored_names = []
            if self.bot1_id and self.bot1_id in self.ignored_bot_mentions:
                ignored_names.append("@Bot1")
            if self.bot2_id and self.bot2_id in self.ignored_bot_mentions:
                ignored_names.append("@Bot2")
            if ignored_names:
                status_text = f"Ignoring mentions of: {', '.join(ignored_names)}"
        
        info = f"<b>Ignore when OTHERS mention bots</b>\n<i>{status_text}</i>"
        
        loop = asyncio.get_event_loop()
        selected, exit_code = await loop.run_in_executor(
            None,
            self.rofi_select,
            "Ignore Menu",
            options,
            info
        )
        
        if exit_code != 0 or not selected:
            return
        
        # Handle selection
        if selected == "❌ Cancel":
            return
        
        elif selected == "🔄 Clear All":
            self.ignored_bot_mentions.clear()
            self._log("✓ Cleared ignore list")
        
        elif "Bot1" in selected:
            if self.bot1_id in self.ignored_bot_mentions:
                self.ignored_bot_mentions.remove(self.bot1_id)
                self._log("✓ Will notify when others mention @Bot1")
            else:
                self.ignored_bot_mentions.add(self.bot1_id)
                self._log("✓ Ignoring when others mention @Bot1")
        
        elif "Bot2" in selected:
            if self.bot2_id in self.ignored_bot_mentions:
                self.ignored_bot_mentions.remove(self.bot2_id)
                self._log("✓ Will notify when others mention @Bot2")
            else:
                self.ignored_bot_mentions.add(self.bot2_id)
                self._log("✓ Ignoring when others mention @Bot2")
        
        elif "Both" in selected:
            if self.bot1_id in self.ignored_bot_mentions and self.bot2_id in self.ignored_bot_mentions:
                self.ignored_bot_mentions.discard(self.bot1_id)
                self.ignored_bot_mentions.discard(self.bot2_id)
                self._log("✓ Will notify when others mention both bots")
            else:
                if self.bot1_id:
                    self.ignored_bot_mentions.add(self.bot1_id)
                if self.bot2_id:
                    self.ignored_bot_mentions.add(self.bot2_id)
                self._log("✓ Ignoring when others mention both bots")
    
    def create_embed(self, message: discord.Message, trigger_type: str, keyword: Optional[str] = None) -> discord.Embed:
        """Create webhook notification embed"""
        is_everyone = (trigger_type == "everyone")
        is_keyword = (trigger_type == "keyword")
        
        # Title and color based on trigger type
        if is_everyone:
            title = "🚨 @everyone Mention"
            color = 0xFF6B6B
        elif is_keyword:
            title = f"🔑 Keyword Detected: '{keyword}'"
            color = 0xFFA500
        else:
            title = "🔔 Direct Mention"
            color = 0x5865F2
        
        embed = discord.Embed(
            title=title,
            description=f"**{message.guild.name if message.guild else 'DM'}**",
            color=color,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="From", value=message.author.name, inline=True)
        
        if message.guild:
            embed.add_field(name="Channel", value=f"#{message.channel.name}", inline=True)
        
        content = message.content[:500] if len(message.content) > 500 else message.content
        embed.add_field(
            name="Message",
            value=f"``````" if content else "*[No text]*",
            inline=False
        )
        
        if message.guild:
            embed.add_field(name="Link", value=f"[Jump]({message.jump_url})", inline=False)
        
        if message.author.avatar:
            embed.set_thumbnail(url=message.author.avatar.url)
        
        return embed
    
    async def send_webhook(self, embed: discord.Embed) -> bool:
        """Send webhook notification"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.WEBHOOK_URL,
                    json={"embeds": [embed.to_dict()], "username": "Mentions"}
                ) as resp:
                    return resp.status in [200, 204]
        except Exception as e:
            self._log(f"Webhook failed: {e}", "ERROR")
            return False
    
    async def handle_mention(self, item: Dict) -> None:
        """Handle single mention with keyboard shortcuts"""
        message = item['msg']
        trigger_type = item['type']
        server = item['server']
        keyword = item.get('keyword')
        
        # Add to unreplied list
        self._add_unreplied(message, trigger_type, keyword)
        
        author = message.author.name
        channel = f"#{message.channel.name}" if message.guild else "DM"
        preview = message.content[:60].replace('\n', ' ')
        
        # Info with keyboard shortcuts hint
        if trigger_type == "everyone":
            icon = "🚨"
        elif trigger_type == "keyword":
            icon = f"🔑 '{keyword}'"
        else:
            icon = "🔔"
        
        unreplied_count = len(self.unreplied_mentions)
        info = (
            f"{icon} <b>{author}</b> | 🏠 {server} | 💬 {channel}\n"
            f"📝 {preview}\n\n"
            f"<i>Alt+S = Skip | Alt+T = Templates | Alt+W = Ignore | Alt+H = History ({unreplied_count}) | ESC = Cancel</i>"
        )
        
        loop = asyncio.get_event_loop()
        
        # Show input with shortcuts
        reply, exit_code = await loop.run_in_executor(
            None,
            self.rofi_input,
            "Reply",
            info
        )
        
        # Handle exit codes
        if exit_code == 10:  # Alt+S pressed
            self._log(f"⏭️  Skipped {author} (Alt+S)")
            return
        
        elif exit_code == 11:  # Alt+T pressed - show templates
            await self.show_templates(message, author, info)
            return
        
        elif exit_code == 12:  # Alt+W pressed - show ignore menu
            self._log("⚙️  Opening ignore menu (Alt+W)")
            await self.show_ignore_menu()
            return
        
        elif exit_code == 13:  # Alt+H pressed - show history
            self._log(f"📜 Opening history (Alt+H) - {unreplied_count} unreplied")
            await self.show_unreplied_history()
            return
        
        elif exit_code == 1:  # ESC pressed
            self._log(f"⏭️  Canceled {author} (ESC)")
            return
        
        elif exit_code == 0 and reply:  # Enter with text
            try:
                await message.reply(reply, mention_author=True)
                self._log(f"✓ Replied to {author}: {reply[:40]}")
                self._remove_unreplied(message)
                return
            except discord.HTTPException as e:
                self._log(f"❌ Reply failed: {e}", "ERROR")
                return
        
        # Empty input - show templates
        await self.show_templates(message, author, info)
    
    async def show_templates(self, message: discord.Message, author: str, info: str) -> None:
        """Show template selection menu"""
        loop = asyncio.get_event_loop()
        
        template, exit_code = await loop.run_in_executor(
            None,
            self.rofi_select,
            "Template",
            list(self.TEMPLATES.keys()) + ["🔕 Skip"],
            info
        )
        
        if exit_code == 10:  # Alt+S in template menu
            self._log(f"⏭️  Skipped {author} (Alt+S)")
            return
        
        if template and template != "🔕 Skip":
            try:
                await message.reply(self.TEMPLATES[template], mention_author=True)
                self._log(f"✓ Template to {author}: {self.TEMPLATES[template]}")
                self._remove_unreplied(message)
            except discord.HTTPException as e:
                self._log(f"❌ Template failed: {e}", "ERROR")
        else:
            self._log(f"⏭️  Skipped {author}")
    
    async def process_queue(self) -> None:
        """Process all mentions in queue sequentially"""
        if self.is_processing or not self.queue:
            return
        
        self.is_processing = True
        
        try:
            while self.queue:
                item = self.queue[0]
                
                # Log queue status
                queue_count = len(self.queue)
                if queue_count > 1:
                    self._log(f"📬 Processing 1/{queue_count}")
                
                # Handle mention
                await self.handle_mention(item)
                
                # Remove from queue
                self.queue.pop(0)
                
        except Exception as e:
            self._log(f"❌ Queue error: {e}", "ERROR")
        finally:
            self.is_processing = False
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Detect mentions, keywords and add to queue"""
        # Ignore self
        if message.author == self.bot.user:
            return
        
        # Ignore messages FROM Bot 1 and Bot 2 (they're talking to each other)
        if self._is_conversation_bot(message.author.id):
            return
        
        # Ignore other bots
        if message.author.bot:
            return
        
        # Check if message mentions any ignored bot (from OTHER people)
        if self._message_mentions_ignored_bot(message):
            # Silently ignore - someone mentioned an ignored bot
            return
        
        # Check mentions
        is_mentioned = self.bot.user in message.mentions
        is_everyone = message.mention_everyone
        
        # Check keywords
        keyword = self._contains_keyword(message.content)
        
        # Ignore if no triggers
        if not is_mentioned and not is_everyone and not keyword:
            return
        
        # Determine trigger type (priority: everyone > mention > keyword)
        if is_everyone:
            trigger_type = "everyone"
            trigger_keyword = None
        elif is_mentioned:
            trigger_type = "direct"
            trigger_keyword = None
        else:
            trigger_type = "keyword"
            trigger_keyword = keyword
        
        server = message.guild.name if message.guild else "DM"
        author = message.author.name
        preview = message.content[:50].replace('\n', ' ')
        
        # Log
        if trigger_type == "everyone":
            icon = "🚨"
            log_msg = f"{icon} @everyone from {author} in {server}"
        elif trigger_type == "keyword":
            icon = "🔑"
            log_msg = f"{icon} Keyword '{keyword}' from {author} in {server}"
        else:
            icon = "🔔"
            log_msg = f"{icon} Mention from {author} in {server}"
        
        self._log(log_msg)
        
        # Desktop notification
        if trigger_type == "everyone":
            title = "🚨 @everyone Mention"
        elif trigger_type == "keyword":
            title = f"🔑 Keyword: '{keyword}'"
        else:
            title = "🔔 You Were Mentioned"
        
        body = f"From: {author}\nServer: {server}\n{preview}"
        self.notify(title, body)
        
        # Send webhook
        embed = self.create_embed(message, trigger_type, trigger_keyword)
        await self.send_webhook(embed)
        
        # Add to queue
        self.queue.append({
            'msg': message,
            'type': trigger_type,
            'keyword': trigger_keyword,
            'server': server,
            'time': datetime.now()
        })
        
        # Limit queue size
        if len(self.queue) > 20:
            self.queue.pop(0)
        
        # Process queue
        await self.process_queue()
    
    @commands.command(name="ignore")
    async def ignore_command(self, ctx):
        """Open ignore menu"""
        await self.show_ignore_menu()
    
    @commands.command(name="unignore")
    async def unignore_command(self, ctx, bot: str):
        """
        Unignore bot mentions
        Usage: !unignore bot1 | !unignore bot2 | !unignore all
        """
        bot_lower = bot.lower()
        
        if bot_lower in ["bot1", "1"]:
            if self.bot1_id and self.bot1_id in self.ignored_bot_mentions:
                self.ignored_bot_mentions.remove(self.bot1_id)
                self._log("✓ Will notify when others mention @Bot1")
            else:
                self._log("⚠️ @Bot1 mentions not ignored")
        
        elif bot_lower in ["bot2", "2"]:
            if self.bot2_id and self.bot2_id in self.ignored_bot_mentions:
                self.ignored_bot_mentions.remove(self.bot2_id)
                self._log("✓ Will notify when others mention @Bot2")
            else:
                self._log("⚠️ @Bot2 mentions not ignored")
        
        elif bot_lower == "all":
            if self.ignored_bot_mentions:
                self.ignored_bot_mentions.clear()
                self._log("✓ Will notify for all bot mentions")
            else:
                self._log("⚠️ No bot mentions ignored")
        
        else:
            self._log("❌ Usage: !unignore bot1|bot2|all")
    
    @commands.command(name="ignored")
    async def show_ignored_command(self, ctx):
        """Show currently ignored bot mentions"""
        if not self.ignored_bot_mentions:
            self._log("📭 Not ignoring any bot mentions")
            return
        
        ignored_names = []
        if self.bot1_id and self.bot1_id in self.ignored_bot_mentions:
            ignored_names.append("@Bot1")
        if self.bot2_id and self.bot2_id in self.ignored_bot_mentions:
            ignored_names.append("@Bot2")
        
        if ignored_names:
            self._log(f"🔇 Ignoring mentions of: {', '.join(ignored_names)}")
        else:
            self._log("📭 Not ignoring any bot mentions")
    
    @commands.command(name="history")
    async def history_command(self, ctx):
        """Show unreplied mentions"""
        await self.show_unreplied_history()
    
    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Log when ready and update bot IDs"""
        # Update bot IDs after bot is ready
        self._get_bot_ids()
        
        self._log("✓ Ready with shortcuts")
        self._log(f"   {self.bot.user.name}")
        self._log("   Alt+S = Skip | Alt+T = Templates | Alt+W = Ignore | Alt+H = History")
        self._log(f"   Keywords: {', '.join(self.KEYWORDS)}")
        
        if self.bot1_id or self.bot2_id:
            self._log(f"   Conversation bots: Bot1={self.bot1_id}, Bot2={self.bot2_id}")

async def setup(bot: commands.Bot) -> None:
    """Setup cog"""
    await bot.add_cog(MentionWebhook(bot))
