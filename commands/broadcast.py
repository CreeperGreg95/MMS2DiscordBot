import discord
from discord import app_commands
from discord.ext import commands
import os
from mcrcon import MCRcon

RCON_HOST = os.getenv("RCON_HOST", "localhost")
RCON_PORT = int(os.getenv("RCON_PORT", 25575))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")
GUILD_ID = 1033271218247319562  # ton serveur Discord

class Broadcast(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="broadcast",
        description="Envoie un message dans le chat Minecraft (/say)"
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))  # 👈 important !
    async def broadcast(self, interaction: discord.Interaction, message: str):
        try:
            with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
                mcr.command(f"say {message}")
            await interaction.response.send_message(f"✅ Message envoyé : {message}")
        except Exception as e:
            await interaction.response.send_message(f"❌ Erreur : {e}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Broadcast(bot))
