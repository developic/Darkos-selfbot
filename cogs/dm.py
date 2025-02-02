from discord.ext import commands
import discord
import asyncio

class DM(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="dm", help="Send a DM to a user. Usage: !dm <user> <message>")
    async def dm(self, ctx, user: discord.User, *, message: str):
        try:
            async with user.typing():
                await asyncio.sleep(1)  

            await user.send(message)
            await ctx.send(f"✅ Message successfully sent to {user.mention}.")
        
        except discord.Forbidden:
            await ctx.send(f"❌ Cannot send a message to {user.mention}. They may have DMs disabled.")
        except discord.HTTPException as e:
            await ctx.send(f"⚠️ Failed to send DM to {user.mention}. {str(e)}")
        except discord.RateLimited as e:
            await ctx.send(f"⏳ Rate limited! Please wait before sending more DMs. ({e.retry_after} seconds)")
        except Exception as e:
            await ctx.send(f"🚨 An unexpected error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(DM(bot))
