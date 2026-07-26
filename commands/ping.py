import discord
from discord.ext import commands
from discord import app_commands

GUILD_ID = 1033271218247319562

class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

async def setup(bot):
    await bot.add_cog(Ping(bot))
