# Auto-comment for Calculator.py
import re
from discord.ext import commands

class Calculator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="cr", help="Perform arithmetic operations. Usage: !cr <expression>")
    async def calculator(self, ctx, *, expression: str):
        try:
            
            expression = self.preprocess_expression(expression)
            result = eval(expression, {"__builtins__": None}, {})
            await ctx.send(f"The result of `{expression}` is: {result}")
        except ZeroDivisionError:
            await ctx.send("Error: Division by zero is not allowed!")
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")

    def preprocess_expression(self, expression):
        expression = expression.replace("×", "*").replace("÷", "/")


        expression = re.sub(r"(\d)\s*\(", r"\1*(", expression)  
        expression = re.sub(r"\)\s*(\d)", r")*\1", expression)

        return expression

# Setup 
async def setup(bot):
    await bot.add_cog(Calculator(bot))
