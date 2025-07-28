import discord
from discord.ext import commands, tasks
from db_manager import DBManager

# Constantes
MONEY_INTERVAL = 10  # secondes
LEVEL_INTERVAL = 10
MESSAGE_MONEY = 0.2
MESSAGE_LEVEL = 0.01

ROLE_ID = 1279001249022476342  # Role vocal
ROLE_ID2 = 1271165198392365207  # Role global

class EconomyManager(commands.Cog):
    """Cog pour les gains automatiques d'argent et d'expérience."""

    def __init__(self, bot):
        self.bot = bot
        self._db: DBManager | None = None

    async def cog_load(self):
        """Chargement du cog."""
        self._db = self.bot.get_cog("DBManager")
        if not self._db:
            raise RuntimeError("❌ DBManager doit être chargé avant EconomyManager")

        self.give_money_periodically.start()
        self.give_level_periodically.start()

    def is_in_vocal_with_role(self, member: discord.Member) -> bool:
        """Vérifie si le membre est en vocal ET possède le rôle requis."""
        return member.voice and any(role.id == ROLE_ID for role in member.roles)

    @tasks.loop(seconds=MONEY_INTERVAL)
    async def give_money_periodically(self):
        for guild in self.bot.guilds:
            for member in guild.members:
                if member.bot:
                    continue
                if self.is_in_vocal_with_role(member) and self._db:
                    if self._db.user_get_niveau(member.id) is None:
                        self._db.user_create(member.id)
                    self._db.user_add_balance(member.id, 3)
                    print(f"💰 {member.display_name} a reçu 25 jetons (vocal).")

    @tasks.loop(seconds=LEVEL_INTERVAL)
    async def give_level_periodically(self):
        for guild in self.bot.guilds:
            for member in guild.members:
                if member.bot:
                    continue
                if self.is_in_vocal_with_role(member) and self._db:
                    if self._db.user_get_niveau(member.id) is None:
                        self._db.user_create(member.id)
                    self._db.user_add_niveau(member.id, 0.1)
                    print(f"📈 {member.display_name} a reçu 0.1 XP (vocal).")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not self._db:
            return
        
        # Ne pas donner d'argent/XP pour les commandes du bot
        if message.content.startswith('$'):
            return
            
        user_id = message.author.id
        if self._db.user_get_niveau(user_id) is None:
            self._db.user_create(user_id)
        self._db.user_add_balance(user_id, MESSAGE_MONEY)
        self._db.user_add_niveau(user_id, MESSAGE_LEVEL)
        print(f"✉️ {message.author.name} a gagné {MESSAGE_MONEY} jetons et {MESSAGE_LEVEL} XP via message.")

async def setup(bot):
    await bot.add_cog(EconomyManager(bot))
