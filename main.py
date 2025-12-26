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
import subprocess
import importlib.util
import logging

console = Console()
CURRENT_VERSION = "2.0"

# Global bot instances
bot1 = None
bot2 = None
bot1_task = None
bot2_task = None
logging_enabled = False  # Logging disabled by default

# Logging Configuration (initially disabled)
logger = logging.getLogger(__name__)

def toggle_logging():
    """Toggle logging on/off"""
    global logging_enabled
    logging_enabled = not logging_enabled
    
    if logging_enabled:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)],
            force=True
        )
        logger.setLevel(logging.INFO)
        logging.getLogger('discord').setLevel(logging.INFO)
        console.print(Panel("[green]✓ Logging enabled[/green]", expand=True))
    else:
        logging.disable(logging.CRITICAL)
        console.print(Panel("[yellow]✓ Logging disabled[/yellow]", expand=True))

# Utility Functions
def clear_terminal():
    os.system("cls" if sys.platform == "win32" else "clear")

def display_ascii():
    ascii_art = r"""
██████╗  █████╗ ██████╗ ██╗  ██╗ ██████╗ ███████╗
██╔══██╗██╔══██╗██╔══██╗██║ ██╔╝██╔═══██╗██╔════╝
██║  ██║███████║██████╔╝█████╔╝ ██║   ██║███████║
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
    console.print("\n[bold red]Ctrl+C detected. Stopping bots...[/bold red]")
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
                console.print("\n[cyan]Available files:[/cyan]\n")
                console.print(formatted_text.plain) 
            else:
                console.print("[yellow]No files found.[/yellow]")
        elif response.status_code == 404:
            console.print("[red]The file list is unavailable (404). Please try again later.[/red]")
        elif response.status_code == 500:
            console.print("[red]Server error (500). Please try again later.[/red]")
        else:
            console.print(f"[red]Failed to fetch the file list. Status code: {response.status_code}[/red]")
    except requests.exceptions.RequestException as e:
        console.print(f"[red]An error occurred while fetching the file list: {e}[/red]")
        if logging_enabled:
            logger.exception("Error fetching file list")

def install_missing_modules(modules):
    """Install missing Python modules using pip."""
    for module in modules:
        try:
            spec = importlib.util.find_spec(module)
            if spec is None:
                raise ImportError
            console.print(f"[green]✓ Module '{module}' is already installed.[/green]")
        except ImportError:
            console.print(f"[yellow]⚠ Module '{module}' not found. Installing...[/yellow]")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", module])
                console.print(f"[green]✓ Module '{module}' installed successfully![/green]")
            except Exception as e:
                console.print(f"[red]✗ Failed to install module '{module}': {e}[/red]")
                if logging_enabled:
                    logger.exception(f"Failed to install {module}")

def is_builtin_module(module_name):
    """Check if the module is a built-in Python module."""
    try:
        spec = importlib.util.find_spec(module_name)
        return spec is not None and spec.origin == "built-in"
    except Exception:
        return False

def download_file_and_install_modules(file_name):
    """Download the file and install its required modules based on imports."""
    try:
        cogs_folder = os.path.join(os.getcwd(), "cogs")
        os.makedirs(cogs_folder, exist_ok=True)
        
        console.print(f"[cyan]Downloading {file_name}...[/cyan]")
        response = requests.get(f"https://developic.github.io/api/cogs/{file_name}")
        response.raise_for_status()

        file_path = os.path.join(cogs_folder, file_name)
        with open(file_path, "wb") as file:
            file.write(response.content)

        console.print(Panel(f"[green]✓ File {file_name} downloaded successfully![/green]", expand=True))

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
        
        # Filter out built-in modules and discord
        third_party_modules = {
            module for module in imports 
            if not is_builtin_module(module) and module not in ['discord']
        }
        
        if third_party_modules:
            console.print(f"[cyan]Installing dependencies: {', '.join(third_party_modules)}[/cyan]")
            install_missing_modules(third_party_modules)
        else:
            console.print("[green]No additional dependencies required.[/green]")

    except requests.RequestException as e:
        console.print(Panel(f"[red]✗ Error downloading file {file_name}: {e}[/red]", expand=True))
        if logging_enabled:
            logger.exception(f"Error downloading {file_name}")
    except Exception as e:
        console.print(Panel(f"[red]✗ An error occurred: {e}[/red]", expand=True))
        if logging_enabled:
            logger.exception("Unexpected error")

async def stop_bot_async(bot_number):
    """Stop a specific bot"""
    global bot1, bot2, bot1_task, bot2_task
    
    if bot_number == 1:
        if bot1 and not bot1.is_closed():
            console.print(Panel("[yellow]Stopping Bot 1...[/yellow]", expand=True))
            await bot1.close()
            if bot1_task:
                bot1_task.cancel()
            console.print(Panel("[green]✓ Bot 1 stopped successfully![/green]", expand=True))
        else:
            console.print(Panel("[red]✗ Bot 1 is not running![/red]", expand=True))
    elif bot_number == 2:
        if bot2 and not bot2.is_closed():
            console.print(Panel("[yellow]Stopping Bot 2...[/yellow]", expand=True))
            await bot2.close()
            if bot2_task:
                bot2_task.cancel()
            console.print(Panel("[green]✓ Bot 2 stopped successfully![/green]", expand=True))
        else:
            console.print(Panel("[red]✗ Bot 2 is not running![/red]", expand=True))

def show_menu():
    """Interactive menu for bot management"""
    while True:
        logging_status = "🟢 ON" if logging_enabled else "🔴 OFF"
        menu_text = f"""Menu:
1. List available files
2. Download and process a file
3. Show bot status
4. Stop a bot (Bot 1 or Bot 2)
5. Toggle logging [{logging_status}]
6. Exit"""
        
        console.print(Panel(menu_text, expand=True, style="bold cyan"))
        choice = input("Enter your choice: ").strip()
        
        if choice == "1":
            fetch_file_list()
            
        elif choice == "2":
            file_name = input("Enter the file name to download: ").strip()
            if file_name:
                download_file_and_install_modules(file_name)
            else:
                console.print("[red]✗ File name cannot be empty![/red]")
                
        elif choice == "3":
            # Show bot status
            status_text = "=== BOT STATUS ===\n"
            if bot1:
                status1 = "🟢 Running" if not bot1.is_closed() else "🔴 Stopped"
                status_text += f"Bot 1: {status1}\n"
                if not bot1.is_closed():
                    status_text += f"  User: {bot1.user}\n"
                    status_text += f"  Bot2 ID: {getattr(bot1, '_bot2_user_id', 'Not linked')}\n"
            else:
                status_text += "Bot 1: ⚪ Not initialized\n"
                
            if bot2:
                status2 = "🟢 Running" if not bot2.is_closed() else "🔴 Stopped"
                status_text += f"Bot 2: {status2}\n"
                if not bot2.is_closed():
                    status_text += f"  User: {bot2.user}\n"
                    status_text += f"  Bot1 ID: {getattr(bot2, '_bot1_user_id', 'Not linked')}\n"
            else:
                status_text += "Bot 2: ⚪ Not initialized\n"
                
            console.print(Panel(status_text, expand=True, style="bold yellow"))
            
        elif choice == "4":
            console.print("[cyan]Which bot do you want to stop?[/cyan]")
            console.print("1. Bot 1")
            console.print("2. Bot 2")
            console.print("3. Both bots")
            bot_choice = input("Enter choice (1/2/3): ").strip()
            
            if bot_choice == "1":
                asyncio.run(stop_bot_async(1))
            elif bot_choice == "2":
                asyncio.run(stop_bot_async(2))
            elif bot_choice == "3":
                asyncio.run(stop_bot_async(1))
                asyncio.run(stop_bot_async(2))
            else:
                console.print("[red]✗ Invalid choice![/red]")
                
        elif choice == "5":
            toggle_logging()
            
        elif choice == "6":
            console.print(Panel("[yellow]Exiting... Stopping all bots[/yellow]", expand=True))
            os._exit(0)
            
        else:
            console.print(Panel("[red]✗ Invalid choice. Please try again.[/red]", expand=True))

def link_bots():
    """Link both bots so they can communicate via DM"""
    global bot1, bot2
    if bot2 and bot2.user:
        bot1._bot2_user_id = bot2.user.id
    if bot1 and bot1.user:
        bot2._bot1_user_id = bot1.user.id

# Bot Initialization
clear_terminal()
load_dotenv()

TOKEN1 = os.getenv("TOKEN1")
TOKEN2 = os.getenv("TOKEN2")

if not TOKEN1 or not TOKEN2:
    console.print(Panel("[red]✗ Error: TOKEN1 or TOKEN2 not found in .env file![/red]", expand=True))
    console.print("[yellow]Create a .env file with:[/yellow]")
    console.print("TOKEN1=your_first_token_here")
    console.print("TOKEN2=your_second_token_here")
    sys.exit(1)

bot1 = commands.Bot(command_prefix="!", self_bot=True)
bot2 = commands.Bot(command_prefix="!", self_bot=True)

bot1.remove_command('help')
bot2.remove_command('help')

# Mark bots
bot1._is_primary = True
bot1._bot_name = "Bot 1"
bot1._running = True

bot2._is_primary = False
bot2._is_secondary_bot = True
bot2._bot_name = "Bot 2"
bot2._running = True

# Bot Events
@bot1.event
async def on_ready():
    console.print(Panel(Text(f"✓ Bot 1 logged in as {bot1.user}", justify="center"), expand=True, style="bold cyan"))
    if logging_enabled:
        logger.info(f"Bot 1 ready: {bot1.user}")
    link_bots()
    bot2_id = getattr(bot1, '_bot2_user_id', None)
    if bot2_id:
        console.print(Panel(Text(f"✓ Linked to Bot 2 (ID: {bot2_id})", justify="center"), expand=True, style="bold green"))

@bot2.event
async def on_ready():
    console.print(Panel(Text(f"✓ Bot 2 logged in as {bot2.user}", justify="center"), expand=True, style="bold green"))
    if logging_enabled:
        logger.info(f"Bot 2 ready: {bot2.user}")
    link_bots()
    bot1_id = getattr(bot2, '_bot1_user_id', None)
    if bot1_id:
        console.print(Panel(Text(f"✓ Linked to Bot 1 (ID: {bot1_id})", justify="center"), expand=True, style="bold cyan"))

async def load_cogs(bot):
    """Load all cogs for a specific bot"""
    cogs_dir = "./cogs"
    
    # Create cogs directory if it doesn't exist
    if not os.path.exists(cogs_dir):
        console.print(f"[yellow]Creating cogs directory...[/yellow]")
        os.makedirs(cogs_dir, exist_ok=True)
        console.print(f"[green]✓ Cogs directory created. No cogs to load.[/green]")
        return
    
    # Check if directory is empty
    cog_files = [f for f in os.listdir(cogs_dir) if f.endswith(".py")]
    if not cog_files:
        console.print(f"[yellow]No cogs found in {cogs_dir}[/yellow]")
        return
    
    # Load each cog
    for filename in cog_files:
        try:
            await bot.load_extension(f"cogs.{filename[:-3]}")
            console.print(f"[green]✓ Loaded {filename} on {bot._bot_name}[/green]")
            if logging_enabled:
                logger.info(f"Loaded cog: {filename} on {bot._bot_name}")
        except Exception as e:
            console.print(f"[red]✗ Failed to load {filename} on {bot._bot_name}: {e}[/red]")
            if logging_enabled:
                logger.exception(f"Error loading {filename}")

async def start_bot(bot, token, bot_name):
    """Start a single bot instance"""
    try:
        console.print(f"[cyan]Loading cogs for {bot_name}...[/cyan]")
        await load_cogs(bot)
        
        console.print(f"[cyan]{bot_name} connecting to Discord...[/cyan]")
        if logging_enabled:
            logger.info(f"{bot_name} starting...")
        await bot.start(token)
        
    except discord.LoginFailure as e:
        console.print(Panel(f"[red]✗ {bot_name} Login Failed: Invalid token![/red]", expand=True))
        if logging_enabled:
            logger.error(f"{bot_name} login failed: {e}")
    except Exception as e:
        if "closed" not in str(e).lower():
            console.print(Panel(f"[red]✗ {bot_name} Error: {e}[/red]", expand=True))
            if logging_enabled:
                logger.exception(f"{bot_name} error")

# Main Function
async def main():
    global bot1_task, bot2_task
    
    try:
        display_ascii()
        console.print("-" * console.width)
        console.print(Panel(Text("made by Hb36d", justify="center"), expand=True, style="bold green"))
        console.print(Panel(Text(f"Version {CURRENT_VERSION}", justify="center"), expand=True, style="bold yellow"))
        console.print(Panel(Text("Starting both bots...", justify="center"), expand=True, style="bold magenta"))
        
        # Start menu in separate thread
        asyncio.create_task(asyncio.to_thread(show_menu))
        
        # Run both bots concurrently
        bot1_task = asyncio.create_task(start_bot(bot1, TOKEN1, "Bot 1"))
        bot2_task = asyncio.create_task(start_bot(bot2, TOKEN2, "Bot 2"))
        
        await asyncio.gather(bot1_task, bot2_task, return_exceptions=True)
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Keyboard interrupt received. Shutting down...[/yellow]")
    except Exception as e:
        console.print(Panel(f"[red]✗ Fatal Error: {e}[/red]", expand=True))
        if logging_enabled:
            logger.exception("Fatal error in main()")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Program terminated.[/yellow]")
