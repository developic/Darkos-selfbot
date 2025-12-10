import discord
from discord.ext import commands
import re
import asyncio
import json
import os
import random


CONFIG_FILE = "tracked_bots.json"


class AutoButtonClick(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tracked_bots = {}
        self.clicked_messages = set()  # Store already-clicked message IDs
        self.load_config()


    def parse_channel_link(self, channel_link):
        match = re.match(r"https?://discord\.com/channels/(\d+)/(\d+)", channel_link)
        if not match:
            return None, None
        guild_id, channel_id = match.groups()
        return int(guild_id), int(channel_id)


    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.tracked_bots, f)


    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                self.tracked_bots = json.load(f)
                self.tracked_bots = {int(k): int(v) for k, v in self.tracked_bots.items()}


    @commands.command(name="click", help="Track a bot and auto-click first button in its messages. Usage: !click <bot_id> <channel_link>")
    async def track_bot(self, ctx, bot_id: int, channel_link: str):
        guild_id, channel_id = self.parse_channel_link(channel_link)
        if not guild_id or not channel_id:
            print("Invalid channel link. Use format: https://discord.com/channels/guild_id/channel_id")
            return


        guild = self.bot.get_guild(guild_id)
        if not guild:
            print("Guild not found.")
            return


        channel = guild.get_channel(channel_id)
        if not channel:
            print("Channel not found.")
            return


        self.tracked_bots[channel_id] = bot_id
        self.save_config()
        print(f"Started tracking bot {bot_id} in channel {channel.id} of guild {guild.id}")


    @commands.command(name="untrack", help="Stop tracking a bot in a channel. Usage: !untrack <channel_link>")
    async def untrack_bot(self, ctx, channel_link: str):
        guild_id, channel_id = self.parse_channel_link(channel_link)
        if not guild_id or not channel_id:
            print("Invalid channel link. Use format: https://discord.com/channels/guild_id/channel_id")
            return


        if channel_id in self.tracked_bots:
            del self.tracked_bots[channel_id]
            self.save_config()
            print(f"Stopped tracking any bot in channel {channel_id}")
        else:
            print(f"No bot is being tracked in channel {channel_id}")


    async def process_buttons(self, message):
        # Skip if the message has already been clicked
        if message.id in self.clicked_messages:
            return


        if not message.components:
            return


        buttons = []
        for row in message.components:
            if hasattr(row, 'children'):
                for component in row.children:
                    if component.type == discord.ComponentType.button:
                        buttons.append(component)


        if not buttons:
            return


        # Mark as clicked before clicking to prevent double-click
        self.clicked_messages.add(message.id)
        
        # Random delay between 1.0 and 2.0 seconds
        delay = random.uniform(2.0, 3.0)
        print(f"Delaying for {delay:.2f} seconds before clicking button...")
        await asyncio.sleep(delay)
        
        try:
            result = await buttons[0].click()
            if isinstance(result, str):
                print(f"Auto-clicked button, opened URL: {result}")
            else:
                print("Auto-clicked button successfully.")
        except Exception as e:
            print(f"Auto-click failed: {e}")


    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id not in self.tracked_bots:
            return


        bot_id = self.tracked_bots[message.channel.id]
        if message.author.id != bot_id:
            return


        await self.process_buttons(message)


    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if after.channel.id not in self.tracked_bots:
            return


        bot_id = self.tracked_bots[after.channel.id]
        if after.author.id != bot_id:
            return


        await self.process_buttons(after)


async def setup(bot):
    await bot.add_cog(AutoButtonClick(bot))
