# Auto-comment for main.py
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
from rich.panel import Panel
from rich.console import Console
from rich.text import Text
import sys
import requests
import time

#version checker 
current_version = "2.0.0.1"
def compare_versions(current_version, latest_version):
    current_version = current_version.lstrip("v")
    latest_version = latest_version.lstrip("v")
    current = list(map(int, current_version.split(".")))
    latest = list(map(int, latest_version.split(".")))

    for c, l in zip(current, latest):
        if l > c:
            return True
        elif l < c:
            return False

    return len(latest) > len(current) and any(x > 0 for x in latest[len(current):])

def get_latest_version(api_url):
    try:
        response = requests.get(f"{api_url}/version.json?nocache={time.time()}")
        response.raise_for_status()
        return response.json().get("version", "0.0.0")
    except Exception:
        return "0.0.0"

async def check_for_update():
    try:
        latest_version = get_latest_version("https://hc36d.github.io/Selfbot")
        if compare_versions(current_version, latest_version):
            text = Text(r"""
       ________              ______               
       ___  __ \____________ ___  /_______________
       __  / / /_  ___/  __ `/_  //_/  __ \_  ___/
       _  /_/ /_  /   / /_/ /_  ,<  / /_/ /(__  ) 
       /_____/ /_/    \__,_/ /_/|_| \____//____/  
                                                  """, justify="center")
            console.print(Panel(text, style="white", expand=True)) 
            console.print(Panel(f"[red]A new version ({latest_version}) is available! Please update your bot.[/red]", expand=True)) 
            sys.exit(0)
    except Exception as e:
        console.print(Panel(f"[yellow]Warning: Could not check for updates ({e}).[/yellow]", expand=True))

def clear_terminal():
    os.system("cls" if sys.platform == "win32" else "clear")

#main code for loading and clearing terminal 
clear_terminal()
console = Console()
load_dotenv()
TOKEN = os.getenv("TOKEN")
bot = commands.Bot(command_prefix="!", self_bot=True)

async def load_cogs():
    filenames = [f[:-3] for f in os.listdir("./cogs") if f.endswith(".py")]
    tasks = [bot.load_extension(f"cogs.{filename}") for filename in filenames]
    await asyncio.gather(*tasks)

@bot.event
async def on_ready():
    text = Text(r"""
       ________              ______               
       ___  __ \____________ ___  /_______________
       __  / / /_  ___/  __ `/_  //_/  __ \_  ___/
       _  /_/ /_  /   / /_/ /_  ,<  / /_/ /(__  ) 
       /_____/ /_/    \__,_/ /_/|_| \____//____/  
                                                  """, justify="center")
    console.print(Panel(text, style="white", expand=True))
    console.print("-" * console.width)
    text = Text("made by Hb36d", justify="center")
    console.print(Panel(text, expand=True, style="bold green"))
    text = Text(f"Logged in as {bot.user}", justify="center")
    console.print(Panel(text, expand=True, style="bold magenta"))

#start the bot 
async def main():
    await check_for_update()
    await asyncio.gather(
        bot.start(TOKEN),
        load_cogs(),
    )

asyncio.run(main())
# Auto-comment for main.py
