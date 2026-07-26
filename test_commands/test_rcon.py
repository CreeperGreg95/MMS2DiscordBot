import os
from mcrcon import MCRcon
from dotenv import load_dotenv

# Charger les variables depuis .env
load_dotenv()

RCON_HOST = os.getenv("RCON_HOST", "localhost")
RCON_PORT = int(os.getenv("RCON_PORT", 25575))
RCON_PASSWORD = os.getenv("RCON_PASSWORD")

with MCRcon(RCON_HOST, RCON_PASSWORD, port=RCON_PORT) as mcr:
    print(mcr.command("list"))
