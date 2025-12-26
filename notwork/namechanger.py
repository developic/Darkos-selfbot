import discord
from discord.ext import commands, tasks
import json
import os
import random
import asyncio


USERNAME_FILE = "user.json"
PROCESS_FILE = "process_mode.json"


class AutoProfileChanger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.is_primary = getattr(bot, '_is_primary', True)
        self.bot_name = getattr(bot, '_bot_name', 'Bot')
        self.display_names = []
        
        # Only initialize for primary bot (Bot 1)
        if self.is_primary:
            self.load_config()
            self.check_and_start_changer()
        else:
            print(f"[{self.bot_name}] Profile changer disabled (Secondary bot)")


    def cog_unload(self):
        if hasattr(self, 'display_name_changer') and self.display_name_changer.is_running():
            self.display_name_changer.cancel()


    def load_config(self):
        """Load display names from JSON file"""
        if os.path.exists(USERNAME_FILE):
            with open(USERNAME_FILE, "r") as f:
                data = json.load(f)
                self.display_names = data.get("display_names", [])
                print(f"[{self.bot_name}] Loaded {len(self.display_names)} display names from user.json")
        else:
            # Create default user.json file
            default_data = {
                "display_names": [
                    "john", "mike", "steve", "dave", "tom",
                    "bob", "sola", "poul", "last", "jim",
                    "joe", "ryan", "mark", "luke", "paul"
                ]
            }
            with open(USERNAME_FILE, "w") as f:
                json.dump(default_data, f, indent=4)
            self.display_names = default_data["display_names"]
            print(f"[{self.bot_name}] Created user.json with default configuration")


    def get_current_process(self):
        """Get the current process mode from file"""
        if os.path.exists(PROCESS_FILE):
            with open(PROCESS_FILE, "r") as f:
                data = json.load(f)
                return data.get("process", 1)
        return 1


    def check_and_start_changer(self):
        """Start name changer only if in Process 1 mode"""
        current_process = self.get_current_process()
        
        if current_process == 1:
            if not hasattr(self, 'display_name_changer'):
                # First time initialization
                self.display_name_changer.start()
                print(f"[{self.bot_name}] ✓ Display name changer started (Process 1 mode)")
            elif not self.display_name_changer.is_running():
                self.display_name_changer.start()
                print(f"[{self.bot_name}] ✓ Display name changer resumed (Process 1 mode)")
        else:
            if hasattr(self, 'display_name_changer') and self.display_name_changer.is_running():
                self.display_name_changer.cancel()
                print(f"[{self.bot_name}] ⏸️  Display name changer paused (Process 2 mode)")


    @tasks.loop(hours=2)
    async def display_name_changer(self):
        """Automatically change display name every 2 hours (Process 1 only)"""
        # Check if we're still in Process 1 mode
        if self.get_current_process() != 1:
            print(f"[{self.bot_name}] Skipping name change (Not in Process 1)")
            return

        if not self.display_names:
            print(f"[{self.bot_name}] No display names available")
            return

        # Pick a random display name
        new_display_name = random.choice(self.display_names)

        try:
            await self.bot.user.edit(global_name=new_display_name)
            print(f"[{self.bot_name}] 🔄 Changed display name to: {new_display_name}")
            
            # Tell AutoButtonClick to skip next 3 buttons
            button_cog = self.bot.get_cog("AutoButtonClick")
            if button_cog:
                button_cog.skip_next_buttons(3)
                print(f"[{self.bot_name}] ⏭️  Next 3 buttons will be skipped")
        except discord.errors.HTTPException as e:
            if "rate limited" in str(e).lower():
                print(f"[{self.bot_name}] ⚠️  Rate limited! Try again later")
            else:
                print(f"[{self.bot_name}] ✗ Error changing name: {e}")
        except Exception as e:
            print(f"[{self.bot_name}] ✗ Error: {e}")


    @display_name_changer.before_loop
    async def before_display_name_changer(self):
        """Wait for bot to be ready and add initial random delay"""
        await self.bot.wait_until_ready()
        
        # Random initial delay (0-30 minutes) to avoid starting immediately
        initial_delay = random.uniform(0, 1800)
        print(f"[{self.bot_name}] Waiting {initial_delay/60:.1f} minutes before first name change...")
        await asyncio.sleep(initial_delay)


    @commands.command(name="changenow", help="Manually change display name immediately (Process 1 only)")
    async def change_now(self, ctx):
        """Manually trigger name change"""
        # Only work for primary bot
        if not self.is_primary:
            print(f"[{self.bot_name}] Name change is only available on Bot 1")
            return
        
        # Only work in Process 1 mode
        if self.get_current_process() != 1:
            print(f"[{self.bot_name}] Name change is only available in Process 1 mode")
            print("Use !process 1 to switch to Process 1")
            return
            
        if not self.display_names:
            print(f"[{self.bot_name}] No display names available")
            return

        # Pick a random display name
        new_display_name = random.choice(self.display_names)

        try:
            await self.bot.user.edit(global_name=new_display_name)
            print(f"[{self.bot_name}] 🔄 Manually changed display name to: {new_display_name}")
            
            # Tell AutoButtonClick to skip next 3 buttons
            button_cog = self.bot.get_cog("AutoButtonClick")
            if button_cog:
                button_cog.skip_next_buttons(3)
                print(f"[{self.bot_name}] ⏭️  Next 3 buttons will be skipped")
        except discord.errors.HTTPException as e:
            if "rate limited" in str(e).lower():
                print(f"[{self.bot_name}] ⚠️  Rate limited! Try again later")
            else:
                print(f"[{self.bot_name}] ✗ Error changing name: {e}")
        except Exception as e:
            print(f"[{self.bot_name}] ✗ Error: {e}")


    @commands.command(name="addname", help="Add a new display name to the list. Usage: !addname <name>")
    async def add_name(self, ctx, name: str):
        """Add a new display name to the rotation"""
        if not self.is_primary:
            return
        
        if name in self.display_names:
            print(f"[{self.bot_name}] '{name}' is already in the list")
            return
        
        self.display_names.append(name)
        
        # Save to file
        data = {"display_names": self.display_names}
        with open(USERNAME_FILE, "w") as f:
            json.dump(data, f, indent=4)
        
        print(f"[{self.bot_name}] ✓ Added '{name}' to display names ({len(self.display_names)} total)")


    @commands.command(name="removename", help="Remove a display name from the list. Usage: !removename <name>")
    async def remove_name(self, ctx, name: str):
        """Remove a display name from the rotation"""
        if not self.is_primary:
            return
        
        if name not in self.display_names:
            print(f"[{self.bot_name}] '{name}' is not in the list")
            return
        
        self.display_names.remove(name)
        
        # Save to file
        data = {"display_names": self.display_names}
        with open(USERNAME_FILE, "w") as f:
            json.dump(data, f, indent=4)
        
        print(f"[{self.bot_name}] ✓ Removed '{name}' from display names ({len(self.display_names)} total)")


    @commands.command(name="listnames", help="Show all available display names")
    async def list_names(self, ctx):
        """List all display names in rotation"""
        if not self.is_primary:
            return
        
        if not self.display_names:
            print(f"[{self.bot_name}] No display names configured")
            return
        
        print(f"\n[{self.bot_name}] === DISPLAY NAMES ({len(self.display_names)}) ===")
        for i, name in enumerate(self.display_names, 1):
            print(f"  {i}. {name}")
        print("=" * 40 + "\n")


    @commands.command(name="nameinterval", help="Change the name change interval in hours. Usage: !nameinterval <hours>")
    async def change_interval(self, ctx, hours: float):
        """Change how often the name changes"""
        if not self.is_primary:
            return
        
        if hours < 0.1 or hours > 24:
            print(f"[{self.bot_name}] Interval must be between 0.1 and 24 hours")
            return
        
        # Restart the loop with new interval
        if hasattr(self, 'display_name_changer') and self.display_name_changer.is_running():
            self.display_name_changer.cancel()
        
        self.display_name_changer.change_interval(hours=hours)
        self.display_name_changer.start()
        
        print(f"[{self.bot_name}] ✓ Name change interval set to {hours} hours")


async def setup(bot):
    await bot.add_cog(AutoProfileChanger(bot))
