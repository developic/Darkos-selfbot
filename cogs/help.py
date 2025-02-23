import discord
from discord.ext import commands

class CustomHelp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help", help="help to show command")
    async def help_command(self, ctx, command_name: str = None):
        if command_name: 
            command = self.bot.get_command(command_name)
            if command:
                await ctx.send(f"**Command:** {command.name}\n**Usage:** `{ctx.prefix}{command.name} {command.signature}`\n**Description:** {command.help or 'No description available.'}")
            else:
                await ctx.send("⚠️ Command not found!")
        else:  # Show general help
            help_text = "**Bot Commands:**\n"
            for command in self.bot.commands:
                help_text += f"- **{command.name}**: {command.help or 'No description'}\n"
            await ctx.send(help_text)

async def setup(bot):
    await bot.add_cog(CustomHelp(bot))
    