# Auto-comment for avandbanner.py
from discord.ext import commands
import discord

class AvatarBanner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="av", help="Get a user's avatar. Usage: !av <user>")
    async def av(self, ctx, user: commands.MemberConverter):
        """
        Fetch a user's avatar.
        """
        try:
            avatar_url = user.avatar.url
            await ctx.send(f"{user.mention}'s avatar: {avatar_url}")
        except AttributeError:
            await ctx.send(f"{user.mention} does not have an avatar.")

    @commands.command(name="banner", help="Get a user's banner. Usage: !banner <user>")
    async def banner(self, ctx, user: commands.MemberConverter):
        """
        Fetch a user's banner.
        """
        try:
            fetched_user = await self.bot.fetch_user(user.id)
            if fetched_user.banner:
                banner_url = fetched_user.banner.url
                await ctx.send(f"{fetched_user.mention}'s banner: {banner_url}")
            else:
                await ctx.send(f"{fetched_user.mention} does not have a banner.")
        except discord.NotFound:
            await ctx.send("User not found.")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred: {e}")
async def setup(bot):
    await bot.add_cog(AvatarBanner(bot))
# Auto-comment for avandbanner.py
