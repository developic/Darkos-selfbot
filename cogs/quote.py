import discord
from discord.ext import commands
import requests
import random

class Quote(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="quote")
    async def fetch_quote(self, ctx):
        api_url = "https://hc36d.github.io/Selfbot/quote.json"

        try:
            response = requests.get(api_url, timeout=5)
            response.raise_for_status()

            quotes = response.json()
            if not quotes:
                await ctx.send("⚠️ No quotes found.")
                return

            quote = random.choice(quotes)
            quote_text = quote.get("content", "No quote found.")
            author = quote.get("author", "Unknown")
            comment = quote.get("comment", "")

            await ctx.send(f"```\n📜 {quote_text}\n— {author}\n💬 {comment}\n```")

        except requests.exceptions.RequestException:
            await ctx.send("⚠️ Failed to retrieve a quote. Please try again later.")

async def setup(bot):
    await bot.add_cog(Quote(bot))
