# Auto-comment for autoreact.py
import json
import os
from discord.ext import commands

DATA_FILE = "./data/react.json"

class AutoReact(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.auto_reacts = self.load_data()

    def load_data(self):
        """Load auto-react data from JSON file."""
        if not os.path.exists(DATA_FILE):
            return {}
        with open(DATA_FILE, "r") as file:
            return json.load(file)

    def save_data(self):
        """Save auto-react data to JSON file."""
        with open(DATA_FILE, "w") as file:
            json.dump(self.auto_reacts, file, indent=4)

    @commands.group(name="ar", aliases=["autoreact"], invoke_without_command=True)
    async def autoreact(self, ctx):
        """Base command for auto-react."""
        await ctx.send("Use `!ar add [msg] [emoji] `, `!ar remove [msg]`, or `!ar list`.")

    @autoreact.command(name="add")
    async def add_autoreact(self, ctx, trigger: str, emoji: str):
        """Add an auto-react for a specific word/phrase in the current server."""
        server_id = str(ctx.guild.id)
        if server_id not in self.auto_reacts:
            self.auto_reacts[server_id] = {}

        if trigger in self.auto_reacts[server_id]:
            if emoji in self.auto_reacts[server_id][trigger]:
                await ctx.send(f"The emoji `{emoji}` is already set to auto-react for `{trigger}`.")
                return
            self.auto_reacts[server_id][trigger].append(emoji)
        else:
            self.auto_reacts[server_id][trigger] = [emoji]

        self.save_data()
        await ctx.send(f"Added auto-react `{emoji}` for the trigger `{trigger}`.")

    @autoreact.command(name="remove")
    async def remove_autoreact(self, ctx, trigger: str, emoji: str = None):
        """Remove an auto-react for a word/phrase or all reactions for a trigger."""
        server_id = str(ctx.guild.id)
        if server_id not in self.auto_reacts or trigger not in self.auto_reacts[server_id]:
            await ctx.send(f"No auto-reacts found for `{trigger}`.")
            return

        if emoji:
            if emoji in self.auto_reacts[server_id][trigger]:
                self.auto_reacts[server_id][trigger].remove(emoji)
                if not self.auto_reacts[server_id][trigger]:
                    del self.auto_reacts[server_id][trigger]
                self.save_data()
                await ctx.send(f"Removed auto-react `{emoji}` for the trigger `{trigger}`.")
            else:
                await ctx.send(f"The emoji `{emoji}` is not set for `{trigger}`.")
        else:
            del self.auto_reacts[server_id][trigger]
            self.save_data()
            await ctx.send(f"Removed all auto-reacts for the trigger `{trigger}`.")

        if not self.auto_reacts[server_id]:
            del self.auto_reacts[server_id]

    @autoreact.command(name="list")
    async def list_autoreacts(self, ctx):
        """List all auto-reacts in the current server."""
        server_id = str(ctx.guild.id)
        if server_id not in self.auto_reacts or not self.auto_reacts[server_id]:
            await ctx.send("No auto-reacts set in this server.")
            return

        response = "Auto-reacts in this server:\n"
        for trigger, emojis in self.auto_reacts[server_id].items():
            response += f"- `{trigger}`: {', '.join(emojis)}\n"
        await ctx.send(response)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Automatically react to messages based on triggers."""
        if message.guild is None or message.author.bot:
            return

        server_id = str(message.guild.id)
        if server_id in self.auto_reacts:
            for trigger, emojis in self.auto_reacts[server_id].items():
                if trigger.lower() in message.content.lower():
                    for emoji in emojis:
                        try:
                            await message.add_reaction(emoji)
                        except Exception as e:
                            print(f"Failed to add reaction {emoji} to message: {e}")

async def setup(bot):
    await bot.add_cog(AutoReact(bot))
# Auto-comment for autoreact.py
