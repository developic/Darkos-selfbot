import discord
from discord.ext import commands
import os
import signal
from dotenv import load_dotenv
import asyncio
from rich.panel import Panel
from rich.console import Console
from rich.text import Text
import sys
import requests
import time

console = Console()
CURRENT_VERSION = "2.0"

def compare_versions(current, latest):
    return list(map(int, latest.lstrip("v").split("."))) > list(map(int, current.lstrip("v").split(".")))

def get_latest_version(api_url):
    try:
        response = requests.get(f"{api_url}/version.json?nocache={time.time()}")
        response.raise_for_status()
        return response.json().get("version", "0.0.0")
    except requests.RequestException:
        return "0.0.0"

async def check_for_update():
    latest_version = get_latest_version("https://developic.github.io/api")
    if compare_versions(latest_version, CURRENT_VERSION):
        display_ascii()
        console.print(Panel(f"[red]A new version ({latest_version}) is available! Please update your bot.[/red]", expand=True))
        sys.exit(0)

def clear_terminal():
    os.system("cls" if sys.platform == "win32" else "clear")

def display_ascii():
    console.print(Panel(Text(r"""________              ______                   
___  __ \_____ __________  /_______________    
__  / / /  __ `/_  ___/_  //_/  __ \_  ___/    
_  /_/ // /_/ /_  /   _  ,<  / /_/ /(__  )     
/_____/ \__,_/ /_/    /_/|_| \____//____/      
                                               
""", justify="center"), style="white", expand=True))

def handle_sigint(signal_number, frame):
    console.print("\n[bold red]Ctrl+C detected. Stopping bot...[/bold red]")
    os._exit(0)

signal.signal(signal.SIGINT, handle_sigint)

clear_terminal()
load_dotenv()
TOKEN = os.getenv("TOKEN")
bot = commands.Bot(command_prefix="!", self_bot=True)
bot.remove_command('help')

@bot.event
async def on_ready():
    display_ascii()
    console.print("-" * console.width)
    console.print(Panel(Text("made by Hb36d", justify="center"), expand=True, style="bold green"))
    console.print(Panel(Text(f"Logged in as {bot.user}", justify="center"), expand=True, style="bold magenta"))

async def load_cogs():
    await asyncio.gather(*(bot.load_extension(f"cogs.{f[:-3]}") for f in os.listdir("./cogs") if f.endswith(".py")))

async def main():
    try:
        await check_for_update()
        await asyncio.gather(bot.start(TOKEN), load_cogs())
    except Exception as e:
        console.print(Panel(f"[red]Error: {e}[/red]", expand=True))

asyncio.run(main())
