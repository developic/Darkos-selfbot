import discord
from discord.ext import commands

class BlockCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def block(self, ctx, user: discord.User):
        """Block a user."""
        try:
            await user.block()
            print(f"Blocked user: {user.id} ({user})")
        except discord.Forbidden:
            print(f"Cannot block user: {user.id} ({user}) - Not allowed.")
        except discord.HTTPException:
            print(f"Failed to block user: {user.id} ({user})")

    @commands.command()
    async def unblock(self, ctx, user: discord.User):
        """Unblock a user."""
        try:
            await user.unblock()
            print(f"Unblocked user: {user.id} ({user})")
        except discord.Forbidden:
            print(f"Cannot unblock user: {user.id} ({user}) - Not allowed.")
        except discord.HTTPException:
            print(f"Failed to unblock user: {user.id} ({user})")

async def setup(bot):
    await bot.add_cog(BlockCog(bot))
