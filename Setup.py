import os
import subprocess
import sys
import asyncio

def uninstall_stuff():
    # List of packages to check
    packages = ["discord.py"]  # Add more as needed

    # Get installed packages using pip list
    result = subprocess.run(["pip", "list"], capture_output=True, text=True)
    installed = [line.split()[0].lower() for line in result.stdout.splitlines()[2:]]

    for pkg in packages:
        if pkg.lower() in installed:
            print(f"\nPackage '{pkg}' is installed.")
            confirm = input(f"Do you want to uninstall '{pkg}'? (y/n): ").strip().lower()
            if confirm == 'y':
                reason = input("Please provide a reason for uninstalling: ").strip()
                print(f"Uninstalling '{pkg}' for reason: {reason}")
                subprocess.run(["pip", "uninstall", pkg, "-y"])
            else:
                print(f"Skipped '{pkg}'.")
        else:
            print(f"\nPackage '{pkg}' is not installed.")

def install_requirements():
    required_modules = ["git+https://github.com/dolfies/discord.py-self@20ae80b398ec83fa272f0a96812140e14868c88f", "python-dotenv","rich","requests"]
    for module in required_modules:
        try:
            subprocess.check_call([os.sys.executable, "-m", "pip", "install", module])
            print(f"Installed {module} successfully.")
        except subprocess.CalledProcessError as e:
            print(f"An error occurred while installing {module}: {e}")
            return False
    return True

def create_or_update_env():
    if not os.path.exists('.env'):
        token = input("Please enter your Discord token: ")
        with open('.env', 'w') as f:
            f.write(f"TOKEN={token}\n")
        print(".env file created successfully!")
    else:
        choice = input(".env file already exists. Do you want to overwrite it? (yes/no): ").strip().lower()
        if choice == 'yes':
            token = input("Please enter your Discord token: ")
            with open('.env', 'w') as f:
                f.write(f"TOKEN={token}\n")
            print(".env file has been updated successfully!")
        else:
            print(".env file was not modified.")

def clear_terminal():
    if sys.platform == "win32":
        os.system('cls')
    else:
        os.system('clear')

def run_bot():
    import discord
    from discord.ext import commands
    import os
    from dotenv import load_dotenv
    load_dotenv()

    TOKEN = os.getenv("TOKEN")

    if not TOKEN:
        print("No token found. Please provide a token by entering it in the .env file.")
        return

    bot = commands.Bot(command_prefix="!", self_bot=True)

    @bot.event
    async def on_ready():
        print(f"Logged in as {bot.user}")
        await bot.close()

    try:
        bot.run(TOKEN)
        print("Correct token! Proceeding with the bot setup.")
    except discord.LoginFailure:
        print("Incorrect token. Please enter a valid token in the .env file.")
        new_token = input("Please enter your Discord token: ")
        with open('.env', 'w') as f:
            f.write(f"TOKEN={new_token}\n")
        print(".env file has been updated with the new token.")
        return

def main():

    uninstall_stuff()
    
    if not install_requirements():
        print("Required modules could not be installed. Please resolve the issue and try again.")
        return

    create_or_update_env()
    run_bot()
    clear_terminal()
    print("""
██╗  ██╗ ██████╗██████╗  ██████╗ ██████╗ 
██║  ██║██╔════╝╚════██╗██╔════╝ ██╔══██╗
███████║██║      █████╔╝███████╗ ██║  ██║
██╔══██║██║      ╚═══██╗██╔═══██╗██║  ██║
██║  ██║╚██████╗██████╔╝╚██████╔╝██████╔╝
╚═╝  ╚═╝ ╚═════╝╚═════╝  ╚═════╝ ╚═════╝ """)
    print("\nSetup completed without any errors!")
    print("Use 'python main.py' to use the bot next time.")

if __name__ == '__main__':
    main()

