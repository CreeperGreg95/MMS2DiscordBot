import discord
from discord import app_commands
from discord.ext import commands
import os
import nbtlib
import json
from datetime import datetime, timezone

# Configuration
STAFF_ROLE_ID = int(os.getenv("STAFF_ROLE_ID", 1121020278126936105))
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", 1033271218247319562))
PLAYERDATA_DIR = os.getenv("PLAYERDATA_DIR")         # chemin vers world/playerdata
PLAYERDATA_MAPPING = os.getenv("PLAYERDATA_MAPPING") # fichier playerdata.txt du bot
BOT_PLAYERDATA_JSON = os.path.join(os.getcwd(), "playerdata")  # répertoire de sortie JSON


class Inventory(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mapping = self.load_mapping()
        os.makedirs(BOT_PLAYERDATA_JSON, exist_ok=True)

    def load_mapping(self):
        mapping = {}
        if not PLAYERDATA_MAPPING or not os.path.exists(PLAYERDATA_MAPPING):
            print(f"[MAPPING] ⚠️ Fichier playerdata.txt introuvable: {PLAYERDATA_MAPPING}")
            return mapping
        try:
            with open(PLAYERDATA_MAPPING, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split(";")
                    data = {}
                    for p in parts:
                        if "=" in p:
                            k, v = p.split("=", 1)
                            data[k.strip()] = v.strip()
                    if "Pseudo" in data and "UUID" in data:
                        mapping[data["Pseudo"]] = data["UUID"]
        except Exception as e:
            print(f"[MAPPING] ❌ Erreur lecture mapping: {e}")
        return mapping

    def read_and_convert_dat(self, uuid: str):
        """Lit le fichier .dat, le convertit en JSON, et retourne un dict structuré"""
        if not PLAYERDATA_DIR:
            return None

        path = os.path.join(PLAYERDATA_DIR, f"{uuid}.dat")
        if not os.path.exists(path):
            return None

        try:
            data = nbtlib.load(path)

            # Inventaire (inclut slots 0–35, 100–103)
            inventory = {}
            for item in data.get("Inventory", []):
                slot = item.get("Slot")
                if "id" in item and "Count" in item and slot is not None:
                    inventory[int(slot)] = {
                        "id": str(item["id"]),
                        "count": int(item["Count"])
                    }

            # Armure : lecture dans l'ordre (100 bottes → 103 casque)
            armor_slots = {
                100: "Bottes",
                101: "Jambières",
                102: "Plastron",
                103: "Casque"
            }
            armor = {}
            for slot_id, slot_name in armor_slots.items():
                if slot_id in inventory:
                    armor[slot_name] = f"{inventory[slot_id]['count']}x {inventory[slot_id]['id']}"
                else:
                    armor[slot_name] = None

            # Main secondaire
            offhand = []
            for item in data.get("HandItems", []):
                if "id" in item:
                    offhand.append(f"{int(item['Count'])}x {str(item['id'])}")

            structured_data = {
                "inventory": inventory,
                "armor": armor,
                "offhand": offhand
            }

            out_path = os.path.join(BOT_PLAYERDATA_JSON, f"{uuid}.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(structured_data, f, ensure_ascii=False, indent=4)

            return structured_data
        except Exception as e:
            print(f"[DAT] ❌ Erreur lecture .dat pour UUID {uuid}: {e}")
            return None

    def make_embed(self, player: str, uuid: str, data: dict, section: str) -> discord.Embed:
        """Crée un embed selon la section demandée"""
        embed = discord.Embed(
            title=f"🎒 Inventaire de {player}",
            description=f"UUID : `{uuid}`\n🔴 Joueur hors ligne",
            color=discord.Color.gold()
        )

        if section == "Hotbar":
            hotbar = [f"{data['inventory'][i]['count']}x {data['inventory'][i]['id']}" 
                      for i in range(0, 9) if i in data["inventory"]]
            embed.add_field(name="Hotbar", value="\n".join(hotbar) if hotbar else "(vide)", inline=False)

        elif section == "Inventaire":
            inv = [f"{data['inventory'][i]['count']}x {data['inventory'][i]['id']}" 
                   for i in range(9, 36) if i in data["inventory"]]
            embed.add_field(name="Inventaire", value="\n".join(inv) if inv else "(vide)", inline=False)

        elif section == "Armure":
            armor_list = [f"{piece}: {val}" for piece, val in data["armor"].items() if val]
            embed.add_field(name="Armure", value="\n".join(armor_list) if armor_list else "(vide)", inline=False)

        elif section == "Main secondaire":
            embed.add_field(name="Main secondaire", value="\n".join(data["offhand"]) if data["offhand"] else "(vide)", inline=False)

        elif section == "Full":
            hotbar = [f"{data['inventory'][i]['count']}x {data['inventory'][i]['id']}" 
                      for i in range(0, 9) if i in data["inventory"]]
            inv = [f"{data['inventory'][i]['count']}x {data['inventory'][i]['id']}" 
                   for i in range(9, 36) if i in data["inventory"]]
            armor_list = [f"{piece}: {val}" for piece, val in data["armor"].items() if val]

            embed.add_field(name="Hotbar", value="\n".join(hotbar) if hotbar else "(vide)", inline=False)
            embed.add_field(name="Inventaire", value="\n".join(inv) if inv else "(vide)", inline=False)
            embed.add_field(name="Armure", value="\n".join(armor_list) if armor_list else "(vide)", inline=False)
            embed.add_field(name="Main secondaire", value="\n".join(data["offhand"]) if data["offhand"] else "(vide)", inline=False)

        # Ajout footer date/heure
        now = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S UTC")
        embed.set_footer(text=f"Requête effectuée le {now}")


        return embed

    @app_commands.command(name="inventory", description="Voir l'inventaire d'un joueur (staff uniquement, même hors ligne)")
    @app_commands.describe(player="Pseudo du joueur")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def inventory(self, interaction: discord.Interaction, player: str):
        if not any(r.id == STAFF_ROLE_ID for r in interaction.user.roles):
            await interaction.response.send_message("❌ Tu n’as pas la permission.", ephemeral=True)
            return

        uuid = self.mapping.get(player)
        if not uuid:
            await interaction.response.send_message(f"❌ Impossible de trouver l’UUID du joueur.", ephemeral=True)
            return

        data = self.read_and_convert_dat(uuid)
        if not data:
            await interaction.response.send_message(f"❌ Impossible de lire le fichier .dat.", ephemeral=True)
            return

        # Embed initial (hotbar par défaut)
        embed = self.make_embed(player, uuid, data, "Hotbar")

        # Vue interactive
        class InventoryView(discord.ui.View):
            def __init__(self, cog: Inventory):
                super().__init__(timeout=120)
                self.cog = cog

            @discord.ui.button(label="Hotbar", style=discord.ButtonStyle.primary)
            async def hotbar(self, interaction_btn: discord.Interaction, button: discord.ui.Button):
                await interaction_btn.response.edit_message(embed=self.cog.make_embed(player, uuid, data, "Hotbar"), view=self)

            @discord.ui.button(label="Inventaire", style=discord.ButtonStyle.primary)
            async def inv(self, interaction_btn: discord.Interaction, button: discord.ui.Button):
                await interaction_btn.response.edit_message(embed=self.cog.make_embed(player, uuid, data, "Inventaire"), view=self)

            @discord.ui.button(label="Armure", style=discord.ButtonStyle.secondary)
            async def armor(self, interaction_btn: discord.Interaction, button: discord.ui.Button):
                await interaction_btn.response.edit_message(embed=self.cog.make_embed(player, uuid, data, "Armure"), view=self)

            @discord.ui.button(label="Main secondaire", style=discord.ButtonStyle.secondary)
            async def offhand(self, interaction_btn: discord.Interaction, button: discord.ui.Button):
                await interaction_btn.response.edit_message(embed=self.cog.make_embed(player, uuid, data, "Main secondaire"), view=self)

            @discord.ui.button(label="Full Inventaire", style=discord.ButtonStyle.success)
            async def full(self, interaction_btn: discord.Interaction, button: discord.ui.Button):
                await interaction_btn.response.edit_message(embed=self.cog.make_embed(player, uuid, data, "Full"), view=self)

        await interaction.response.send_message(embed=embed, view=InventoryView(self))


async def setup(bot: commands.Bot):
    await bot.add_cog(Inventory(bot))
