# commands/players.py
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from zoneinfo import ZoneInfo
from mcrcon import MCRcon
import os
from dotenv import load_dotenv

# Charger les variables
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

RCON_HOST = os.getenv("RCON_HOST", "localhost")
RCON_PORT = int(os.getenv("RCON_PORT", 25575))
RCON_PASSWORD = os.getenv("RCON_PASSWORD", "")
MC_SERVER_PORT = int(os.getenv("MC_SERVER_PORT", 25565))
GUILD_ID = 1033271218247319562  # ton serveur Discord

class Players(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="joueurs",
        description="Affiche la liste des joueurs connectés sur le serveur Minecraft"
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def joueurs(self, interaction: discord.Interaction):
        try:
            # Connexion RCON
            with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
                response = mcr.command("list")

            # Exemple de réponse : "Il y a 2 joueurs en ligne: Joueur1, Joueur2"
            parts = response.split(":")
            joueurs_liste = parts[1].strip().split(", ") if len(parts) > 1 and parts[1].strip() else []
            joueurs_connectes = len(joueurs_liste)

            # Pour récupérer le max, on peut parser le début de la réponse
            max_players = 0
            import re
            match = re.search(r"Il y a (\d+) joueur", response)
            if match:
                joueurs_connectes = int(match.group(1))

            # Limite max si dispo dans la config
            joueurs_max = int(os.getenv("MC_MAX_PLAYERS", 3))  # par défaut 20 si non défini
            pourcentage = round((joueurs_connectes / joueurs_max) * 100, 1) if joueurs_max > 0 else 0

            # Format liste
            if joueurs_liste:
                joueurs_str = "\n".join(f"- {p}" for p in joueurs_liste)
            else:
                joueurs_str = "Aucun joueur connecté."

            # Texte limite
            limite_str = f"Limite de joueurs sur le serveur : {joueurs_connectes}/{joueurs_max} ({pourcentage}%)"
            if joueurs_connectes >= joueurs_max:
                limite_str += " - 🚨 Serveur plein."

            # Embed
            paris_time = datetime.now(ZoneInfo("Europe/Paris"))
            embed = discord.Embed(
                title="📋 Liste des joueurs sur le serveur",
                description=(
                    f"Il y a actuellement **{joueurs_connectes}** joueur(s) connecté(s).\n\n"
                    f"{joueurs_str}\n\n"
                    f"{limite_str}"
                ),
                color=discord.Color.blue()
            )
            embed.set_footer(text=paris_time.strftime("%H:%M:%S - %d-%b-%Y"))

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Erreur",
                description=f"Impossible de récupérer la liste des joueurs.\n\nErreur : {e}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Players(bot))
