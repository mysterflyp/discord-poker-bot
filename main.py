import os
import discord
import asyncio
from discord.ext import commands, tasks

# Récuperation du token du bot depuis les variables d'environement
TOKEN_BOT = os.environ['TOKEN_BOT']

# Définir les intentions du bot
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.members = True

bot = commands.Bot(command_prefix="$", intents=intents)
client = discord.Client(intents=discord.Intents.all())

@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")

# Chargement des extensions (Cog), approche asynchrone
async def load_extensions():
    await bot.load_extension("bot_commands")  # Charge bot_commands.py

async def main():
    async with bot:
        await load_extensions()
        await bot.start(TOKEN_BOT)

# Démarrage du bot en async
asyncio.run(main())
