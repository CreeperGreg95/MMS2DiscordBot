# -*- coding: utf-8 -*-
import os
import re
import time
import asyncio
import discord
from discord.ext import tasks, commands
from mcrcon import MCRcon
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo
from mcstatus import JavaServer

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", 0))
PING_ROLE_ID = os.getenv("PING_ROLE_ID")

RCON_HOST = os.getenv("RCON_HOST", "localhost")
RCON_PORT = int(os.getenv("RCON_PORT", 25575))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")

RCON_HOST_PLAYER = os.getenv("RCON_HOST") or RCON_HOST
MC_SERVER_PORT = int(os.getenv("MC_SERVER_PORT", 25565))
MC_LOG_PATH = os.getenv("MC_LOG_PATH")
GUILD_ID = 1033271218247319562

# === INTENTS ===
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

last_status = None
recent_events = {}
recent_actions = {}
recent_banned_players = set()
DUP_WINDOW = 3
SUPPRESS_DISCONNECT_WINDOW = 4
DATA_FILE = "data.txt"

# --- Chargement des infos joueurs pour notifications personnalisées ---
def load_playerdata(file_path="playerdata.txt"):
    """Retourne un dict {pseudo: {"uuid": ..., "discord_id": ...}}"""
    players = {}
    if not os.path.exists(file_path):
        return players
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(";")
            data = {}
            pseudo = None
            for part in parts:
                if "=" in part:
                    k, v = part.split("=", 1)
                    if k == "Pseudo":
                        pseudo = v
                    elif k == "UUID":
                        data["uuid"] = v
                    elif k == "DiscordID":
                        data["discord_id"] = int(v)
            if pseudo:
                players[pseudo] = data
    return players

# === UTILITAIRES ===
def now_ts():
    return time.time()

def event_key(event_type, player):
    return f"{event_type}:{player}"

def is_duplicate(event_type, player, window=DUP_WINDOW):
    key = event_key(event_type, player)
    t = now_ts()
    for k in list(recent_events.keys()):
        if t - recent_events[k] > window:
            del recent_events[k]
    if key in recent_events:
        return True
    recent_events[key] = t
    return False

def set_recent_action(player, action):
    recent_actions[player] = (action, now_ts())

def recent_action_is(player, actions, window=SUPPRESS_DISCONNECT_WINDOW):
    v = recent_actions.get(player)
    if not v:
        return False
    action, ts = v
    if isinstance(actions, (list, tuple, set)):
        return action in actions and (now_ts() - ts <= window)
    else:
        return action == actions and (now_ts() - ts <= window)

def read_status_file():
    if not os.path.exists(DATA_FILE):
        print(f"[DATA] ⚠️ {DATA_FILE} inexistant → OFF")
        return "OFF"
    try:
        with open(DATA_FILE, "r") as f:
            for line in f:
                if line.startswith("Server_Status="):
                    val = line.split("=")[1].strip()
                    print(f"[DATA] 📖 Lecture {DATA_FILE} = {val}")
                    return val
    except Exception as e:
        print(f"[DATA] ❌ Erreur lecture {DATA_FILE}: {e}")
    return "OFF"

def write_status_file(status: str):
    try:
        with open(DATA_FILE, "w") as f:
            f.write(f"Server_Status={status}\n")
        print(f"[DATA] ✅ Server_Status={status} écrit dans {DATA_FILE}")
    except Exception as e:
        print(f"[DATA] ❌ Erreur écriture {DATA_FILE}: {e}")

def query_server_status():
    try:
        server = JavaServer.lookup(f"{RCON_HOST_PLAYER}:{MC_SERVER_PORT}")
        status = server.status()
        print(f"[DEBUG] mcstatus: {status.players.online} joueurs connectés")
        write_status_file("ON")
        return "online"
    except Exception as e:
        print(f"[ERREUR] mcstatus KO: {e}")

    try:
        with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
            response = mcr.command("list")
            print(f"[DEBUG] Réponse RCON: {response}")
            if response and ("There are" in response or "players online" in response):
                write_status_file("ON")
                return "online"
    except Exception as e:
        print(f"[ERREUR] RCON KO: {e}")

    file_status = read_status_file()
    if file_status == "ON":
        print("[INFO] RCON/mcstatus KO mais fichier=ON → on garde serveur online")
        return "online"

    write_status_file("OFF")
    return "offline"

def extract_player_from_text(text):
    m = re.search(r"name=([A-Za-z0-9_]{2,16})\b", text)
    if m:
        p = m.group(1)
        if p.lower() in ("disconnected", "left", "joined"):
            return None
        if p.isdigit():
            return None
        return p
    m = re.search(r"\]:\s+([A-Za-z0-9_]{2,16})\s+(?:joined the game|left the game|lost connection|logged in with entity id)", text, re.IGNORECASE)
    if m:
        p = m.group(1)
        if p.isdigit():
            return None
        return p
    m = re.search(r"\b(?:Banned|Kicked)\s+([A-Za-z0-9_]{2,16})\b", text)
    if m:
        p = m.group(1)
        if p.isdigit():
            return None
        return p
    return None

def make_embed(title, desc, color):
    paris_time = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%d %H:%M:%S")
    e = discord.Embed(title=title, description=desc, color=color)
    e.set_footer(text=paris_time)
    return e

# === STATUS UPDATER ===
@tasks.loop(seconds=5)
async def status_updater():
    global last_status
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        return
    status = query_server_status()
    if status != last_status:
        last_status = status
        color = discord.Color.green() if status == "online" else discord.Color.red()
        paris_time = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%d %H:%M:%S")
        embed = discord.Embed(
            title="Statut du serveur Minecraft Moddé",
            description="✅ Serveur en ligne" if status == "online" else "❌ Serveur hors ligne",
            color=color
        )
        embed.set_footer(text=paris_time)
        try:
            if status == "online" and PING_ROLE_ID:
                await channel.send(content=f"<@&{PING_ROLE_ID}>", embed=embed)
            else:
                await channel.send(embed=embed)
        except Exception as e:
            print(f"[ERREUR] envoi Discord: {e}")

# === LOG PROCESSING ===
async def tail_log(path, channel):
    current_block = []
    f = open(path, "r", encoding="utf-8", errors="ignore")
    f.seek(0, os.SEEK_END)
    inode = os.fstat(f.fileno()).st_ino
    while True:
        line = f.readline()
        if not line:
            await asyncio.sleep(0.25)
            try:
                new_inode = os.stat(path).st_ino
                if new_inode != inode:
                    print("[LOG] 📂 Nouveau latest.log détecté → réouverture")
                    f.close()
                    f = open(path, "r", encoding="utf-8", errors="ignore")
                    inode = new_inode
            except FileNotFoundError:
                pass
            continue
        line = line.rstrip("\n")
        if line.startswith("["):
            if current_block:
                await process_log_block(current_block, channel)
            current_block = [line]
        else:
            if current_block:
                current_block.append(line)
            else:
                await process_log_block([line], channel)

async def process_log_block(lines, channel):
    full_text = " ".join(line.strip() for line in lines if line and line.strip())
    player = extract_player_from_text(full_text)
    playerdata = load_playerdata()

    # --- BAN ---
    m_ban = re.search(r"\bBanned\s+([A-Za-z0-9_]{2,16})(?:[:\s]+(.*))?$", full_text)
    if m_ban:
        p = m_ban.group(1)
        reason = m_ban.group(2).strip() if m_ban.group(2) else None
        if not is_duplicate("ban", p):
            recent_banned_players.add(p)
            set_recent_action(p, "ban")
            desc = f"⛔ **{p}** a été banni du serveur."
            if reason:
                desc += f"\n> Raison : {reason}"
            await channel.send(embed=make_embed("⛔ Banni", desc, discord.Color.red()))
        return

    # --- KICK ---
    m_kick = re.search(r"\bKicked\s+([A-Za-z0-9_]{2,16})(?:[:\s]+(.*))?$", full_text)
    if m_kick:
        p = m_kick.group(1)
        reason = m_kick.group(2).strip() if m_kick.group(2) else None
        if reason and reason.lower() in ("disconnected", "timed out"):
            return
        if not is_duplicate("kick", p):
            set_recent_action(p, "kick")
            desc = f"👢 **{p}** a été expulsé(e)."
            if reason:
                desc += f"\n> Raison : {reason}"
            await channel.send(embed=make_embed("👢 Expulsion", desc, discord.Color.orange()))
        return

    # --- BANNED ATTEMPT ---
    if "You are banned from this server" in full_text:
        p = player
        if p and not is_duplicate("ban_attempt", p):
            await channel.send(embed=make_embed("🚫 Tentative bannie", f"🚫 **{p}** a tenté de se connecter mais est banni.", discord.Color.red()))
        return

    # --- LOST CONNECTION ---
    m_lost = re.search(r"\]:\s+([A-Za-z0-9_]{2,16})\s+lost connection: (.+)", full_text, re.IGNORECASE)
    if m_lost:
        p = m_lost.group(1)
        reason = m_lost.group(2).strip()
        if reason.lower() in ("disconnected", "timed out"):
            return
        if p and not is_duplicate("kick", p):
            set_recent_action(p, "kick")
            desc = f"👢 **{p}** a été expulsé(e)."
            if reason:
                desc += f"\n> Raison : {reason}"
            await channel.send(embed=make_embed("👢 Expulsion", desc, discord.Color.orange()))
        return

    # --- JOIN ---
    if re.search(r"joined the game", full_text, re.IGNORECASE):
        if player and not is_duplicate("join", player):
            mention = f"<@{playerdata[player]['discord_id']}>" if player in playerdata else f"**{player}**"
            embed = make_embed("📥 Connexion", f"▶️ {mention} s'est connecté(e).", discord.Color.green())
            await channel.send(content=mention if mention.startswith("<@") else None, embed=embed)
        return

    # --- LEFT ---
    if re.search(r"(left the game|lost connection)", full_text, re.IGNORECASE):
        if player and not is_duplicate("disconnect", player):
            mention = f"<@{playerdata[player]['discord_id']}>" if player in playerdata else f"**{player}**"
            embed = make_embed("📤 Déconnexion", f"⏹️ {mention} s'est déconnecté(e).", discord.Color.dark_grey())
            await channel.send(content=mention if mention.startswith("<@") else None, embed=embed)
        return

    # --- UNBAN ---
    m_unban = re.search(r"\bUnbanned\s+([A-Za-z0-9_]{2,16})\b", full_text)
    if m_unban:
        p = m_unban.group(1)
        if not is_duplicate("unban", p):
            await channel.send(embed=make_embed("✅ Débanni", f"✅ **{p}** a été débanni.", discord.Color.green()))
        return

    # --- WHITELIST ---
    if "Whitelist is now turned on" in full_text:
        await channel.send(embed=make_embed("🔐 Whitelist", "🔐 La whitelist est activée.", discord.Color.blue()))
        return
    if "Whitelist is now turned off" in full_text:
        await channel.send(embed=make_embed("🔓 Whitelist", "🔓 La whitelist est désactivée.", discord.Color.orange()))
        return

    # --- SERVER STOP ---
    if "Stopping server" in full_text:
        write_status_file("OFF")
        await channel.send(embed=make_embed("⛔ Serveur arrêté", "Le serveur vient de s'éteindre.", discord.Color.red()))
        await asyncio.sleep(5)
        await channel.send(embed=make_embed("❌ Serveur hors ligne", "Le serveur est maintenant hors ligne.", discord.Color.red()))
        return

    # --- SERVER START ---
    if "ModLauncher running:" in full_text:
        await channel.send(embed=make_embed("🟠 Démarrage", "Le serveur est en train de démarrer...", discord.Color.orange()))
        return

    # --- SERVER READY ---
    if "Done (" in full_text and ")! For help, type" in full_text:
        write_status_file("ON")
        await channel.send(embed=make_embed("✅ Serveur en ligne", "Le serveur est maintenant opérationnel.", discord.Color.green()))
        return

# === COG LOADER ===
async def load_cogs():
    for filename in os.listdir("./commands"):
        if filename.endswith(".py") and filename != "__init__.py":
            cog_name = f"commands.{filename[:-3]}"
            try:
                await bot.load_extension(cog_name)
                print(f"📦 Cog '{cog_name}' chargé avec succès")
            except Exception as e:
                print(f"❌ Erreur chargement '{cog_name}': {e}")

# === ON READY ===
@bot.event
async def on_ready():
    print(f"✅ Connecté en tant que {bot.user}")
    await load_cogs()
    guild = discord.Object(id=GUILD_ID)
    try:
        synced = await bot.tree.sync(guild=guild)
        print(f"🌐 {len(synced)} commandes synchronisées pour la guilde {GUILD_ID}")
    except Exception as e:
        print(f"❌ Erreur lors de la synchronisation des commandes : {e}")

    status_updater.start()
    print("⏳ status_updater démarré")

    if MC_LOG_PATH and CHANNEL_ID:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            asyncio.create_task(tail_log(MC_LOG_PATH, channel))
            print(f"📜 Surveillance du log Minecraft activée sur le channel {CHANNEL_ID}")

bot.run(DISCORD_TOKEN)
