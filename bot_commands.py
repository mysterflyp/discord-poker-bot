import discord
from discord.ext import commands

from db_manager import DBManager
from poker_game import GameStatus


class BotCommands(commands.Cog):
    """Groupe de commandes pour le bot."""

    def __init__(self, bot):
        self.bot = bot
        self._db: DBManager | None = None

    async def cog_load(self):
        """Méthode appelée automatiquement lors du chargement du Cog."""
        self._db = self.bot.get_cog("DBManager")
        if self._db is None:
            raise RuntimeError("❌ Erreur : DBManager n'a pas été chargé avant BotCommands !")

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
        new_target_balance = self._db.user_add_balance(target_member.id, amount)
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
            await ctx.send("Tu n'as pas la permission d'utiliser cette commande.")
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
            await ctx.send(f"L'expérience de {member.mention} a été remise à zéro.")
        else:
            await ctx.send(f"{member.mention} n'a pas d'expérience enregistrée.")

    # Gestion des erreurs pour la commande de remise à zéro level
    # FIXME : Dans le else utiliser error.toStr....
    @reset_niveau.error
    async def reset_niveau_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Tu n'as pas la permission d'utiliser cette commande.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                "Tu dois spécifier un membre pour réinitialiser son expérience.")
        else:
            await ctx.send("Une erreur est survenue.")

    # Commande pour remettre à zéro l'argent d'un utilisateur
    # FIXME : il faut differencier le fait que le user n'existe pas du montant 0
    @commands.command(name="reset_balance")
    @commands.has_permissions(administrator=True)
    async def reset_balance(self, ctx, member: discord.Member):
        new_balance = self._db.user_reset_niveau(member.id)
        if new_balance == 0:
            await ctx.send(f"Le solde de {member.mention} a été remis à zéro.")
        else:
            await ctx.send(f"{member.mention} n'a pas d'argent enregistré.")

    # Gestion des erreurs pour la commande de remise à zéro argent
    @reset_balance.error
    async def reset_balance_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Tu n'as pas la permission d'utiliser cette commande.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                "Tu dois spécifier un membre pour réinitialiser son argent.")
        else:
            await ctx.send("Une erreur est survenue.")


    # Commande pour bannir un utilisateur par ID
    @commands.command(name="ban")
    async def ban_id(self, ctx,
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
        if self.bot.game.status!=GameStatus.OFF:
            await ctx.send("Le poker ne peut etre demarré qu'une seule fois!")
            return

        self.bot.game.initialize()
        await ctx.send(f"Poker initialisé")

        self.bot.game.add_player(ctx.author)
        await ctx.send(f"{ctx.author.name} a rejoint la table!")

    
    @commands.command(name="join_poker")
    async def join_poker(self, ctx):
        if self.bot.game.status!=GameStatus.INIT:
            await ctx.send("Le poker ne peut etre rejoint que lors de la phase d'init!")
            return

        if ctx.author in self.bot.game.players:
            await ctx.send(f"{ctx.author.name}, vous avez déjà rejoint la partie !")
            return
    
        self.bot.game.add_player(ctx.author)
        await ctx.send(f"{ctx.author.name} a rejoint la partie !")

        # FIXME Check nb players
        await ctx.send(f"Il y a actuellement {len(self.bot.game.players)} joueur(s) dans la partie.")

        if self.bot.game.can_start():
            await ctx.send(f"La partie peut maintenant commencer !")
            await ctx.send(f"Utilisez la commande $start pour démarrer")

    
    @commands.command(name="start")
    async def start(self, ctx):
        # FIXME Check start
        if not self.bot.game.can_start():
            await ctx.send(f"Il y a actuellement {len(self.bot.game.players)} joueur(s) dans la partie.")
            await ctx.send(f"La partie ne peut pas etre démarée !")
            return

        first_player = self.bot.game.players[0]
        if ctx.author != first_player:  # Only the first player can start
            await ctx.send(f"Seul le premier joueur ({first_player.name}) peut démarrer la partie.")
            return

        await ctx.send("La partie commence maintenant !")

        community_cards, player_hands = self.bot.game.start_game()
        for player in self.bot.game.players:
            hand = player_hands.get(player, [])
            self.bot.game.start_betting_round()
            await ctx.send ("La phase de mise commence! Chaque joueur peut miser, suivre, relancer ou se coucher")
            await player.send(f"Main de {player.name}: {hand}")
    
    # Commande pour miser, suivre, relancer
    @commands.command(name='miser')
    async def bet(self, ctx, amount: int):
        if self.bot.game.status!=GameStatus.RUNNING:
            await ctx.send("Aucun jeu n'est en cours!")
            return
    
        if ctx.author not in self.bot.game.players:
            await ctx.send("Vous n'êtes pas dans cette partie!")
            return
    
        if ctx.author in self.bot.game.folded_players:
            await ctx.send("Vous vous êtes déjà couché!")
            return
    
        if amount <= 0:
            await ctx.send("La mise doit être supérieure à zéro.")
            return
    
        # Le montant relatif c'est "coller" + la relance
        amount_relative = amount + self.bot.game.bet_tour
    
        # Maintenant, à combien cela revient-il par rapport a son bet actuel
        bet_relatif = amount_relative - self.bot.game.bets[ctx.author]
    
        # On verifie qu'il a assez
        # FIXME : ne pas utiliser les get_balance pais les game.player.chips
        current_chips = self._db.user_get_balance(ctx.author.id)
        if current_chips < bet_relatif:
            await ctx.send(f"Vous n'avez pas assez de jetons. Vous avez {current_chips} jetons.")
            return
        #Mettre un timer de 20secondes qui dans le cas ou le joueur n'a pas misé, il se couche et le tour passe au joueur suivant
        # on ajoute le montant relatif au bet tour
        self.bot.game.bet_tour += amount_relative
    
        # on affecte le bet tour au bet du joueur (puis que c'est)
        self.bot.game.bets[ctx.author] = self.bot.game.bet_tour
        await ctx.send(f"{ctx.author.name} a misé {amount} jetons.")
    
    # Commande pour se coucher
    @commands.command(name='coucher')
    async def fold(self, ctx):
        if self.bot.game.status!=GameStatus.RUNNING:
            await ctx.send("Aucun jeu n'est en cours!")
            return

        if ctx.author not in self.bot.game.players:
            await ctx.send("Vous n'êtes pas dans cette partie!")
            return
    
        self.bot.game.folded_players.append(ctx.author)
        await ctx.send(f"{ctx.author.name} s'est couché.")
    
    
    # Commande pour quitter la partie
    @commands.command(name='partir')
    async def leave_poker(self, ctx):
        if self.bot.game.status!=GameStatus.RUNNING:
            await ctx.send("Aucun jeu n'est en cours!")
            return
    
        if ctx.author in self.bot.game.players:
            self.bot.game.players.remove(ctx.author)
            self.bot.game.player_chips[ctx.author] = 0  # Réinitialiser les crédits
            await ctx.send(f"{ctx.author.name} a quitté la partie.")
        else:
            await ctx.send("Vous n'êtes pas dans cette partie!")
    
    
    # Commande pour passer à la phase suivante (flop, turn, river)
    @commands.command(name='check')
    async def check(self, ctx):
        if self.bot.game.status!=GameStatus.RUNNING:
            await ctx.send("Aucun jeu n'est en cours!")
            return

        if ctx.author not in self.bot.game.players:
            await ctx.send("Vous n'êtes pas dans cette partie!")
            return
        if len(self.bot.game.winners) > 0:
            await ctx.send("la partie est terminée!")
            return
    
        # Vérifier si la mise du joueur est bien celle du maximum du tour, sinon l'appliquer
        playerbet = self.bot.game.bets.get(ctx.author, 0)
        if playerbet < self.bot.game.bet_tour:
            difference = self.bot.game.bet_tour - playerbet
            self.bot.game.bets[ctx.author] = self.bot.game.bet_tour
            self.bot.game.player_chips[ctx.author] -= difference
            await ctx.send(f"{ctx.author.name} a complété sa mise avec {difference} jetons, mise totale: {self.bot.game.bet_tour}.")
        else:
            return
    
        ret = self.bot.game.next_card()
        if ret:
            await ctx.send(ret)
        else :
            self.bot.game.end_game()
            await ctx.send(f"Le jeu est terminé! Le gagnant est: {', '.join([winner.name for winner in self.bot.game.winners])}. Le pot de {bot.game.pot} jetons a été distribué.")
            self.bot.game.reset_game()
            # FIXME END
            self.bot.game = None
    
    @commands.command(name='mises')
    async def get_mises(self, ctx):
        if self.bot.game.status!=GameStatus.RUNNING:
            await ctx.send("Aucun jeu n'est en cours!")
            return

        await ctx.send(f"Mise actuelle du tour : {self.bot.game.bet_tour}")
        for player in self.bot.game.players:
            await ctx.send(f" -{player.name}: {self.bot.game.bets[player]} jetons.")
    
    @commands.command(name='pot')
    async def get_pot(self, ctx):
        if self.bot.game.status!=GameStatus.RUNNING:
            await ctx.send("Aucun jeu n'est en cours!")
            return

        await ctx.send(f"Contenu du pot : {self.bot.game.pot} jetons")









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
    
        Commandes admin
        1. $donner @utilisateur montant - Donne de l'argent à un utilisateur.
        2. $ban_id @utilisateur raison - Banni un utilisateur par ID.
        3. $reset_niveau @utilisateur - Réinitialise l'expérience de l'util
        4. $reset_balance @utilisateur - Réinitialise l'argent de l'utilisateur.
        5. $user_info @utilisateur - Affiche les informations sur un utilisateur.
    
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


# Fonction pour ajouter les commandes au bot
async def setup(bot):
    await bot.add_cog(BotCommands(bot))
