import discord
import os
import re
from discord.ext import commands
from discord import app_commands
from mcstatus import JavaServer
from mcrcon import MCRcon
from dotenv import load_dotenv

# Détecter le dossier racine du projet pour charger le .env
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Configuration récupérée du .env
RCON_HOST = os.getenv("RCON_HOST", "163.5.121.201")
RCON_HOST_PLAYER = os.getenv("RCON_HOST_PLAYER", RCON_HOST)
RCON_PORT = int(os.getenv("RCON_PORT", 25567))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")
MC_SERVER_PORT = int(os.getenv("MC_SERVER_PORT", 25566))
GUILD_ID = int(os.getenv("GUILD_ID", 1033271218247319562))

class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="status",
        description="Affiche les détails techniques et le statut du serveur Minecraft"
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def status(self, interaction: discord.Interaction):
        # 1. On prévient Discord que la requête peut prendre du temps (évite le timeout)
        await interaction.response.defer()

        # Variables par défaut
        online = False
        mc_version = "Inconnue"
        forge_version = "Inconnue"
        players_online = 0
        players_max = 0
        ping = "N/A"
        
        # --- ÉTAPE 1 : Récupération via MCSTATUS (Port 25566) ---
        try:
            server = JavaServer.lookup(f"{RCON_HOST}:{MC_SERVER_PORT}", timeout=3)
            query = server.status()
            
            online = True
            players_online = query.players.online
            players_max = query.players.max
            ping = f"{round(query.latency)} ms"
            mc_version = query.version.name # Récupère souvent "1.16.5" ou "Forge 1.16.5"
        except Exception as e:
            print(f"[DEBUG] Erreur mcstatus: {e}")

        # --- ÉTAPE 2 : Récupération via RCON (Port 25567) si possible ---
        # On utilise RCON pour essayer de trouver la version Forge précise
        if RCON_PASSWORD:
            try:
                with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT, timeout=3) as mcr:
                    # On demande la version au serveur
                    resp = mcr.command("version")
                    # On cherche un numéro de version type X.X.X dans la réponse
                    match = re.search(r"version ([\d\.]+)", resp)
                    if match:
                        forge_version = match.group(1)
                    
                    # Si mcstatus a échoué mais que RCON répond, le serveur est ON
                    if not online:
                        online = True
                        status_rcon = mcr.command("list")
                        # Extraction basique des joueurs via RCON
                        p_match = re.search(r"(\d+) of a max of (\d+)", status_rcon)
                        if p_match:
                            players_online = p_match.group(1)
                            players_max = p_match.group(2)
            except Exception as e:
                print(f"[DEBUG] Erreur RCON: {e}")

        # --- ÉTAPE 3 : Construction de l'Embed ---
        if online:
            color = discord.Color.green()
            status_desc = "✅ **Serveur en ligne**"
        else:
            color = discord.Color.red()
            status_desc = "❌ **Serveur hors ligne**"

        embed = discord.Embed(
            title="🌐 Statut Technique du Serveur",
            description=status_desc,
            color=color
        )

        embed.add_field(name="--- Informations ---", value="\u200b", inline=False)
        embed.add_field(name="🎮 Édition", value="Java (Forge)", inline=True)
        embed.add_field(name="📌 Version MC", value=mc_version, inline=True)
        embed.add_field(name="🛠️ Version Forge", value=forge_version, inline=True)
        
        embed.add_field(name="--- Réseau ---", value="\u200b", inline=False)
        embed.add_field(name="📡 IP", value=f"`{RCON_HOST_PLAYER}`", inline=True)
        embed.add_field(name="⚡ Ping", value=ping, inline=True)
        embed.add_field(name="👥 Joueurs", value=f"{players_online} / {players_max}", inline=True)

        embed.set_footer(text=f"Demandé par {interaction.user.display_name} • {interaction.created_at.strftime('%H:%M:%S')}")
        
        # Envoi de la réponse finale
        await interaction.edit_original_response(embed=embed)

async def setup(bot):
    await bot.add_cog(Status(bot))