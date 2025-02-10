import discord
from discord.ext import commands
import random
import asyncio

class Hack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="hack")
    async def hack(self, ctx, member: discord.Member):
        message = await ctx.send(f"[*] Starting hack on {member.name}...")

        hack_steps = [
            f"[*] Initializing breach for {member.name}...",
            f"[*] Scanning for vulnerabilities in {member.name}'s network...",
            f"[*] Accessing remote server {member.name}...",
            f"[*] Cracking password for {member.name}... 12% complete",
            f"[*] Bypassing firewall for {member.name}...",
            f"[*] Searching for exploits in {member.name}'s account...",
            f"[*] Cracking password... 45% complete",
            f"[*] Accessing confidential data... 58% complete",
            f"[*] 2FA bypassed for {member.name}. Vulnerability exploited.",
            f"[*] Establishing backdoor access... 79% complete",
            f"[*] Injecting malicious code into {member.name}'s system... 85% complete",
            f"[*] Creating SSH access tunnel for {member.name}...",
            f"[*] Hack complete. Secure shell access established.",
            f"[ALERT] {member.name}'s account compromised. Personal data accessed. 🔓"
        ]

        for step in hack_steps:
            await message.edit(content=f"**[SYSTEM]** {step}")
            await asyncio.sleep(random.uniform(0.5, 1.0))

        await message.edit(content=f"[ALERT] {member.name}'s account has been successfully hacked. 🔓💻")
        await asyncio.sleep(1)

        fake_details = self.generate_fake_details(member)
        await ctx.send(f"**[EXFIL]** Here are some details found from {member.name}:\n\n{fake_details}")

    def generate_fake_details(self, member):
        fake_names = ["JohnDoe", "JaneSmith", "ChrisEvans", "AnnaTaylor"]
        fake_email_providers = ["gmail.com", "yahoo.com", "outlook.com", "protonmail.com"]
        fake_ip_addresses = ["192.168.0.1", "10.0.0.1", "172.16.0.1", "203.0.113.5"]
        fake_phone_numbers = ["+1 800-555-0100", "+1 800-555-0200", "+1 800-555-0300"]
        fake_socials = ["@john_doe123", "@janesmith_45", "@chrisevans_22", "@annataylor_777"]
        fake_credit_cards = ["4111 1111 1111 1111", "5500 0000 0000 0004", "6011 0000 0000 0004", "3400 0000 0000 009"]
        fake_devices = ["Windows 10 PC", "MacBook Pro 2021", "iPhone 13 Pro", "Samsung Galaxy S21"]
        fake_locations = ["New York, USA", "California, USA", "London, UK", "Berlin, Germany"]
        fake_addresses = [f"{random.randint(100, 999)} {random.choice(['Elm St', 'Main Ave', 'Pine Rd'])}, {random.choice(['New York', 'California', 'Texas', 'Florida'])}"]

        fake_name = random.choice(fake_names)
        fake_email = f"{fake_name.lower()}{random.randint(100, 999)}@{random.choice(fake_email_providers)}"
        fake_ip = random.choice(fake_ip_addresses)
        fake_phone = random.choice(fake_phone_numbers)
        fake_social = random.choice(fake_socials)
        fake_credit_card = random.choice(fake_credit_cards)
        fake_device = random.choice(fake_devices)
        fake_location = random.choice(fake_locations)
        fake_address = random.choice(fake_addresses)

        return f"""```Name: {fake_name}\nEmail: {fake_email}\nIP Address: {fake_ip}\nPhone: {fake_phone}\nSocial Media: {fake_social}\nCredit Card: {fake_credit_card}\nDevice: {fake_device}\nLocation: {fake_location}\nAddress: {fake_address}
        ```
        """

    @hack.error
    async def hack_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Please mention a user to hack.")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("Invalid user mentioned. Please mention a valid user.")

async def setup(bot):
    await bot.add_cog(Hack(bot))
