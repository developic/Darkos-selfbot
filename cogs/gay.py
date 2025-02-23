import random
import urllib.parse
import discord
from discord.ext import commands

class GayHeritage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="gay", help="Check someone's gay heritage. Usage: !gay <user>")
    async def gay(self, ctx, user: discord.Member = None):
        if user is None:
            user = ctx.author  # Default to command sender if no user is mentioned

        gay_percentage = random.randint(1, 100)
        description = f"{user.display_name} is {gay_percentage}% gay! 🌈"
        embed_url = f"https://benny.fun/api/embed?description={urllib.parse.quote(description)}&colour=52e6e5&big_image=false"

        await ctx.send(f"[․]({embed_url})")

async def setup(bot):
    await bot.add_cog(GayHeritage(bot))
