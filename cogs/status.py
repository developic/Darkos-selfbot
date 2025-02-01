# Auto-comment for status.py
import discord
from discord.ext import commands

class StatusCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def set(self, ctx, *, status: str):
        """Sets the user's custom status."""
        activity = discord.Game(name=status)
        await self.bot.user.edit(activity=activity)
        await ctx.send(f"✅ Status has been updated to: `{status}`")
         
# Setup function for loading the cog
async def setup(bot):
    await bot.add_cog(StatusCog(bot))
# Auto-comment for status.py
