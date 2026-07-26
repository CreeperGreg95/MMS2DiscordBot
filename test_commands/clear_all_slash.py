# clear_all_slash.py
import discord
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID"))  # Mets l'ID de ta guilde

intents = discord.Intents.default()
bot = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(bot)

@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user} ({bot.user.id})")

    # --- Suppression commandes de guilde ---
    guild = discord.Object(id=GUILD_ID)
    tree.clear_commands(guild=guild)
    await tree.sync(guild=guild)
    print("✅ Commandes de guilde supprimées.")

    # --- Suppression commandes globales ---
    tree.clear_commands(guild=None)
    await tree.sync()
    print("✅ Commandes globales supprimées.")

    print("💡 Toutes les commandes slash ont été purgées.")
    await bot.close()

bot.run(TOKEN)
