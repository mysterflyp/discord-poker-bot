import os
import discord
from discord.ext import commands, tasks

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

@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

my_secret = os.environ['TOKEN_BOT']
bot.run(my_secret)
