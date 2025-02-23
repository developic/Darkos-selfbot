import json
import os
from discord.ext import commands

DATA_FILE = "./data/channel_react.json"

class ChannelReact(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_reacts = self.load_data()

    def load_data(self):
        if not os.path.exists(DATA_FILE):
            return {}
        with open(DATA_FILE, "r") as file:
            return json.load(file)

    def save_data(self):
        with open(DATA_FILE, "w") as file:
            json.dump(self.channel_reacts, file, indent=4)

    @commands.group(name="rc", aliases=["channelreact"], invoke_without_command=True)
    async def channelreact(self, ctx):
        await ctx.send("Use `!rc add [emoji] [channel ID]`, `!rc remove [channel ID]`, or `!rc list`.")

    @channelreact.command(name="add")
    async def add_channelreact(self, ctx, emoji: str, channel_id: int):
        channel = self.bot.get_channel(channel_id)
        if not channel:
            await ctx.send("Invalid channel ID. Please provide a valid channel ID.")
            return

        if str(channel_id) not in self.channel_reacts:
            self.channel_reacts[str(channel_id)] = []

        if emoji in self.channel_reacts[str(channel_id)]:
            await ctx.send(f"The emoji `{emoji}` is already set to auto-react in {channel.mention}.")
            return

        self.channel_reacts[str(channel_id)].append(emoji)
        self.save_data()
        await ctx.send(f"Added auto-reaction `{emoji}` to all messages in {channel.mention}.")

    @channelreact.command(name="remove")
    async def remove_channelreact(self, ctx, channel_id: int):
        channel = self.bot.get_channel(channel_id)
        if not channel:
            await ctx.send("Invalid channel ID. Please provide a valid channel ID.")
            return

        if str(channel_id) not in self.channel_reacts:
            await ctx.send(f"No auto-reactions are set for {channel.mention}.")
            return

        del self.channel_reacts[str(channel_id)]
        self.save_data()
        await ctx.send(f"Removed all auto-reactions for {channel.mention}.")

    @channelreact.command(name="list")
    async def list_channelreacts(self, ctx):
        if not self.channel_reacts:
            await ctx.send("No auto-reactions are set for any channels.")
            return

        response = "Auto-reactions for channels:\n"
        for channel_id, emojis in self.channel_reacts.items():
            channel = self.bot.get_channel(int(channel_id))
            channel_name = channel.mention if channel else f"Channel ID: {channel_id}"
            response += f"- {channel_name}: {', '.join(emojis)}\n"
        await ctx.send(response)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is None or message.author.bot:
            return

        channel_id = str(message.channel.id)
        if channel_id in self.channel_reacts:
            for emoji in self.channel_reacts[channel_id]:
                try:
                    await message.add_reaction(emoji)
                except Exception as e:
                    print(f"Failed to add reaction {emoji} to message: {e}")

async def setup(bot):
    await bot.add_cog(ChannelReact(bot))
