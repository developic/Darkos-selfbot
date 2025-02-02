from discord.ext import commands
import discord
import aiohttp
import os
import aiofiles
import mimetypes  # This helps identify file types

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

                    # Generate the filename based on URL and determine its content type
                    filename = url.split("/")[-1]
                    
                    # Guess the MIME type (e.g., image/png, video/mp4) based on the file extension
                    mime_type, _ = mimetypes.guess_type(filename)

                    # Check if the file type is image/video and handle appropriately
                    if mime_type and ('image' in mime_type or 'video' in mime_type):
                        # Platform-specific file paths
                        if platform.system() == "Windows":
                            file_path = os.path.join(os.getenv("USERPROFILE"), "Downloads", filename)
                        elif platform.system() == "Darwin" or platform.system() == "Linux":
                            file_path = os.path.join(os.getenv("HOME"), "Downloads", filename)
                        else:
                            file_path = f"./downloads/{filename}"

                        # Ensure the directory exists
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)

                        # Download and write the file
                        async with aiofiles.open(file_path, "wb") as f:
                            await f.write(await response.read())

                        # Send a confirmation message
                        await ctx.send(f"✅ Downloaded: `{filename}` to {file_path}", file=discord.File(file_path))
                    else:
                        await ctx.send("❌ The file format is not supported for downloading (must be an image or video).")
        
        except Exception as e:
            await ctx.send(f"🚨 Error: {str(e)}")

async def setup(bot):
    await bot.add_cog(Download(bot))
