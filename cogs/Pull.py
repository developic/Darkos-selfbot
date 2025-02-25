import os
import requests
from discord.ext import commands
from rich.console import Console
from rich.text import Text

BASE_URL = "https://developic.github.io/api/"
COGS_DIR = 'cogs'
os.makedirs(COGS_DIR, exist_ok=True)

console = Console()

class PullCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    async def pull(self, ctx, filename: str = None):
        """Main command to pull cogs or list available files"""
        if filename is None:
            await ctx.send("Usage: `!pull <filename>` or `!pull list`.")
        else:
            await self.download_file(ctx, filename)

    @pull.command()
    async def list(self, ctx):
        """Command to list available files from the list.json API"""
        list_url = BASE_URL + "list.json"
        
        try:
            response = requests.get(list_url)
            
            if response.status_code == 200:
                file_list = response.json()
                if file_list:
                    formatted_list = '\n'.join(f"**{file}**" for file in file_list)
                    formatted_list = Text.from_markup(formatted_list)
                    # Use .plain to get the string representation of the Text object
                    await ctx.send("Here are the available files:\n" + formatted_list.plain)
                else:
                    await ctx.send("No files found.")
            elif response.status_code == 404:
                await ctx.send("The file list is unavailable (404). Please try again later.")
            elif response.status_code == 500:
                await ctx.send("Server error (500). Please try again later.")
            else:
                await ctx.send(f"Failed to fetch file list. Status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            await ctx.send(f"An error occurred while fetching the file list: {e}")

    async def download_file(self, ctx, filename: str):
        """Download and save the file from the cogs directory"""
        file_url = BASE_URL + f"cogs/{filename}"
        file_path = os.path.join(COGS_DIR, filename)

        if os.path.exists(file_path):
            console.log(f"[bold green]File `{filename}` already downloaded![/bold green]")
            await ctx.send(f"File `{filename}` is already downloaded.")
            return

        try:
            response = requests.get(file_url)
            if response.status_code == 200:
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                console.print(f"[bold cyan]File `{filename}` successfully pulled and saved![/bold cyan]")
                await ctx.send(f"File `{filename}` successfully pulled and saved!")
            elif response.status_code == 404:
                console.print(f"[bold red]File `{filename}` not found! (404)[/bold red]")
                await ctx.send(f"File `{filename}` not found (404). Please check the filename or try again later.")
            else:
                console.print(f"[bold red]Failed to fetch `{filename}`. Status code: {response.status_code}[/bold red]")
                await ctx.send(f"Failed to fetch `{filename}`. Status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            console.print(f"[bold red]Error occurred: {e}[/bold red]")
            await ctx.send(f"An error occurred while trying to pull the file: {e}")

async def setup(bot):
    await bot.add_cog(PullCog(bot))
