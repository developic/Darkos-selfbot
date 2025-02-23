import discord
from discord.ext import commands
import requests
import random
import urllib.parse

class quote(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="test")
    async def fetch_quote(self, ctx):
        api_url = "https://hc36d.github.io/api/quote.json"

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
            
            title_encoded = urllib.parse.quote(author)
            description_encoded = urllib.parse.quote(quote_text)
            comment_encoded = urllib.parse.quote(comment)

            
            embed_url = f"https://benny.fun/api/embed?title={title_encoded}&description={description_encoded}&author_name={comment_encoded}&colour=52e6e5&big_image=false"

            
            await ctx.send(f"[˙]({embed_url})")  

        except requests.exceptions.RequestException:
            await ctx.send("⚠️ Failed to retrieve a quote. Please try again later.")

async def setup(bot):
    await bot.add_cog(quote(bot))
    