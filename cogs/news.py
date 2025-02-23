import discord
from discord.ext import commands
import requests
import random

class News(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="news", help="daily news about stuffs happening in world")
    async def fetch_news(self, ctx):
        api_url = "https://hc36d.github.io/api/news.json"

        try:
            response = requests.get(api_url)
            response.raise_for_status()

            news_list = response.json()
            if not news_list:
                await ctx.send("⚠️ No news found.")
                return

            news = random.choice(news_list)
            title = news.get("title", "No title available.")
            description = news.get("description", "No description available.")
            source = news.get("source", "Unknown source")
            link = news.get("link", "#")

            await ctx.send(
                f"```\n📰 {title}\n📖 {description}\n🔗 Source: {source}\n```- 🔎 *Click here*[Read more](<{link}>)  "
            )

        except requests.exceptions.RequestException:
            await ctx.send("⚠️ Failed to retrieve news. Please try again later.")

async def setup(bot):
    await bot.add_cog(News(bot))
    