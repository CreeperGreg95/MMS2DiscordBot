import discord
import re
from discord.ext import commands
from discord import app_commands
from mcrcon import MCRcon
import os

RCON_HOST = os.getenv("RCON_HOST", "localhost")
RCON_PORT = int(os.getenv("RCON_PORT", 25575))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")
GUILD_ID = 1033271218247319562

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

class TPS(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

async def setup(bot):
    await bot.add_cog(TPS(bot))
