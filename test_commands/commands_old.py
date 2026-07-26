import discord
import os
import re
from datetime import datetime
from mcrcon import MCRcon
from dotenv import load_dotenv
from discord.ext import commands
from discord import app_commands
from mcstatus import JavaServer  # Pour obtenir le ping réel du serveur

load_dotenv()
RCON_HOST = os.getenv("RCON_HOST", "localhost")
RCON_HOST_PLAYER = os.getenv("RCON_HOST_PLAYER")
RCON_PORT = int(os.getenv("RCON_PORT", 25575))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")
MC_SERVER_PORT = int(os.getenv("MC_SERVER_PORT", 25565))  # Port Minecraft normal
GUILD_ID = 1033271218247319562
MC_LOG_PATH = os.getenv("MC_LOG_PATH")

DIMENSIONS_UI = {
    "minecraft:overworld": "Overworld",
    "minecraft:the_nether": "Nether",
    "minecraft:the_end": "End",
    "boss_tools:mercury": "Mercure",
    "boss_tools:mercury_orbit": "Orbite de Mercure",
    "boss_tools:venus": "Venus",
    "boss_tools:venus_orbit": "Orbite de Venus",
    "boss_tools:overworld_orbit": "Orbite de l'Overworld",
    "boss_tools:moon": "Lune",
    "boss_tools:moon_orbit": "Orbite de la Lune",
    "boss_tools:mars": "Mars",
    "boss_tools:mars_orbit": "Orbite de Mars",
    "allthemodium:mining": "Dimension Minage",
    "allthemodium:the_other": "Dimension 'The Other'"
}

def get_server_start_info_and_versions():
    """
    Lit le latest.log pour récupérer :
    - date de démarrage
    - version Minecraft
    - version Forge
    """
    start_time = None
    mc_version = None
    forge_version = None
    try:
        with open(MC_LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                # Récupère la date de démarrage et version Minecraft
                if "Starting minecraft server version" in line and start_time is None:
                    date_str = line.split("]")[0].strip("[")
                    try:
                        start_time = datetime.strptime(date_str, "%d%b%Y %H:%M:%S.%f")
                    except ValueError:
                        start_time = None
                    mc_version = line.split("version")[1].strip()
                
                # Récupère uniquement la version numérique de Forge
                if "Forge mod loading" in line and forge_version is None:
                    match = re.search(r"Forge mod loading, version ([\d\.]+)", line)
                    if match:
                        forge_version = match.group(1)  # <-- juste "36.2.42"
    except Exception:
        pass
    return start_time, mc_version, forge_version

class BotCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ------------------- PING -------------------
    @app_commands.command(
        name="ping",
        description="Vérifie la latence du bot"
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def ping(self, interaction: discord.Interaction):
        latency_ms = round(self.bot.latency * 1000)
        embed = discord.Embed(
            title="🏓 Pong !",
            description=f"Latence du bot : {latency_ms} ms",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"{interaction.user} • {interaction.created_at}")
        await interaction.response.send_message(embed=embed)

    # ------------------- STATUS -------------------
    @app_commands.command(
        name="status",
        description="Vérifie le statut et le ping du serveur Minecraft"
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def status(self, interaction: discord.Interaction):
        # Ping serveur et nombre de joueurs
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

        # Récupération du log
        start_time, mc_version, forge_version = get_server_start_info_and_versions()
        if start_time:
            now = datetime.now()
            uptime = now - start_time
            days, remainder = divmod(uptime.total_seconds(), 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_str = f"{int(days)}j {int(hours)}h {int(minutes)}m {int(seconds)}s"
            start_str = start_time.strftime("%d/%m/%Y %H:%M:%S")
        else:
            uptime_str = "Impossible de récupérer"
            start_str = "Impossible de récupérer"

        # Embed
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

    # ------------------- SAY -------------------
    @app_commands.command(
        name="say",
        description="Fait dire quelque chose au bot"
    )
    @app_commands.describe(message="Le message que le bot doit dire")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def say(self, interaction: discord.Interaction, message: str):
        await interaction.response.send_message(
            "Cette commande est temporairement désactivée pour le moment."
        )

    # ------------------- TPS -------------------
    @app_commands.command(
        name="tps",
        description="Affiche le TPS et le temps de tick du serveur Minecraft"
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def tps(self, interaction: discord.Interaction):
        try:
            with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
                response = mcr.command("forge tps")
        except Exception:
            await interaction.response.send_message(
                "❌ Impossible de récupérer les TPS du serveur.", ephemeral=True
            )
            return

        dim_pattern = re.compile(
            r"Dim ([\w_:]+).*?: Mean tick time: ([\d\.]+) ms. Mean TPS: ([\d\.]+)"
        )
        matches = dim_pattern.findall(response)

        embed = discord.Embed(
            title="⏱️ TPS du Serveur Minecraft", color=discord.Color.green()
        )

        for category_name, dims in [
            ("----Minecraft----", ["minecraft:overworld", "minecraft:the_nether", "minecraft:the_end"]),
            ("----Système Solaire (Boss Tools Mod)----", [
                "boss_tools:mercury", "boss_tools:mercury_orbit", "boss_tools:venus", 
                "boss_tools:venus_orbit", "boss_tools:overworld_orbit", "boss_tools:moon", 
                "boss_tools:moon_orbit", "boss_tools:mars", "boss_tools:mars_orbit"
            ]),
            ("----Dimensions All The Modium----", ["allthemodium:mining", "allthemodium:the_other"])
        ]:
            embed.add_field(name=category_name, value="\u200b", inline=False)
            for dim, time, tps in matches:
                if dim in dims:
                    name = DIMENSIONS_UI.get(dim, dim.split(":")[1].capitalize())
                    embed.add_field(name=name, value=f"TPS : {tps} ({time} ms)", inline=False)

        overall_match = re.search(
            r"Overall: Mean tick time: ([\d\.]+) ms. Mean TPS: ([\d\.]+)", response
        )
        if overall_match:
            overall_time = overall_match.group(1)
            overall_tps = overall_match.group(2)
            embed.add_field(
                name="--------\nServer Overall (en moyenne)",
                value=f"TPS : {overall_tps} / {overall_time} ms",
                inline=False
            )

        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(BotCommands(bot))
