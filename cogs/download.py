from discord.ext import commands
import discord
import aiohttp
import os

class Download(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="download", aliases=["dw"], help="Download a file from a given URL")
    async def download(self, ctx, url: str):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return await ctx.send("❌ Failed to download the file. Invalid URL or server issue.")

                    filename = url.split("/")[-1]
                    file_path = f"./downloads/{filename}"

                    os.makedirs("./downloads", exist_ok=True)

                    with open(file_path, "wb") as f:
                        f.write(await response.read())

                    await ctx.send(f"✅ Downloaded: `{filename}`")
        
        except Exception as e:
            await ctx.send(f"🚨 Error: {str(e)}")

async def setup(bot):
    await bot.add_cog(Download(bot))
    