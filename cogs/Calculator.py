# Auto-comment for Calculator.py
import re
from discord.ext import commands

class Calculator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="cr", help="Perform arithmetic operations. Usage: !cr <expression>")
    async def calculator(self, ctx, *, expression: str):
        """
        Perform calculations using mathematical expressions.
        Supports operators: +, -, *, /, and parentheses.
        """
        try:
            # Preprocess the expression to ensure valid syntax
            expression = self.preprocess_expression(expression)
            
            # Safely evaluate the mathematical expression
            result = eval(expression, {"__builtins__": None}, {})
            await ctx.send(f"The result of `{expression}` is: {result}")
        except ZeroDivisionError:
            await ctx.send("Error: Division by zero is not allowed!")
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")

    def preprocess_expression(self, expression):
        """
        Preprocess the input expression to handle implicit multiplication and standardize operators.
        """
        # Replace × and ÷ with * and / respectively
        expression = expression.replace("×", "*").replace("÷", "/")

        # Add explicit multiplication for cases like 2(6 - 4) or 7(1 ÷ 6)
        expression = re.sub(r"(\d)\s*\(", r"\1*(", expression)  # e.g., 7(1 ÷ 6) -> 7*(1 ÷ 6)
        expression = re.sub(r"\)\s*(\d)", r")*\1", expression)  # e.g., (6 - 4)2 -> (6 - 4)*2

        return expression

# Setup function to add the cog
async def setup(bot):
    await bot.add_cog(Calculator(bot))
# Auto-comment for Calculator.py
