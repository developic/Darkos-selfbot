import discord
from discord.ext import commands
import aiohttp
import subprocess
from datetime import datetime
from typing import Optional, Dict
import asyncio
import os
import base64

class CaptchaJoiner(commands.Cog):
    """
    Join servers and forward captcha to you for manual solving.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot_name = getattr(bot, '_bot_name', 'Bot')
        
        # Channel to send captcha notifications (optional)
        self.captcha_channel_id = None  # Set this to your channel ID
        
        # Pending captcha challenges
        self.pending_captcha: Optional[Dict] = None
        
        self._log("Captcha joiner initialized")

    def _log(self, msg: str, level: str = "INFO") -> None:
        """Centralized logging"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{self.bot_name}] [{level}] {msg}")

    def notify(self, title: str, body: str, urgency: str = "normal") -> None:
        """Send desktop notification"""
        try:
            subprocess.run(
                ['notify-send', '-u', urgency, '-a', 'Discord Captcha', '-i', 'dialog-warning', title, body],
                timeout=2,
                check=False
            )
        except Exception as e:
            self._log(f"Notification failed: {e}", "WARNING")

    async def download_captcha_image(self, url: str, filename: str = "captcha.png") -> Optional[str]:
        """Download captcha image to local file"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        filepath = f"/tmp/{filename}"
                        with open(filepath, 'wb') as f:
                            f.write(await resp.read())
                        self._log(f"Captcha image saved: {filepath}")
                        return filepath
        except Exception as e:
            self._log(f"Failed to download captcha: {e}", "ERROR")
        return None

    def rofi_input(self, prompt: str, info: str = "", image_path: Optional[str] = None) -> tuple[Optional[str], int]:
        """
        Show Rofi input for captcha solving
        Returns (text, exit_code)
        """
        try:
            cmd = [
                'rofi',
                '-dmenu',
                '-p', prompt,
                '-theme-str', 'window {width: 60%;}',
                '-theme-str', 'listview {enabled: false;}',
                '-theme-str', 'entry {placeholder: "Type captcha solution...";}',
                '-l', '0',
                '-format', 's',
            ]
            
            if info:
                cmd.extend(['-mesg', info])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            text = result.stdout.strip()
            return (text if text else None, result.returncode)
                
        except subprocess.TimeoutExpired:
            self._log("Rofi timeout", "WARNING")
            return (None, 1)
        except Exception as e:
            self._log(f"Rofi error: {e}", "ERROR")
            return (None, 1)

    async def show_captcha_image(self, image_path: str) -> None:
        """Display captcha image using feh or xdg-open"""
        try:
            # Try feh first (image viewer)
            subprocess.Popen(['feh', '--title', 'Discord Captcha', image_path], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            try:
                # Fallback to xdg-open
                subprocess.Popen(['xdg-open', image_path], 
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL)
            except Exception as e:
                self._log(f"Failed to open image: {e}", "WARNING")

    async def solve_captcha_prompt(self, captcha_data: Dict) -> Optional[str]:
        """
        Show captcha to user and get manual solution
        """
        invite_code = captcha_data.get('invite', 'Unknown')
        captcha_url = captcha_data.get('captcha_url', '')
        captcha_sitekey = captcha_data.get('sitekey', '')
        captcha_rqdata = captcha_data.get('rqdata', '')
        captcha_rqtoken = captcha_data.get('rqtoken', '')
        
        self._log(f"🔐 Captcha challenge detected for invite: {invite_code}")
        
        # Desktop notification
        self.notify(
            "🔐 Captcha Challenge!",
            f"Server: {invite_code}\nSolve the captcha in the popup window",
            urgency="critical"
        )
        
        # Download and display captcha image if URL provided
        image_path = None
        if captcha_url:
            image_path = await self.download_captcha_image(captcha_url)
            if image_path:
                await self.show_captcha_image(image_path)
        
        # Build info message
        info = (
            f"<b>🔐 Captcha Challenge</b>\n"
            f"Server Invite: <b>{invite_code}</b>\n"
            f"Sitekey: <tt>{captcha_sitekey[:30]}...</tt>\n\n"
            f"<i>Solve the captcha in the image window and type solution below</i>"
        )
        
        loop = asyncio.get_event_loop()
        
        # Show input prompt
        solution, exit_code = await loop.run_in_executor(
            None,
            self.rofi_input,
            "Captcha Solution",
            info,
            image_path
        )
        
        # Clean up image
        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
            except:
                pass
        
        if exit_code == 0 and solution:
            self._log(f"✓ Captcha solution provided: {solution[:20]}...")
            return solution
        else:
            self._log("⏭️  Captcha solving canceled")
            return None

    async def send_captcha_to_discord(self, captcha_data: Dict) -> None:
        """Send captcha notification to Discord channel"""
        if not self.captcha_channel_id:
            return
        
        channel = self.bot.get_channel(self.captcha_channel_id)
        if not channel:
            return
        
        invite_code = captcha_data.get('invite', 'Unknown')
        captcha_url = captcha_data.get('captcha_url', '')
        captcha_sitekey = captcha_data.get('sitekey', '')
        
        embed = discord.Embed(
            title="🔐 Captcha Challenge Detected",
            description=f"**Invite:** `{invite_code}`",
            color=0xFFA500,
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(name="Sitekey", value=f"``````", inline=False)
        embed.add_field(name="Action", value="Solve via `!solvecaptcha <solution>`", inline=False)
        
        try:
            if captcha_url:
                await channel.send(embed=embed)
                await channel.send(f"Captcha Image: {captcha_url}")
            else:
                await channel.send(embed=embed)
        except Exception as e:
            self._log(f"Failed to send to Discord: {e}", "ERROR")

    @commands.command(name="joinserver")
    async def join_server(self, ctx, invite_code: str):
        """
        Join a Discord server with captcha support
        Usage: !joinserver abc123
        """
        self._log(f"📥 Attempting to join: {invite_code}")
        
        try:
            # Fetch invite info
            invite = await self.bot.fetch_invite(invite_code)
            server_name = invite.guild.name if invite.guild else "Unknown"
            
            self._log(f"📋 Invite info: {server_name}")
            
            # Attempt to join
            try:
                # This will raise CaptchaRequired if captcha is needed
                guild = await invite.accept()
                
                self._log(f"✅ Successfully joined: {server_name}")
                await ctx.send(f"✅ Successfully joined **{server_name}**!")
                
                # Desktop notification
                self.notify("✅ Server Joined", f"Joined: {server_name}")
                
            except discord.errors.CaptchaRequired as captcha_exc:
                # Captcha challenge detected!
                self._log(f"🔐 Captcha required for: {server_name}")
                
                # Prepare captcha data
                captcha_data = {
                    'invite': invite_code,
                    'server_name': server_name,
                    'sitekey': captcha_exc.sitekey,
                    'rqdata': getattr(captcha_exc, 'rqdata', ''),
                    'rqtoken': getattr(captcha_exc, 'rqtoken', ''),
                    'captcha_url': f"https://discord.com/api/v9/captcha/image?captcha_key={captcha_exc.sitekey[:20]}"  # Example URL
                }
                
                # Save pending captcha
                self.pending_captcha = captcha_data
                
                # Send to Discord channel
                await self.send_captcha_to_discord(captcha_data)
                
                # Show captcha to user
                solution = await self.solve_captcha_prompt(captcha_data)
                
                if solution:
                    # Retry join with captcha solution
                    try:
                        await ctx.send(f"🔄 Retrying join with captcha solution...")
                        
                        # Submit captcha solution and retry
                        # Note: Actual implementation depends on discord.py-self library
                        # This is a placeholder for the captcha submission flow
                        
                        guild = await self.bot.http.request(
                            discord.http.Route('POST', f'/invites/{invite_code}'),
                            json={
                                'captcha_key': solution,
                                'captcha_rqtoken': captcha_data.get('rqtoken', '')
                            }
                        )
                        
                        self._log(f"✅ Joined with captcha: {server_name}")
                        await ctx.send(f"✅ Successfully joined **{server_name}** after solving captcha!")
                        
                        # Clear pending
                        self.pending_captcha = None
                        
                    except Exception as e:
                        self._log(f"❌ Captcha solution failed: {e}", "ERROR")
                        await ctx.send(f"❌ Captcha solution failed: {e}")
                else:
                    await ctx.send(f"⏭️  Captcha solving canceled. Use `!solvecaptcha <solution>` to retry.")
        
        except discord.errors.NotFound:
            self._log(f"❌ Invalid invite: {invite_code}", "ERROR")
            await ctx.send(f"❌ Invalid invite code: `{invite_code}`")
            
        except discord.errors.HTTPException as e:
            self._log(f"❌ HTTP error: {e}", "ERROR")
            await ctx.send(f"❌ Error joining server: {e}")
            
        except Exception as e:
            self._log(f"❌ Unexpected error: {e}", "ERROR")
            await ctx.send(f"❌ Unexpected error: {e}")

    @commands.command(name="solvecaptcha")
    async def solve_captcha_command(self, ctx, *, solution: str):
        """
        Submit captcha solution manually
        Usage: !solvecaptcha <your_solution>
        """
        if not self.pending_captcha:
            await ctx.send("❌ No pending captcha to solve")
            return
        
        invite_code = self.pending_captcha.get('invite', '')
        server_name = self.pending_captcha.get('server_name', 'Unknown')
        
        self._log(f"🔑 Manual captcha solution: {solution[:20]}...")
        
        try:
            await ctx.send(f"🔄 Attempting to join with your solution...")
            
            # Retry join with captcha solution
            guild = await self.bot.http.request(
                discord.http.Route('POST', f'/invites/{invite_code}'),
                json={
                    'captcha_key': solution,
                    'captcha_rqtoken': self.pending_captcha.get('rqtoken', '')
                }
            )
            
            self._log(f"✅ Joined with manual captcha: {server_name}")
            await ctx.send(f"✅ Successfully joined **{server_name}**!")
            
            # Clear pending
            self.pending_captcha = None
            
            # Notification
            self.notify("✅ Captcha Solved", f"Joined: {server_name}")
            
        except Exception as e:
            self._log(f"❌ Captcha solution failed: {e}", "ERROR")
            await ctx.send(f"❌ Failed to join: {e}\nTry again with `!solvecaptcha <solution>`")

    @commands.command(name="cancelcaptcha")
    async def cancel_captcha(self, ctx):
        """Cancel pending captcha"""
        if self.pending_captcha:
            invite = self.pending_captcha.get('invite', 'Unknown')
            self.pending_captcha = None
            self._log(f"⏭️  Canceled captcha for: {invite}")
            await ctx.send(f"⏭️  Canceled captcha challenge")
        else:
            await ctx.send("📭 No pending captcha")

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Log when ready"""
        self._log("✓ Captcha joiner ready")
        self._log(f"   {self.bot.user.name}")

async def setup(bot: commands.Bot) -> None:
    """Setup cog"""
    await bot.add_cog(CaptchaJoiner(bot))
