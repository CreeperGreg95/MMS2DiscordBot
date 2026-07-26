# commands.py
from commands.ping import *
from commands.status import *
from commands.say import *
from commands.tps import *
from commands.players import *
from commands.broadcast import *


# Admin Commands ONLY
from commands.inventory import *
from commands.server import *
#


async def load_all_cogs(bot):
    # Appelle setup de chaque Cog
    await setup(bot)  # Chaque setup est importé depuis les fichiers de commandes
