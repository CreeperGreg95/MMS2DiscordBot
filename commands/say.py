import discord
from discord.ext import commands
from discord import app_commands

GUILD_ID = 1033271218247319562

class Say(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

async def setup(bot):
    await bot.add_cog(Say(bot))
