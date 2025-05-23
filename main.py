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
import subprocess
import importlib.util

console = Console()
CURRENT_VERSION = "2.0"

# Utility Functions
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
    ascii_art = r"""
██████╗  █████╗ ██████╗ ██╗  ██╗ ██████╗ ███████╗
██╔══██╗██╔══██╗██╔══██╗██║ ██╔╝██╔═══██╗██╔════╝
██║  ██║███████║██████╔╝█████╔╝ ██║   ██║███████╗
██║  ██║██╔══██║██╔══██╗██╔═██╗ ██║   ██║╚════██║
██████╔╝██║  ██║██║  ██║██║  ██╗╚██████╔╝███████║
╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════     
                                               
"""
    styled_text = Text(ascii_art, justify="center")
    styled_text.stylize("bold magenta", 0, 50)
    styled_text.stylize("bold cyan", 50, 100)
    styled_text.stylize("bold green", 100, len(ascii_art))
    console.print(styled_text, justify="center")
    
def handle_sigint(signal_number, frame):
    console.print("\n[bold red]Ctrl+C detected. Stopping bot...[/bold red]")
    os._exit(0)

signal.signal(signal.SIGINT, handle_sigint)

# File Operations
def fetch_file_list():
    try:
        response = requests.get("https://developic.github.io/api/list.json", timeout=5) 
        if response.status_code == 200:
            file_list = response.json()
            if file_list: 
                formatted_list = '\n'.join(f"**{file}**" for file in file_list)
                formatted_text = Text.from_markup(formatted_list)
                print("Here are the available files:\n")
                print(formatted_text.plain) 
            else:
                print("No files found.")
        elif response.status_code == 404:
            print("The file list is unavailable (404). Please try again later.")
        elif response.status_code == 500:
            print("Server error (500). Please try again later.")
        else:
            print(f"Failed to fetch the file list. Status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching the file list: {e}")

def install_missing_modules(modules):
    """
    Install missing Python modules using pip.
    """
    for module in modules:
        try:
            spec = importlib.util.find_spec(module)
            if spec is None:
                raise ImportError
            console.print(f"[green]Module '{module}' is already installed.[/green]")
        except ImportError:
            console.print(f"[yellow]Module '{module}' not found. Installing...[/yellow]")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", module])
                console.print(f"[green]Module '{module}' installed successfully![/green]")
            except Exception as e:
                console.print(f"[red]Failed to install module '{module}': {e}[/red]")

def is_builtin_module(module_name):
    """
    Check if the module is a built-in Python module.
    """
    try:
        spec = importlib.util.find_spec(module_name)
        return spec is not None and spec.origin == "built-in"
    except Exception:
        return False

def download_file_and_install_modules(file_name):
    """
    Download the file and install its required modules based on imports.
    """
    try:
        cogs_folder = os.path.join(os.getcwd(), "cogs")
        os.makedirs(cogs_folder, exist_ok=True)
        
        response = requests.get(f"https://developic.github.io/api/cogs/{file_name}")
        response.raise_for_status()

        file_path = os.path.join(cogs_folder, file_name)
        with open(file_path, "wb") as file:
            file.write(response.content)

        console.print(Panel(f"[green]File {file_name} downloaded successfully![/green]", expand=True))

        # Parse the file for imports
        with open(file_path, "r") as file:
            content = file.read()

        # Extract imported modules
        imports = set()
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("import "):
                imports.add(line.split(" ")[1].split(".")[0])
            elif line.startswith("from "):
                imports.add(line.split(" ")[1].split(".")[0])
        
        # Filter out built-in modules (basic filter)
        third_party_modules = {module for module in imports if not is_builtin_module(module)}
        
        # Install missing modules
        install_missing_modules(third_party_modules)

    except requests.RequestException as e:
        console.print(Panel(f"[red]Error downloading file {file_name}: {e}[/red]", expand=True))
    except Exception as e:
        console.print(Panel(f"[red]An error occurred: {e}[/red]", expand=True))

def show_menu():
    while True:
        console.print(Panel("Menu:\n1. List files\n2. Download and process a file\n3. Exit", expand=True))
        choice = input("Enter your choice: ")
        if choice == "1":
            file_list = fetch_file_list()
            if file_list:
                console.print(Panel(f"Files:\n{', '.join(file_list)}", expand=True))
        elif choice == "2":
            file_name = input("Enter the file name to download: ")
            if file_name:
                download_file_and_install_modules(file_name)
            else:
                console.print("[red]File name cannot be empty![/red]")
        elif choice == "3":
            os._exit(0)
        else:
            console.print(Panel("[red]Invalid choice. Please try again.[/red]", expand=True))

# Bot Initialization
clear_terminal()
load_dotenv()
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    sys.exit("Error: TOKEN not found in environment variables.")

bot = commands.Bot(command_prefix="!", self_bot=True)
bot.remove_command('help')

# Bot Events
@bot.event
async def on_ready():
    display_ascii()
    console.print("-" * console.width)
    console.print(Panel(Text("made by Hb36d", justify="center"), expand=True, style="bold green"))
    console.print(Panel(Text(f"Logged in as {bot.user}", justify="center"), expand=True, style="bold magenta"))
    await asyncio.to_thread(show_menu)

async def load_cogs():
    await asyncio.gather(*(bot.load_extension(f"cogs.{f[:-3]}") for f in os.listdir("./cogs") if f.endswith(".py")))

# Main Function
async def main():
    try:
        await check_for_update()
        await load_cogs()
        await bot.start(TOKEN)
    except Exception as e:
        console.print(Panel(f"[red]Error: {e}[/red]", expand=True))

if __name__ == "__main__":
    asyncio.run(main())