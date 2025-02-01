# Auto-comment for Selfclear.py
from discord.ext import commands

class ClearMessages(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="cl", help="Delete the last 20 messages sent by you.")
    async def clear_messages(self, ctx):
        """Delete the last 20 messages sent by the bot user in the current channel."""
        if ctx.guild is None:
            await ctx.send("This command cannot be used in direct messages.")
            return

        deleted_count = 0
        async for message in ctx.channel.history(limit=100): 
            if message.author.id == self.bot.user.id:  
                await message.delete()
                deleted_count += 1
                if deleted_count == 20:
                    break

        await ctx.send(f"Deleted {deleted_count} messages sent by you.", delete_after=5)

async def setup(bot):
    await bot.add_cog(ClearMessages(bot))
# Auto-comment for Selfclear.py
