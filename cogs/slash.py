import discord
from discord.ext import commands
import re
import asyncio
import random
from typing import Optional, Dict, Any
from datetime import datetime


class SlashCommander(commands.Cog):
    """
    Send slash commands to bots - fully compatible with discord.py-self
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot_name = getattr(bot, '_bot_name', 'Bot')
        self.last_interaction = None
        self.cached_commands: Dict[int, Dict[str, discord.SlashCommand]] = {}
        self._log("SlashCommander initialized")


    def _log(self, message: str, level: str = "INFO") -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{self.bot_name}] [{level}] {message}")


    def parse_channel_link(self, channel_link: str) -> tuple:
        match = re.match(r"https?://discord\.com/channels/(\d+)/(\d+)", channel_link)
        if not match:
            return None, None
        guild_id, channel_id = match.groups()
        return int(guild_id), int(channel_id)


    async def get_random_member(self, guild: discord.Guild, exclude_bots: bool = True) -> Optional[discord.Member]:
        try:
            members = [m for m in guild.members if not m.bot] if exclude_bots else guild.members
            return random.choice(members) if members else None
        except Exception as e:
            self._log(f"Error: {e}", "ERROR")
            return None


    async def get_random_online_member(self, guild: discord.Guild, exclude_bots: bool = True) -> Optional[discord.Member]:
        try:
            online_statuses = [discord.Status.online, discord.Status.idle, discord.Status.dnd]
            members = [
                m for m in guild.members 
                if m.status in online_statuses and (not m.bot if exclude_bots else True)
            ]
            if not members:
                return await self.get_random_member(guild, exclude_bots)
            return random.choice(members)
        except Exception as e:
            self._log(f"Error: {e}", "ERROR")
            return None


    async def resolve_user(self, value: str, guild: discord.Guild) -> Optional[discord.Member]:
        """
        Resolve user identifier to discord.Member object
        Returns: discord.Member or None
        """
        # Random keywords
        if value.lower() == '@random':
            member = await self.get_random_member(guild)
            if member:
                self._log(f"Random: {member.name}")
            return member
        
        if value.lower() == '@online':
            member = await self.get_random_online_member(guild)
            if member:
                self._log(f"Random online: {member.name}")
            return member
        
        # User mention: <@123456789> or <@!123456789>
        user_match = re.match(r'<@!?(\d+)>', value)
        if user_match:
            user_id = int(user_match.group(1))
            member = guild.get_member(user_id)
            if member:
                return member
            try:
                return await guild.fetch_member(user_id)
            except:
                pass
        
        # Direct user ID
        if value.isdigit():
            user_id = int(value)
            member = guild.get_member(user_id)
            if member:
                return member
            try:
                return await guild.fetch_member(user_id)
            except:
                pass
        
        # Username search
        for member in guild.members:
            if member.name.lower() == value.lower():
                self._log(f"Found: {member.name}")
                return member
            if member.nick and member.nick.lower() == value.lower():
                self._log(f"Found by nick: {member.nick}")
                return member
        
        # Username#discriminator
        if '#' in value:
            username, discriminator = value.rsplit('#', 1)
            for member in guild.members:
                if member.name.lower() == username.lower() and member.discriminator == discriminator:
                    return member
        
        self._log(f"User not found: {value}", "WARN")
        return None


    def parse_simple_value(self, value: str) -> Any:
        """Parse non-user values"""
        # Channel mention
        channel_match = re.match(r'<#(\d+)>', value)
        if channel_match:
            return int(channel_match.group(1))
        
        # Role mention
        role_match = re.match(r'<@&(\d+)>', value)
        if role_match:
            return int(role_match.group(1))
        
        # Boolean
        if value.lower() in ('true', 'yes', '1'):
            return True
        if value.lower() in ('false', 'no', '0'):
            return False
        
        # Number
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
        
        # String (default)
        return value


    async def get_commands_for_bot(self, channel: discord.TextChannel, bot_id: int) -> Dict[str, discord.SlashCommand]:
        """Fetch and cache commands"""
        if bot_id in self.cached_commands:
            return self.cached_commands[bot_id]
        
        try:
            self._log(f"Fetching commands for bot {bot_id}...")
            all_commands = await channel.application_commands()
            
            bot_commands = {
                cmd.name: cmd
                for cmd in all_commands
                if cmd.application_id == bot_id and isinstance(cmd, discord.SlashCommand)
            }
            
            self.cached_commands[bot_id] = bot_commands
            self._log(f"Cached {len(bot_commands)} commands")
            return bot_commands
            
        except Exception as e:
            self._log(f"Error fetching commands: {e}", "ERROR")
            return {}


    def is_user_option(self, cmd: discord.SlashCommand, option_name: str) -> bool:
        """Check if option expects a user/member type"""
        if not hasattr(cmd, 'options') or not cmd.options:
            return option_name.lower() in ['user', 'target', 'member', 'player']
        
        for option in cmd.options:
            if option.name == option_name and hasattr(option, 'type'):
                type_str = str(option.type).lower()
                return 'user' in type_str or 'member' in type_str
        
        return option_name.lower() in ['user', 'target', 'member', 'player']


    async def parse_slash_options(self, slash_command: discord.SlashCommand, args: tuple, guild: discord.Guild) -> Dict[str, Any]:
        """Parse slash command options from arguments"""
        options = {}
        
        for arg in args:
            if ':' not in arg:
                continue
            
            key, value = arg.split(':', 1)
            key = key.strip()
            value = value.strip()
            
            # Check if this option expects a user
            if self.is_user_option(slash_command, key):
                user = await self.resolve_user(value, guild)
                if user is None:
                    self._log(f"Failed to resolve user: {value}", "ERROR")
                    return None
                options[key] = user
            else:
                options[key] = self.parse_simple_value(value)
        
        return options


    @commands.command(name="slash")
    async def send_slash(self, ctx: commands.Context, bot_id: int, channel_link: str, command_name: str, *args) -> None:
        """
        Send slash command
        Usage: !slash <bot_id> <channel_link> <command> [option:value ...]
        
        Examples:
          !slash 123 link profile
          !slash 123 link snowball target:@random
          !slash 123 link gift target:<@123> item:Snowball
        """
        guild_id, channel_id = self.parse_channel_link(channel_link)
        if not guild_id or not channel_id:
            self._log("Invalid channel link", "ERROR")
            return

        guild = self.bot.get_guild(guild_id)
        if not guild:
            self._log("Guild not found", "ERROR")
            return

        channel = guild.get_channel(channel_id)
        if not channel:
            self._log("Channel not found", "ERROR")
            return

        try:
            commands_dict = await self.get_commands_for_bot(channel, bot_id)
            
            if command_name not in commands_dict:
                self._log(f"Command '/{command_name}' not found", "ERROR")
                available = list(commands_dict.keys())[:5]
                if available:
                    self._log(f"Available: {', '.join(available)}", "INFO")
                return
            
            slash_command = commands_dict[command_name]
            
            if slash_command.is_group():
                self._log("This is a command group, not a command", "ERROR")
                if slash_command.children:
                    self._log(f"Subcommands: {', '.join([c.name for c in slash_command.children])}", "INFO")
                return
            
            # Parse options
            options = await self.parse_slash_options(slash_command, args, guild)
            if options is None:
                return
            
            # Build display string
            cmd_str = f"/{command_name}"
            if options:
                display = []
                for k, v in options.items():
                    if isinstance(v, (discord.Member, discord.User)):
                        display.append(f"{k}:<@{v.id}>")
                    else:
                        display.append(f"{k}:{v}")
                cmd_str += " " + " ".join(display)
            
            self._log(f"Sending: {cmd_str}")
            
            # Call command
            if options:
                interaction = await slash_command(channel, **options)
            else:
                interaction = await slash_command(channel)
            
            self._log(f"✓ Sent (ID: {interaction.id})")
            
        except discord.errors.Forbidden:
            self._log("Missing permissions", "ERROR")
        except discord.errors.HTTPException as e:
            self._log(f"HTTP error: {e}", "ERROR")
        except Exception as e:
            self._log(f"Error: {type(e).__name__}: {e}", "ERROR")


    @commands.command(name="slashrandom")
    async def send_slash_random(self, ctx: commands.Context, bot_id: int, channel_link: str, command_name: str, user_option: str = "target") -> None:
        """
        Quick random user slash
        Usage: !slashrandom <bot_id> <channel_link> <command> [user_option_name]
        Example: !slashrandom 123 link snowball target
        """
        guild_id, channel_id = self.parse_channel_link(channel_link)
        if not guild_id or not channel_id:
            return

        guild = self.bot.get_guild(guild_id)
        channel = guild.get_channel(channel_id) if guild else None
        
        if not channel:
            return

        try:
            member = await self.get_random_online_member(guild)
            if not member:
                self._log("No members available", "ERROR")
                return
            
            commands_dict = await self.get_commands_for_bot(channel, bot_id)
            if command_name not in commands_dict:
                self._log(f"Command not found: /{command_name}", "ERROR")
                return
            
            slash_command = commands_dict[command_name]
            
            self._log(f"/{command_name} → {member.name}")
            interaction = await slash_command(channel, **{user_option: member})
            self._log(f"✓ Sent (ID: {interaction.id})")
            
        except Exception as e:
            self._log(f"Error: {e}", "ERROR")


    @commands.command(name="slashloop")
    async def send_slash_loop(self, ctx: commands.Context, bot_id: int, channel_link: str, command_name: str, *args) -> None:
        """
        Send slash command multiple times with loop control
        Usage: !slashloop <bot_id> <link> <command> option:value ... count delay
        
        Examples:
          !slashloop 123 link snowball target:@random 10 5.0
          !slashloop 123 link gift target:<@123> item:Snowball 5 3.0
          
        Note: Last two arguments MUST be count (int) and delay (float)
        """
        guild_id, channel_id = self.parse_channel_link(channel_link)
        if not guild_id or not channel_id:
            self._log("Invalid channel link", "ERROR")
            return

        guild = self.bot.get_guild(guild_id)
        channel = guild.get_channel(channel_id) if guild else None
        
        if not channel:
            self._log("Channel not found", "ERROR")
            return

        # Parse count and delay from last two arguments
        if len(args) < 2:
            self._log("Missing count and delay. Usage: !slashloop ... option:value count delay", "ERROR")
            return
        
        try:
            count = int(args[-2])
            delay = float(args[-1])
            option_args = args[:-2]  # All args except last two
        except (ValueError, IndexError):
            self._log("Invalid count/delay. Last two args must be: count(int) delay(float)", "ERROR")
            self._log("Example: !slashloop ... target:@random 10 5.0", "INFO")
            return

        try:
            commands_dict = await self.get_commands_for_bot(channel, bot_id)
            if command_name not in commands_dict:
                self._log(f"Command not found", "ERROR")
                return
            
            slash_command = commands_dict[command_name]
            
            # Parse base options (before loop)
            base_options = await self.parse_slash_options(slash_command, option_args, guild)
            if base_options is None:
                return
            
            self._log(f"Loop: {count}x with {delay}s delay")
            
            success = 0
            for i in range(count):
                options = base_options.copy()
                
                # If any option has @random, resolve it each iteration
                for key, value in list(options.items()):
                    if isinstance(value, str) and value.lower() in ['@random', '@online']:
                        if value.lower() == '@random':
                            member = await self.get_random_member(guild)
                        else:
                            member = await self.get_random_online_member(guild)
                        
                        if member:
                            options[key] = member
                
                try:
                    interaction = await slash_command(channel, **options)
                    
                    # Display who it was sent to
                    user_display = ""
                    for k, v in options.items():
                        if isinstance(v, (discord.Member, discord.User)):
                            user_display = f"→ {v.name}"
                            break
                    
                    self._log(f"[{i+1}/{count}] ✓ {user_display}")
                    success += 1
                except Exception as e:
                    self._log(f"[{i+1}/{count}] ✗ {e}", "ERROR")
                
                if i < count - 1:
                    await asyncio.sleep(delay)
            
            self._log(f"✓ Completed: {success}/{count}")
            
        except Exception as e:
            self._log(f"Error: {e}", "ERROR")


    @commands.command(name="listslash")
    async def list_slash(self, ctx: commands.Context, bot_id: int, channel_link: str) -> None:
        """List available slash commands"""
        guild_id, channel_id = self.parse_channel_link(channel_link)
        if not guild_id or not channel_id:
            return

        guild = self.bot.get_guild(guild_id)
        channel = guild.get_channel(channel_id) if guild else None
        
        if not channel:
            return

        try:
            bot_user = await self.bot.fetch_user(bot_id)
            commands_dict = await self.get_commands_for_bot(channel, bot_id)
            
            if not commands_dict:
                self._log("No commands found", "WARN")
                return
            
            self._log("=" * 60)
            self._log(f"Commands for {bot_user.name}:")
            self._log("=" * 60)
            
            for name, cmd in commands_dict.items():
                params = []
                if hasattr(cmd, 'options') and cmd.options:
                    for opt in cmd.options:
                        type_str = str(opt.type).split('.')[-1] if hasattr(opt, 'type') else ""
                        p = f"<{opt.name}:{type_str}>" if opt.required else f"[{opt.name}:{type_str}]"
                        params.append(p)
                
                param_str = " ".join(params)
                desc = cmd.description if hasattr(cmd, 'description') else ""
                
                self._log(f"/{name} {param_str}")
                if desc:
                    self._log(f"  → {desc}")
            
            self._log("=" * 60)
            
        except Exception as e:
            self._log(f"Error: {e}", "ERROR")


    @commands.command(name="refreshcmds")
    async def refresh_commands(self, ctx: commands.Context, bot_id: int = None) -> None:
        """Clear command cache"""
        if bot_id:
            if bot_id in self.cached_commands:
                del self.cached_commands[bot_id]
                self._log(f"✓ Cleared cache for {bot_id}")
            else:
                self._log("No cache found", "WARN")
        else:
            count = len(self.cached_commands)
            self.cached_commands.clear()
            self._log(f"✓ Cleared all cache ({count} bots)")


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Track bot messages"""
        if message.author.bot and message.components:
            self.last_interaction = message


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SlashCommander(bot))
