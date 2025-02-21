import discord
import asyncio
import random
from discord.ext import commands
from rich.console import Console

class Spam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.console = Console()

    @commands.command()
    async def spam(self, ctx, amount: int = None, *, message: str = None):
        if amount is None or amount < 1 or message is None:
            await ctx.send("Error: You must specify both a valid amount (at least 1) and a message.")
            return

        max_spam = 200
        if amount > max_spam:
            await ctx.send(f"Error: You can only spam up to {max_spam} messages at once.")
            return

        for i in range(amount):
            delay = random.uniform(0.5, 1.0)
            await ctx.send(message)
            await asyncio.sleep(delay)

        self.console.log(f"[bold green]Spam complete! {amount} messages sent! 🎉[/bold green]")
        await ctx.send(f"Successfully sent {amount} messages! 🎉")

async def setup(bot):
    await bot.add_cog(Spam(bot))
