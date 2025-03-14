import discord
from discord.ext import commands

class BotCommands(commands.Cog):
    """Groupe de commandes pour le bot."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx):
        """Répond avec 'Pong!'."""
        await ctx.send("Pong!")

    @commands.command()
    async def hello(self, ctx):
        """Répond avec un message de bienvenue."""
        await ctx.send(f"Salut {ctx.author.mention} ! 😊")

# Fonction pour ajouter les commandes au bot
async def setup(bot):
    await bot.add_cog(BotCommands(bot))
