import discord
import sqlite3
from discord.ext import commands
from db_manager import DBManager
from poker_game import GameStatus, FakeMember, PlayerView
from views.test_view import TestView




class BotCommands(commands.Cog):
    """Groupe de commandes pour le bot."""

    def __init__(self, bot):
        self.bot = bot
        self._db: DBManager | None = None

    async def cog_load(self):
        """Méthode appelée automatiquement lors du chargement du Cog."""
        self._db = self.bot.get_cog("DBManager")
        if self._db is None:
            raise RuntimeError(
                "❌ Erreur : DBManager n'a pas été chargé avant BotCommands !")

    @commands.command(name="solde")
    async def solde(self, ctx, member: discord.Member = None):
        """Affiche le solde du joueur."""

        if member is None:
            member = ctx.author

        # FIXME A VOIR....
        self._db.user_ensure_exist(member)
        balance = self._db.user_get_balance(member.id)
        if balance is None:
            await ctx.send(f"⚠️ Pas encore de compte ?")
            return

        # FIXME gerer "member nommé" vs "current ctx.member"
        await ctx.send(f"💰 Ton solde est de {balance} jetons.")

    @commands.command(name="niveau")
    async def niveau(self, ctx, membre: discord.Member = None):
        """Affiche le niveau du joueur."""

        if membre is None:
            membre = ctx.author

        # FIXME A VOIR....
        # self._db.user_ensure_exist(membre)
        niveau = self._db.user_get_niveau(membre.id)
        if niveau is None:
            await ctx.send(f"⚠️ Pas encore de compte ?")
            return

        # FIXME gerer "member nommé" vs "current ctx.member"
        await ctx.send(f"{membre.mention} a {niveau} % d'expérience.")

    # Commande pour payer une personne
    # FIXME : Il faut verifier que les users existent sinon les get/add_balance vont crasher
    @commands.command(name="donner")
    async def donner(self, ctx, target_member: discord.Member, amount: int):
        author_balance = self._db.get_balance(ctx.author.id)
        if author_balance < amount:
            await ctx.send(
                f"{ctx.author.mention}, votre solde est de {author_balance} jetons, vous n'avez pas assez pour donner {amount} jetons."
            )
            return
        # Soustraire à l'author
        new_author_balance = self._db.user_add_balance(ctx.author.id, -amount)

        # Ajouter au target
        new_target_balance = self._db.user_add_balance(target_member.id,
                                                       amount)
        await ctx.send(
            f"{ctx.author.mention} a donné {amount} jetons à {target_member.mention}. Nouveaux soldes : {ctx.author.mention}={new_author_balance} jetons, {target_member.mention}={new_target_balance} jetons"
        )

    # Gestion des erreurs pour les commandes nécessitant des permissions administratives
    @donner.error
    async def donner_error(ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(
                "Vous n'avez pas la permission d'utiliser cette commande.")

    # Commande pour donner de l'argent à un autre utilisateur (réservée aux admins)
    # FIXME : Il faut verifier que les users existent sinon les get/add_balance vont crasher
    @commands.command(name="crediter")
    @commands.has_permissions(administrator=True)
    async def crediter(self, ctx, target_member: discord.Member, amount: int):
        old_balance = self._db.user_get_balance(target_member.id)
        new_balance = self._db.user_add_balance(target_member.id, amount)

        await ctx.send(
            f"{target_member.mention} a reçu {amount} jetons ! Ancien solde : {old_balance} jetons, Nouveau solde: {new_balance} jetons."
        )

        # Gestion des erreurs pour la commande de remise à zéro level

    # FIXME : Dans le else utiliser error.toStr....
    @crediter.error
    async def crediter_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(
                "Tu n'as pas la permission d'utiliser cette commande.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                "Tu dois spécifier un membre pour lui assigner du credit.")
        else:
            await ctx.send(f"Une erreur est survenue. {error}")

    # Commande pour remettre à zéro l'expérience (niveau) d'un utilisateur
    # FIXME : il faut differencier le fait que le user n'existe pas du niveau 0
    @commands.command(name="reset_niveau")
    @commands.has_permissions(administrator=True)
    async def reset_niveau(self, ctx, member: discord.Member):
        new_niveau = self._db.user_reset_niveau(member.id)
        if new_niveau == 0:
            await ctx.send(
                f"L'expérience de {member.mention} a été remise à zéro.")
        else:
            await ctx.send(
                f"{member.mention} n'a pas d'expérience enregistrée.")

    # Gestion des erreurs pour la commande de remise à zéro level
    # FIXME : Dans le else utiliser error.toStr....
    @reset_niveau.error
    async def reset_niveau_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(
                "Tu n'as pas la permission d'utiliser cette commande.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                "Tu dois spécifier un membre pour réinitialiser son expérience."
            )
        else:
            await ctx.send("Une erreur est survenue.")

    # Commande pour remettre à zéro l'argent d'un utilisateur
    # FIXME : il faut differencier le fait que le user n'existe pas du montant 0
    @commands.command(name="reset_balance")
    @commands.has_permissions(administrator=True)
    async def reset_balance(self, ctx, member: discord.Member):
        new_balance = self._db.user_reset_balance(member.id)
        if new_balance == 0:
            await ctx.send(f"Le solde de {member.mention} a été remis à zéro.")
        else:
            await ctx.send(f"{member.mention} n'a pas d'argent enregistré.")

    # Gestion des erreurs pour la commande de remise à zéro argent
    @reset_balance.error
    async def reset_balance_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(
                "Tu n'as pas la permission d'utiliser cette commande.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                "Tu dois spécifier un membre pour réinitialiser son argent.")
        else:
            await ctx.send("Une erreur est survenue.")


    # Commande pour bannir un utilisateur par ID 
    @commands.command(name="ban")
    async def ban_id(self,
                     ctx,
                     user_id: int,
                     *,
                     reason: str = "Aucune raison spécifiée"):
        if not ctx.author.guild_permissions.ban_members:
            await ctx.send("Tu n'as pas la permission de bannir des membres.")
            return

        user = await self.bot.fetch_user(user_id)
        if user:
            try:
                await ctx.guild.ban(user, reason=reason)
                await ctx.send(
                    f"L'utilisateur {user} a été banni avec succès pour : {reason}"
                )
            except discord.Forbidden:
                await ctx.send(
                    "Je n'ai pas les permissions nécessaires pour bannir cet utilisateur."
                )
            except discord.HTTPException as e:
                await ctx.send(f"Une erreur est survenue lors du ban : {e}")
        else:
            await ctx.send("Aucun utilisateur trouvé avec cet ID.")

    # Commande pour obtenir des infos sur un utilisateur
    @commands.command(name="userinfo")
    async def userinfo(self, ctx, user: discord.User):
        embed = discord.Embed(
            title=f"Infos de {user.name}",
            description=f"Voici les informations sur {user.name}",
            color=discord.Color.blue())
        embed.add_field(name="Nom d'utilisateur", value=user.name)
        embed.add_field(name="ID", value=user.id)
        embed.set_thumbnail(url=user.avatar.url)
        await ctx.send(embed=embed)

    # POKER Commands
    @commands.command(name='start_poker')
    async def start_poker(self, ctx):
        if self.bot.game.status != GameStatus.OFF:
            await ctx.send("Le poker ne peut etre demarré qu'une seule fois!")
            return
        self.bot.game.initialize(ctx)
        await ctx.send(f"Poker initialisé")
        self.bot.game.add_player(ctx.author)
        await ctx.send(f"{ctx.author.name} a rejoint la table!")
        await self.bot.game.display_entry_window(ctx)
        await self.bot.game.display_cpu_window(ctx)
        await self.bot.game.display_start_window(ctx)

    @commands.command(name="join_poker")
    async def join_poker(self, ctx):
        if self.bot.game.status != GameStatus.INIT:
            await ctx.send(
                "Le poker ne peut etre rejoint que lors de la phase d'init!")
            return

        if ctx.author in self.bot.game.players:
            await ctx.send(
                f"{ctx.author.name}, vous avez déjà rejoint la partie !")
            return

        self.bot.game.add_player(ctx.author)
        await ctx.send(f"{ctx.author.name} a rejoint la partie !")

        # FIXME Check nb players
        await ctx.send(
            f"Il y a actuellement {len(self.bot.game.players)} joueur(s) dans la partie."
        )

        if self.bot.game.can_start():
            await ctx.send(f"La partie peut maintenant commencer !")
            await ctx.send(f"cliquez sur le bouton Démarrer la partie")

    @commands.command(name="join_cpu")
    async def join_cpu(self, ctx):
        if self.bot.game.status != GameStatus.INIT:
            await ctx.send(
                "Le poker ne peut etre rejoint que lors de la phase d'init!")
            return

        cpu_player = self.bot.game.create_cpu_player()
        self.bot.game.add_player(cpu_player)
        await ctx.send(f"{cpu_player.name} a rejoint la partie !")

        # FIXME Check nb players
        await ctx.send(
            f"Il y a actuellement {len(self.bot.game.players)} joueur(s) dans la partie."
        )

        if self.bot.game.can_start():
            await ctx.send(f"La partie peut maintenant commencer !")
            await ctx.send(f"Utilisez la commande $start pour démarrer")

    @commands.command(name="start")
    async def start(self, ctx):
        # FIXME Check start
        if not self.bot.game.can_start():
            await ctx.send(
                f"Il y a actuellement {len(self.bot.game.players)} joueur(s) dans la partie."
            )
            await ctx.send(f"La partie ne peut pas etre démarée !")
            return

        await ctx.send("La partie commence maintenant !")

        self.bot.game.start_game()
        self.bot.game.start_betting_round()
        self.bot.game.display_entry_window(ctx)


        player_hands = self.bot.game.get_players_hands()
        for player in self.bot.game.players:
            hand = player_hands.get(player, [])
            if not isinstance(player, FakeMember):
                await self.bot.game.display_player_window(self.bot.game.current_player)
                


    # Commande pour miser, suivre, relancer
    @commands.command(name='miser')
    async def bet(self, ctx, amount: int):
        if self.bot.game.status != GameStatus.RUNNING:
            await ctx.send("Aucun jeu n'est en cours!")
            return

        #FIXME : Demo only
        player = self.get_author_or_cpu_if_current(ctx)
        try:
            self.bot.game.bet(player, amount)
        except ValueError as e:
            await ctx.send(f"{e}")
            return

        await ctx.send(f"{player.name} a misé {amount} jetons.")
        await self.bot.game.handle_played(ctx)

    # Commande pour se coucher
    @commands.command(name='coucher')
    async def fold(self, ctx):
        if self.bot.game.status != GameStatus.RUNNING:
            await ctx.send("Aucun jeu n'est en cours!")
            return

        #FIXME : Demo only
        player = self.get_author_or_cpu_if_current(ctx)

        try:
            self.bot.game.fold(player)
        except ValueError as e:
            await ctx.send(f"{e}")
            return

        await ctx.send(f"{player.name} s'est couché.")
        await self.bot.game.handle_played(ctx)

    #FIXME Commande pour quitter la partie
    @commands.command(name='partir')
    async def leave_poker(self, ctx):
        if self.bot.game.status != GameStatus.RUNNING:
            await ctx.send("Aucun jeu n'est en cours!")
            return
        player = self.get_author_or_cpu_if_current(ctx)
        if ctx.author in self.bot.game.players:
            self.bot.game.players.remove(ctx.author)
            self.bot.game.player_chips[
                ctx.author] = 0  # Réinitialiser les crédits
            await ctx.send(f"{ctx.author.name} a quitté la partie.")
        else:
            await ctx.send("Vous n'êtes pas dans cette partie!")

    # Commande pour passer à la phase suivante (flop, turn, river)
    @commands.command(name='check')
    async def check(self, ctx):

        if self.bot.game.status != GameStatus.RUNNING:
            await ctx.send("Aucun jeu n'est en cours!")
            return

        #FIXME : Demo only
        player = self.get_author_or_cpu_if_current(ctx)

        try:
            difference = self.bot.game.check(player)
            if difference != 0:
                await ctx.send(
                    f"{player.name} a complété sa mise avec {difference} jetons, mise totale: {self.bot.game.get_player_bet(player)}."
                )
            else:
                await ctx.send(f"{player.name} a suivi.")
        except ValueError as e:
            await ctx.send(f"error:{e}")
            return

        await self.bot.game.handle_played(ctx)

    # FIXME : only for demo
    def get_author_or_cpu_if_current(self, ctx):
        player = ctx.author
        expected_player = self.bot.game.current_player
        if expected_player and isinstance(expected_player, FakeMember):
            player = expected_player
        return player

    @commands.command(name='mises')
    async def get_mises(self, ctx):
        if self.bot.game.status != GameStatus.RUNNING:
            await ctx.send("Aucun jeu n'est en cours!")
            return

        await ctx.send(f"Mises du tour")
        await ctx.send(f" MinTour : {self.bot.game.min_bet_tour}")
        await ctx.send(f" Max : {self.bot.game.get_current_max_bet()}")
        for player in self.bot.game.players:
            await ctx.send(
                f" -{player.name}: {self.bot.game.get_player_bet(player)} jetons."
            )

    @commands.command(name='pot')
    async def get_pot(self, ctx):
        if self.bot.game.status != GameStatus.RUNNING:
            await ctx.send("Aucun jeu n'est en cours!")
            return

        await ctx.send(f"Contenu du pot : {self.bot.game.pot} jetons")


    @commands.command(name="reset_poker")
    @commands.has_permissions(administrator=True)
    async def reset_poker(self, ctx):
        self.bot.game.reset_game()
        await ctx.send("Le poker a été réinitialisé.")

    # FIXME Revoir help
    @commands.command()
    async def aide(self, ctx):
        help_text = """
        Bienvenue dans l'aide ! Voici les commandes disponibles :

        1. $aide - Affiche cette aide.
        2. $solde - Affiche votre argent.
        3. $niveau - Affiche votre pourcentage d'expérience.
        4. $shop - Vous ouvre la boutique.
        5. $payer - Paye un utilisateur.
        6. $userinfo @utilisateur - Affiche les informations sur un utilisateur.
        7. $start_poker - Démarre une partie de poker.
        8. $join_poker - Rejoins une partie de poker.
        9. $miser - Mise un montant de jetons.
        10. $suivre - Suivre la mise du tour.
        11. $relancer - Relance la mise du tour.
        12. $coucher - Se couche.
        13. $partir - Quitte la partie
        14. $boutique - Ouvre la boutique.

        Commandes admin
        1. $donner @utilisateur montant - Donne de l'argent à un utilisateur.
        2. $ban_id @utilisateur raison - Banni un utilisateur par ID.
        3. $reset_niveau @utilisateur - Réinitialise l'expérience de l'util
        4. $reset_balance @utilisateur - Réinitialise l'argent de l'utilisateur.
        5. $user_info @utilisateur - Affiche les informations sur un utilisateur.
        6. $reset_poker - Réinitialise le poker.
        7. $add_item prix nom - Ajoute un article à la boutique.
        8. $remove_item <id> - Supprime un article de la boutique.
        9. $list_items - Liste tous les articles de la boutique avec leurs IDs.

        Utilisez ces commandes pour interagir avec le bot.
        """
        await ctx.send(help_text)

    @commands.command(name="ping")
    async def ping(self, ctx):
        """Répond avec 'Pong!'."""
        await ctx.send("Pong!")

    @commands.command(name="hello")
    async def hello(self, ctx):
        """Répond avec un message de bienvenue."""
        await ctx.send(f"Salut {ctx.author.mention} ! 😊")

    @commands.command(name="commenter")
    async def commenter(self, ctx, item_id: int, *, comment_text: str):
        """Ajoute un commentaire à un article. Usage: $commenter <id_article> <commentaire>"""
        if not self._db:
            await ctx.send("❌ La base de données n'est pas disponible.")
            return
        
        # Vérifier que l'article existe
        item = self._db.get_item(item_id)
        if not item:
            await ctx.send(f"❌ Aucun article trouvé avec l'ID {item_id}.")
            return
        
        item_name, item_price = item
        
        # S'assurer que l'utilisateur existe
        if self._db.user_get_balance(ctx.author.id) is None:
            self._db.user_create(ctx.author.id)
        
        success = self._db.add_comment(
            ctx.author.id,
            ctx.author.display_name,
            item_id,
            comment_text
        )
        
        if success:
            await ctx.send(f"✅ Commentaire ajouté à l'article **{item_name}**!")
        else:
            await ctx.send("❌ Erreur lors de l'ajout du commentaire.")

    @commands.command(name="voir_commentaires")
    async def voir_commentaires(self, ctx, item_id: int):
        """Affiche les commentaires d'un article. Usage: $voir_commentaires <id_article>"""
        if not self._db:
            await ctx.send("❌ La base de données n'est pas disponible.")
            return
        
        # Vérifier que l'article existe
        item = self._db.get_item(item_id)
        if not item:
            await ctx.send(f"❌ Aucun article trouvé avec l'ID {item_id}.")
            return
        
        item_name, item_price = item
        comments = self._db.get_item_comments(item_id)
        
        if not comments:
            await ctx.send(f"💬 Aucun commentaire pour l'article **{item_name}**.")
            return
        
        embed = discord.Embed(
            title=f"💬 Commentaires: {item_name}",
            description=f"Prix: {item_price} jetons",
            color=discord.Color.blue()
        )
        
        for username, comment_text, timestamp in comments[:10]:  # Limiter à 10 commentaires
            embed.add_field(
                name=f"👤 {username}",
                value=f"{comment_text}\n*{timestamp}*",
                inline=False
            )
        
        if len(comments) > 10:
            embed.set_footer(text=f"Affichage de 10 commentaires sur {len(comments)}")
        
        await ctx.send(embed=embed)


# Fonction pour ajouter les commandes au bot
async def setup(bot):
    await bot.add_cog(BotCommands(bot))



