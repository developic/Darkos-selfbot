import os
import subprocess
import sys
import asyncio

def install_requirements():
    required_modules = ["discord.py-self", "python-dotenv","rich","requests","aiofiles"]
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
# Auto-comment for Setup.py
