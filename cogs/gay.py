# Auto-comment for gay.py
import random
from discord.ext import commands

class GayHeritage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="gay", help="Check someone's gay heritage. Usage: !gay <user>")
    async def gay(self, ctx, user: commands.MemberConverter):
        """
        Check someone's gay heritage by giving them a random percentage.
        """
        # Generate a random percentage between 1 and 100
        gay_percentage = random.randint(1, 100)
        
        # Send the result
        await ctx.send(f"{user.mention} is {gay_percentage}% gay! 🌈")

# Setup function to add the cog
async def setup(bot):
    await bot.add_cog(GayHeritage(bot))
# Auto-comment for gay.py
