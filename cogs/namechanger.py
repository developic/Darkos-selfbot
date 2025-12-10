import discord
from discord.ext import commands, tasks
import json
import os
import random
import asyncio


USERNAME_FILE = "user.json"


class AutoProfileChanger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.display_names = []
        self.load_config()
        self.display_name_changer.start()


    def cog_unload(self):
        self.display_name_changer.cancel()


    def load_config(self):
        if os.path.exists(USERNAME_FILE):
            with open(USERNAME_FILE, "r") as f:
                data = json.load(f)
                self.display_names = data.get("display_names", [])
                print(f"Loaded {len(self.display_names)} display names from user.json")
        else:
            # Create default user.json file with psychologically invisible names
            default_data = {
                "display_names": [
                    "john",
                    "mike",
                    "steve",
                    "dave",
                    "tom",
                    "bob",
                    "sola",
                    "poul",
                    "last",
                    "jim",
                    "joe",
                    "ryan",
                    "mark",
                    "luke",
                    "paul"
                ]
            }
            with open(USERNAME_FILE, "w") as f:
                json.dump(default_data, f, indent=4)
            self.display_names = default_data["display_names"]
            print(f"Created user.json with default configuration")


    @tasks.loop(hours=2)
    async def display_name_changer(self):
        if not self.display_names:
            return

        # Pick a random display name instead of cycling
        new_display_name = random.choice(self.display_names)

        try:
            await self.bot.user.edit(global_name=new_display_name)
            print(f"Changed display name to: {new_display_name}")
            
            # Tell AutoButtonClick to skip next 3 buttons
            button_cog = self.bot.get_cog("AutoButtonClick")
            if button_cog:
                button_cog.skip_next_buttons(3)
        except Exception as e:
            print(f"Error: {e}")


    @display_name_changer.before_loop
    async def before_display_name_changer(self):
        await self.bot.wait_until_ready()
        # Random initial delay (0-30 minutes) to avoid starting immediately
        initial_delay = random.uniform(0, 1800)
        await asyncio.sleep(initial_delay)


    @commands.command(name="changenow", help="Manually change display name immediately without waiting.")
    async def change_now(self, ctx):
        if not self.display_names:
            print("No display names available.")
            return

        # Pick a random display name
        new_display_name = random.choice(self.display_names)

        try:
            await self.bot.user.edit(global_name=new_display_name)
            print(f"Manually changed display name to: {new_display_name}")
            
            # Tell AutoButtonClick to skip next 3 buttons
            button_cog = self.bot.get_cog("AutoButtonClick")
            if button_cog:
                button_cog.skip_next_buttons(3)
        except Exception as e:
            print(f"Error: {e}")


async def setup(bot):
    await bot.add_cog(AutoProfileChanger(bot))
