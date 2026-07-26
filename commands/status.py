import discord
import os
import re
from datetime import datetime
from discord.ext import commands
from discord import app_commands
from mcstatus import JavaServer
from dotenv import load_dotenv

# Détecter le dossier racine du projet (1 niveau au-dessus de commands/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Charger le .env depuis le dossier racine
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Chemin absolu vers le log Minecraft
MC_LOG_PATH = os.path.join(BASE_DIR, os.getenv("MC_LOG_PATH", "logs/latest.log"))

RCON_HOST = os.getenv("RCON_HOST", "localhost")
RCON_HOST_PLAYER = os.getenv("RCON_HOST_PLAYER")
MC_SERVER_PORT = int(os.getenv("MC_SERVER_PORT", 25565))
GUILD_ID = 1033271218247319562


def get_server_start_info_and_versions():
    start_time = None
    mc_version = None
    forge_version = None
    try:
        with open(MC_LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                # Début du serveur
                if "Starting minecraft server version" in line and start_time is None:
                    date_str = line.split("]")[0].strip("[")
                    start_time = datetime.strptime(date_str, "%d%b%Y %H:%M:%S.%f")
                    mc_version = line.split("version")[1].strip()
                
                # Version Forge
                elif "Forge mod loading" in line and forge_version is None:
                    match = re.search(r"version (\d+\.\d+\.\d+)", line)
                    if match:
                        forge_version = match.group(1)
    except Exception:
        pass
    return start_time, mc_version, forge_version


class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="status",
        description="Vérifie le statut et le ping du serveur Minecraft"
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def status(self, interaction: discord.Interaction):
        try:
            server = JavaServer.lookup(f"{RCON_HOST}:{MC_SERVER_PORT}")
            status = server.status()
            ping_ms = round(status.latency)
            num_players = status.players.online
            status_text = "✅ Serveur en ligne"
            color = discord.Color.green()
        except Exception:
            status_text = "❌ Serveur hors ligne"
            ping_ms = None
            num_players = None
            color = discord.Color.red()

        start_time, mc_version, forge_version = get_server_start_info_and_versions()
        if start_time:
            uptime = datetime.now() - start_time
            days, remainder = divmod(uptime.total_seconds(), 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_str = f"{int(days)}j {int(hours)}h {int(minutes)}m {int(seconds)}s"
            start_str = start_time.strftime("%d/%m/%Y %H:%M:%S")
        else:
            uptime_str = "Impossible de récupérer"
            start_str = "Impossible de récupérer"

        embed = discord.Embed(
            title="🌐 Statut du serveur",
            description=status_text,
            color=color
        )
        embed.add_field(name="--- Serveur ---", value="\u200b", inline=False)
        embed.add_field(name="Edition", value="Minecraft Java Edition", inline=True)
        embed.add_field(name="Version", value=mc_version or "Impossible de récupérer", inline=True)
        embed.add_field(name="Forge Version", value=forge_version or "Impossible de récupérer", inline=True)
        embed.add_field(name="IP serveur", value=RCON_HOST_PLAYER or RCON_HOST, inline=True)
        if ping_ms is not None:
            embed.add_field(name="Ping du serveur", value=f"{ping_ms} ms", inline=True)
        embed.add_field(name="Démarrage du serveur", value=start_str, inline=True)
        embed.add_field(name="Durée de fonctionnement", value=uptime_str, inline=True)
        if num_players is not None:
            embed.add_field(name="Nombre de joueurs", value=str(num_players), inline=True)

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Status(bot))
