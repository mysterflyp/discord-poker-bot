
import discord
import random
from discord.ext import commands
from db_manager import DBManager

class RouletteRusse(commands.Cog):
    """Jeu de roulette russe avec système de mise."""
    
    def __init__(self, bot):
        self.bot = bot
        self._db: DBManager | None = None
        self.games = {}  # Stocke les parties en cours par utilisateur
    
    async def cog_load(self):
        """Chargement du cog."""
        self._db = self.bot.get_cog("DBManager")
        if not self._db:
            raise RuntimeError("❌ DBManager doit être chargé avant RouletteRusse")
    
    @commands.command(name="roulette")
    async def roulette_russe(self, ctx, mise: int = None):
        """Commande pour jouer à la roulette russe."""
        
        if mise is None:
            await ctx.send("🎲 **Roulette Russe Progressive** 🎲\n"
                          "Utilisez `$roulette <mise>` pour jouer !\n"
                          "• 1 balle sur 6 chambres\n"
                          "• **Mise unique**: votre mise est prélevée une seule fois au début\n"
                          "• Si vous survivez aux 6 balles: gain = mise × 12\n"
                          "• Si vous tombez sur la balle: vous perdez tout\n"
                          "• Vous pouvez fuir pour récupérer votre mise de base\n"
                          "• Mise minimum: 1 jeton")
            return
        
        if ctx.author.id in self.games:
            await ctx.send("🔫 Vous avez déjà une partie en cours ! Terminez-la d'abord.")
            return
        
        if mise <= 0:
            await ctx.send("⚠️ La mise doit être supérieure à 0 !")
            return
        
        # Vérifier l'existence du joueur et son solde
        self._db.user_ensure_exist(ctx.author)
        balance = self._db.user_get_balance(ctx.author.id)
        
        if balance < mise:
            await ctx.send(f"💰 Solde insuffisant ! Vous avez {balance} jetons, mais vous voulez miser {mise} jetons.")
            return
        
        # Débiter la mise de base une seule fois
        self._db.user_add_balance(ctx.author.id, -mise)
        
        # Créer une nouvelle partie
        self.games[ctx.author.id] = {
            'mise': mise,
            'chambers': self._create_revolver(),
            'current_chamber': 0,
            'total_chambers': 6
        }
        
        # Calculer le gain potentiel (mise × 6 chambres × 2)
        total_mises = mise * 6
        gain_potentiel = total_mises * 2
        
        gain_potentiel = total_mises * 2
        
        embed = discord.Embed(
            title="🎲 Roulette Russe",
            description=f"**{ctx.author.name}** a misé **{mise} jetons** !\n\n"
                       f"🔫 Revolver chargé avec 1 balle sur 6 chambres\n"
                       f"💰 Mise unique de **{mise} jetons** (déjà prélevée)\n"
                       f"🏆 Gain potentiel: **{gain_potentiel} jetons**\n\n"
                       f"Tapez `$tirer` pour tirer ou `$fuir` pour abandonner",
            color=discord.Color.red()
        )
        embed.set_footer(text="⚠️ Attention: une balle peut être fatale !")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="tirer")
    async def tirer(self, ctx):
        """Tirer une balle dans la roulette russe."""
        
        if ctx.author.id not in self.games:
            await ctx.send("🎯 Vous n'avez pas de partie en cours ! Utilisez `$roulette <mise>` pour commencer.")
            return
        
        game = self.games[ctx.author.id]
        current_chamber = game['current_chamber']
        chambers = game['chambers']
        mise_base = game['mise']
        
        # Pas de débit supplémentaire - la mise de base a déjà été prélevée
        
        # Vérifier la chambre actuelle
        is_bullet = chambers[current_chamber]
        
        if is_bullet:
            # BANG ! Le joueur perd
            
            embed = discord.Embed(
                title="💀 BANG !",
                description=f"**{ctx.author.name}** est tombé sur la balle !\n\n"
                           f"💸 Mise perdue: **{mise_base} jetons**\n"
                           f"🪦 Chambre fatale: {current_chamber + 1}/6\n"
                           f"🎯 Vous aviez survécu à {current_chamber} balle(s)",
                color=discord.Color.dark_red()
            )
            embed.set_footer(text="☠️ La chance n'était pas de votre côté...")
            
            # Supprimer la partie
            del self.games[ctx.author.id]
            
        else:
            # Click ! Le joueur survit
            game['current_chamber'] += 1
            
            if game['current_chamber'] >= 6:
                # Le joueur a survécu à toutes les chambres !
                # Gain = mise de base × 12 (6 chambres × 2)
                gain = mise_base * 12
                self._db.user_add_balance(ctx.author.id, gain)
                
                embed = discord.Embed(
                    title="🎉 VICTOIRE !",
                    description=f"**{ctx.author.name}** a survécu aux 6 chambres !\n\n"
                               f"💰 Mise payée: **{mise_base} jetons**\n"
                               f"💰 Vous gagnez: **{gain} jetons** !\n"
                               f"🏆 Profit net: **{gain - mise_base} jetons**\n"
                               f"🏆 Vous êtes un vrai survivant !",
                    color=discord.Color.gold()
                )
                embed.set_footer(text="🍀 Incroyable chance !")
                
                # Supprimer la partie
                del self.games[ctx.author.id]
                
            else:
                # Le joueur peut continuer
                remaining = 6 - game['current_chamber']
                gain_potentiel = mise_base * 12  # 6 chambres × 2
                
                embed = discord.Embed(
                    title="😅 Click !",
                    description=f"**{ctx.author.name}** a survécu à la balle {current_chamber + 1} !\n\n"
                               f"🔫 Chambres restantes: **{remaining}**\n"
                               f"💰 Mise en jeu: **{mise_base} jetons**\n"
                               f"🏆 Gain potentiel: **{gain_potentiel} jetons**\n\n"
                               f"Tapez `$tirer` pour continuer ou `$fuir` pour abandonner",
                    color=discord.Color.orange()
                )
                embed.set_footer(text="💡 Plus vous allez loin, plus ça rapporte !")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="fuir")
    async def fuir(self, ctx):
        """Abandonner la partie de roulette russe."""
        
        if ctx.author.id not in self.games:
            await ctx.send("🏃 Vous n'avez pas de partie en cours à abandonner !")
            return
        
        game = self.games[ctx.author.id]
        mise_base = game['mise']
        current_chamber = game['current_chamber']
        
        # Le joueur abandonne et perd sa mise de base
        
        embed = discord.Embed(
            title="🏃 Fuite !",
            description=f"**{ctx.author.name}** a abandonné la partie !\n\n"
                       f"💸 Mise perdue: **{mise_base} jetons**\n"
                       f"🔫 Vous aviez survécu à {current_chamber} balle(s)\n"
                       f"🛡️ Parfois, il vaut mieux partir tant qu'on est en vie !",
            color=discord.Color.blue()
        )
        embed.set_footer(text="🛡️ Parfois, fuir est la meilleure option...")
        
        # Supprimer la partie
        del self.games[ctx.author.id]
        
        await ctx.send(embed=embed)
    
    @commands.command(name="roulette_stats")
    async def roulette_stats(self, ctx, membre: discord.Member = None):
        """Affiche les statistiques de roulette russe."""
        
        if membre is None:
            membre = ctx.author
        
        # Pour l'instant, on affiche juste le solde
        # On pourrait ajouter des stats spécifiques plus tard
        self._db.user_ensure_exist(membre)
        balance = self._db.user_get_balance(membre.id)
        
        embed = discord.Embed(
            title="📊 Statistiques Roulette Russe",
            description=f"**{membre.display_name}**\n\n"
                       f"💰 Solde actuel: **{balance} jetons**",
            color=discord.Color.blue()
        )
        
        if ctx.author.id in self.games:
            game = self.games[ctx.author.id]
            embed.add_field(
                name="🎲 Partie en cours",
                value=f"Mise: {game['mise']} jetons\n"
                     f"Chambre: {game['current_chamber'] + 1}/6",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    def _create_revolver(self):
        """Crée un revolver avec une balle placée aléatoirement."""
        chambers = [False] * 6  # 6 chambres vides
        bullet_position = random.randint(0, 5)  # Position aléatoire pour la balle
        chambers[bullet_position] = True  # Placer la balle
        return chambers

async def setup(bot):
    await bot.add_cog(RouletteRusse(bot))
