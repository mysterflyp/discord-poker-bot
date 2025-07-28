
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
            await ctx.send("🎲 **Roulette Russe** 🎲\n"
                          "Utilisez `$roulette <mise>` pour jouer !\n"
                          "• 1 balle sur 6 chambres\n"
                          "• Si vous survivez: gain x2\n"
                          "• Si vous tombez sur la balle: vous perdez votre mise\n"
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
        
        # Créer une nouvelle partie
        self.games[ctx.author.id] = {
            'mise': mise,
            'chambers': self._create_revolver(),
            'current_chamber': 0,
            'total_chambers': 6
        }
        
        # Débiter la mise
        self._db.user_add_balance(ctx.author.id, -mise)
        
        embed = discord.Embed(
            title="🎲 Roulette Russe",
            description=f"**{ctx.author.name}** a misé **{mise} jetons** !\n\n"
                       f"🔫 Revolver chargé avec 1 balle sur 6 chambres\n"
                       f"💰 Gain potentiel: **{mise * 2} jetons**\n\n"
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
        mise = game['mise']
        
        # Vérifier la chambre actuelle
        is_bullet = chambers[current_chamber]
        
        if is_bullet:
            # BANG ! Le joueur perd
            embed = discord.Embed(
                title="💀 BANG !",
                description=f"**{ctx.author.name}** est tombé sur la balle !\n\n"
                           f"💸 Vous avez perdu **{mise} jetons**\n"
                           f"🪦 Chambre fatale: {current_chamber + 1}/6",
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
                gain = mise * 2
                self._db.user_add_balance(ctx.author.id, gain)
                
                embed = discord.Embed(
                    title="🎉 VICTOIRE !",
                    description=f"**{ctx.author.name}** a survécu aux 6 chambres !\n\n"
                               f"💰 Vous gagnez **{gain} jetons** !\n"
                               f"🏆 Vous êtes un vrai survivant !",
                    color=discord.Color.gold()
                )
                embed.set_footer(text="🍀 Incroyable chance !")
                
                # Supprimer la partie
                del self.games[ctx.author.id]
                
            else:
                # Le joueur peut continuer
                remaining = 6 - game['current_chamber']
                embed = discord.Embed(
                    title="😅 Click !",
                    description=f"**{ctx.author.name}** a survécu à la chambre {current_chamber + 1} !\n\n"
                               f"🔫 Chambres restantes: **{remaining}**\n"
                               f"💰 Gain potentiel: **{mise * 2} jetons**\n\n"
                               f"Tapez `$tirer` pour continuer ou `$fuir` pour récupérer votre mise",
                    color=discord.Color.orange()
                )
                embed.set_footer(text="🤔 Voulez-vous tenter votre chance ?")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="fuir")
    async def fuir(self, ctx):
        """Abandonner la partie de roulette russe."""
        
        if ctx.author.id not in self.games:
            await ctx.send("🏃 Vous n'avez pas de partie en cours à abandonner !")
            return
        
        game = self.games[ctx.author.id]
        mise = game['mise']
        current_chamber = game['current_chamber']
        
        # Rendre la mise au joueur
        self._db.user_add_balance(ctx.author.id, mise)
        
        embed = discord.Embed(
            title="🏃 Fuite !",
            description=f"**{ctx.author.name}** a fui le combat !\n\n"
                       f"💰 Mise récupérée: **{mise} jetons**\n"
                       f"🔫 Vous aviez survécu à {current_chamber} chambre(s)",
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
