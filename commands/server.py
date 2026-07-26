import discord
from discord import app_commands
from discord.ext import commands
import os
from mcrcon import MCRcon  # pip install mcrcon

# Configuration
STAFF_ROLE_ID = int(os.getenv("STAFF_ROLE_ID", 1121020278126936105))
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", 1033271218247319562))

RCON_HOST = os.getenv("RCON_HOST")
RCON_PORT = int(os.getenv("RCON_PORT", 25575))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")

# Documentation interne du bot
DOC_PAGES = [
    {
        "title": "📖 Documentation `/server` (Accueil)",
        "fields": [
            ("Bienvenue", "Cette documentation présente les commandes principales utilisables via `/server`."),
            ("Navigation", "Utilisez ⬅️ ➡️ pour parcourir les pages.\nUtilisez 🏠 pour revenir ici."),
            ("Important", "⚠️ Cette documentation est réservée aux membres du staff."),
            ("Plus à venir !", "D'autres commandes arriveront plus tard dans cette documentation. Restez à l'affut !")
        ]
    },
    {
        "title": "📖 Documentation `/server` (1/3)",
        "fields": [
            ("stop", "⚠️ Arrête complètement le serveur."),
            ("whitelist on/off", "Active ou désactive la whitelist."),
            ("whitelist add <pseudo>", "Ajoute un joueur à la whitelist."),
        ]
    },
    {
        "title": "📖 Documentation `/server` (2/3)",
        "fields": [
            ("say <message>", "⚠️ Déconseillé. Utilisez plutôt `/broadcast`."),
            ("broadcast <message>", "Envoie un message global à tous les joueurs."),
            ("op <pseudo>", "⚠️ Donne l'OP à un joueur (à utiliser avec prudence)."),
        ]
    },
    {
        "title": "📖 Documentation `/server` (3/3)",
        "fields": [
            ("ban <pseudo>", "⚠️ Bannit un joueur."),
            ("pardon <pseudo>", "Débannit un joueur."),
            ("kick <pseudo>", "Expulse un joueur du serveur."),
        ]
    },
]


class DocView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.page = 0

    def make_embed(self) -> discord.Embed:
        """Crée un embed en fonction de la page courante"""
        page = DOC_PAGES[self.page]
        embed = discord.Embed(title=page["title"], color=discord.Color.green())
        for name, value in page["fields"]:
            embed.add_field(name=name, value=value, inline=False)
        embed.set_footer(text=f"Page {self.page + 1}/{len(DOC_PAGES)}")
        return embed

    async def update_page(self, interaction: discord.Interaction):
        embed = self.make_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
            await self.update_page(interaction)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < len(DOC_PAGES) - 1:
            self.page += 1
            await self.update_page(interaction)

    @discord.ui.button(label="🏠 Home", style=discord.ButtonStyle.primary)
    async def home(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = 0
        await self.update_page(interaction)


class Server(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def run_rcon(self, command: str) -> str:
        try:
            with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
                resp = mcr.command(command)
                return resp if resp else "✅ Commande exécutée avec succès."
        except Exception as e:
            return f"❌ Erreur RCON: {e}"

    @app_commands.command(
        name="server",
        description="Exécuter une commande Minecraft via RCON (staff uniquement)"
    )
    @app_commands.describe(arguments="Commande Minecraft (ex: stop, whitelist on, say Bonjour)")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def server(self, interaction: discord.Interaction, *, arguments: str):
        # Vérification permissions staff
        if not any(r.id == STAFF_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message("❌ Tu n’as pas la permission.", ephemeral=True)
            return

        # Interception du help → doc interne
        if arguments.strip().lower() == "help":
            view = DocView()
            embed = view.make_embed()
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            return

        # Sinon, exécution RCON classique
        response = self.run_rcon(arguments)

        embed = discord.Embed(
            title="🖥️ Commande RCON",
            description=f"**Commande envoyée :** `{arguments}`",
            color=discord.Color.blurple()
        )
        embed.add_field(name="Réponse", value=response, inline=False)

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Server(bot))
