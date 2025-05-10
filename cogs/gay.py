import random
import urllib.parse
import discord
from discord.ext import commands

class GayHeritage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="gay", help="Check someone's gay heritage. Usage: !gay <user>")
    async def gay(self, ctx, user: discord.Member = None):
        if user is None or user == ctx.author:
            # Send a custom message and stop further execution if the user is the command sender
            await ctx.send("Whoa there! 🌈 Self-reflection is great, but this command is for exposing others! Go ahead, call out a friend—no judgment, just rainbows")
            return  # Exit the command here

        gay_percentage = random.randint(1, 100)
        description = f"{user.display_name} is {gay_percentage}% gay! 🌈"
        embed_url = f"https://benny.fun/api/embed?description={urllib.parse.quote(description)}&colour=52e6e5&big_image=false"

        await ctx.send(f"[․]({embed_url})")
       3
async def setup(bot):
    await bot.add_cog(GayHeritage(bot))