# Auto-comment for dm.py
from discord.ext import commands
import discord
import asyncio

class DM(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="dm", help="Send a DM to a user. Usage: !dm <user> <message>")
    async def dm(self, ctx, user: discord.User, *, message: str):
        """
        Send a direct message to a mentioned user or user ID with the specified message, with a delay to avoid triggering captchas.
        """
        try:
            # Delay before sending the message to avoid captchas
            await asyncio.sleep(2)  # Introduces a 2-second delay
            await user.send(message)
            await ctx.send(f"Message sent to {user.mention}.")
        except discord.Forbidden:
            await ctx.send(f"Error: I cannot send a message to {user.mention}. They may have DMs disabled.")
        except discord.HTTPException as e:
            await ctx.send(f"Error: Failed to send DM to {user.mention}. {str(e)}")
        except Exception as e:
            await ctx.send(f"An unexpected error occurred: {str(e)}")

# Setup function to add the cog
async def setup(bot):
    await bot.add_cog(DM(bot))
# Auto-comment for dm.py
