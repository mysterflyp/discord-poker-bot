import discord
from discord.ext import commands, tasks

# Importer le Cog DBManager pour gérer les requêtes SQL
from db_manager import DBManager

# ✅ Constantes pour régler la périodicité et les gains
MONEY_INTERVAL = 10  # Temps en secondes entre chaque gain automatique
LEVEL_INTERVAL = 10  # Temps en secondes entre chaque gain automatique
MESSAGE_MONEY = 5  # Argent gagné par message
MESSAGE_LEVEL = 0.25  # Expérience gagnée par message

# Constantes de rôle
ROLE_ID = 1279001249022476342  # Role en vocal
ROLE_ID2 = 1271165198392365207  # Role global


class EconomyManager(commands.Cog):
    """Cog pour gérer les gains automatiques d'argent et d'expérience."""

    def __init__(self, bot):
        self.bot = bot
        self._db: DBManager | None = None

    async def cog_load(self):
        """Méthode appelée automatiquement lors du chargement du Cog."""
        self._db = self.bot.get_cog("DBManager")
        if self._db is None:
            raise RuntimeError("❌ Erreur : DBManager n'a pas été chargé avant EconomyManager !")

    # ✅ Lancer un envoi périodique d'argent
    @tasks.loop(seconds=MONEY_INTERVAL)
    async def give_money_periodically(self):
        for guild in self.bot.guilds:
            for member in guild.members:
                role = discord.utils.get(member.roles, id=ROLE_ID)
                if role:
                    if self._db.get_niveau(member.id) is not None:  # Vérifie l'existence de l'user
                        self._db.add_balance(member.id, 25)
                        print(f"{member.name} a gagné 25 jetons.")

    # ✅ Lancer un envoi périodique de niveaux
    @tasks.loop(seconds=LEVEL_INTERVAL)
    async def give_level_periodically(self):
        for guild in self.bot.guilds:
            for member in guild.members:
                role = discord.utils.get(member.roles, id=ROLE_ID)
                if role:
                    if self._db.get_niveau(member.id) is not None:  # Vérifie l'existence de l'user
                        self._db.add_niveau(member.id, 0.25)
                        print(f"{member.name} a gagné 0.25 XP.")

    # ✅ Commande pour DÉMARRER les gains automatiques
    @commands.command()
    async def start_economy(self, ctx):
        """Démarre les tâches de gains automatiques."""
        if not self.give_money_periodically.is_running():
            self.give_money_periodically.start()
        if not self.give_level_periodically.is_running():
            self.give_level_periodically.start()
        await ctx.send("🚀 Les gains automatiques ont été activés !")

    # ✅ Commande pour STOPPER les gains automatiques
    @commands.command()
    async def stop_economy(self, ctx):
        """Stoppe les tâches de gains automatiques."""
        if self.give_money_periodically.is_running():
            self.give_money_periodically.cancel()
        if self.give_level_periodically.is_running():
            self.give_level_periodically.cancel()
        await ctx.send("⏸️ Les gains automatiques ont été stoppés.")

    # ✅ Ajouter des gains via l'envoi de messages
    @commands.Cog.listener()
    async def on_message(self, message):
        """Ajoute des jetons et de l'expérience lorsque les utilisateurs envoient des messages."""
        if message.author.bot:  # Ignorer les bots
            return

        user_id = message.author.id
        if self._db.get_niveau(user_id) is not None:  # Vérifie l'existence de l'user
            self._db.add_balance(user_id, MESSAGE_MONEY)
            self._db.add_niveau(user_id, MESSAGE_LEVEL)
            print(f"{message.author.name} a gagné {MESSAGE_MONEY} jetons et {MESSAGE_LEVEL} XP.")

async def setup(bot):
    """Ajoute le Cog au bot."""
    await bot.add_cog(EconomyManager(bot))
