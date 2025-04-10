import random
from collections import Counter
from datetime import datetime
from enum import Enum
from discord.ext import commands
import discord
import asyncio
from discord.ui import Button, View, Modal, TextInput
from discord.webhook.async_ import interaction_message_response_params

from db_manager import DBManager

MIN_PLAYERS = 1

# Définir les classes pour le jeu de poker
class Card:
    suits = ['♠️', '♥️', '♦️', '♣️']
    values = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']

    def __init__(self, suit, value):
        self.suit = suit
        self.value = value

    def __repr__(self):
        return f"{self.value}{self.suit}"


class Deck:
    def __init__(self):
        self.cards = [
            Card(suit, value) for suit in Card.suits for value in Card.values
        ]
        random.shuffle(self.cards)

    def draw(self):
        return self.cards.pop()


class GameStatus(Enum):
    """Enum pour représenter un statut."""
    OFF = 0
    INIT = 1
    RUNNING = 2
    ENDED = 3


class FakeMember:
    def __init__(self, bot, name, id):
        self.bot = bot
        self.name = name
        self.id = id

    def decide_action(self, game):
        if self in game.folded_players:
            return "fold"

        hand = game.player_hands.get(self, [])
        community = game.community_cards
        full_hand = hand + community

        current_bet = game.get_current_max_bet()
        my_bet = game.get_player_bet(self)
        to_call = current_bet - my_bet
        my_chips = game.player_chips[self]

        values = [card.value for card in full_hand]
        counts = Counter(values)
        best_count = max(counts.values(), default=1)

        if best_count >= 3:
            if to_call <= my_chips * 0.5:
                return "raise"
            else:
                return "call"
        elif best_count == 2:
            if to_call == 0:
                return "check"
            elif to_call <= my_chips * 0.3:
                return "call"
            else:
                return "fold"
        else:
            if to_call == 0:
                return "check"
            elif to_call <= my_chips * 0.2:
                return "call"
            else:
                return "fold"


class PokerGame:
    def __init__(self, bot):
        self.bot = bot
        self.status: GameStatus = GameStatus.OFF
        self._db: DBManager = self.bot.get_cog("DBManager")
        self.players = []  # Liste des joueurs
        self.deck = Deck()
        self.community_cards = []  # Cartes communes
        self.pot = 0  # Le pot
        self.players_bets = {}  # Dictionnaire pour suivre les mises des joueurs
        self.min_bet_tour = 0  # Tour de mise actuel
        self.player_chips = {}  # Jetons des joueurs
        self.folded_players = []  # Liste des joueurs qui ont abandonné
        self.round_over = False  # Drapeau de fin de tour
        self.game_id = random.randint(1000, 9999)  # ID unique de la partie
        self.winners = []
        self.current_player = None
        self.first_max_bet_player = None

    def initialize(self, ctx):
        self.status = GameStatus.INIT
        self.ctx = ctx

    def can_start(self):
        if self.status == GameStatus.OFF or self.status == GameStatus.RUNNING:
            return False

        # Compter tous les joueurs, y compris les FakeMember (CPU)
        total_players = len(self.players)

        # Compte aussi les FakeMember comme des joueurs
        num_cpu_players = len([p for p in self.players if isinstance(p, FakeMember)])

        if total_players - num_cpu_players < MIN_PLAYERS:
            return False  # Si le nombre de joueurs réels est inférieur au minimum, on ne peut pas démarrer

        return True


    def add_player(self, player):
        if player not in self.players:
            self.players.append(player)

    def create_cpu_player(self):
        """Ajoute un joueur CPU."""
        num = 1 + len([p for p in self.players if isinstance(p, FakeMember)])
        cpu_id = 9000 + num
        cpu_player = FakeMember(self.bot, f"FakePlayer_{num}", cpu_id)
        return cpu_player

    def deal_cards(self):
        self.player_hands = {
            player: [self.deck.draw(), self.deck.draw()]
            for player in self.players if player not in self.folded_players
        }

    def reset_bets(self):
        self.players_bets = {player: 0 for player in self.players}

    def collect_bets(self):
        # Collecte des mises des joueurs dans le pot
        for player, bet in self.players_bets.items():
            if player not in self.folded_players:
                self.pot += bet
                # FIXME: mettre à jour le solde ou les jetons
                self.player_chips[player] -= bet
                if not isinstance(player, FakeMember):
                    self._db.user_add_balance(player.id, -bet)  # Mise à jour du solde du joueur

                self.players_bets[player] = 0

    def next_card(self):
        self.collect_bets()
        self.min_bet_tour = 0  # Réinitialisation du min_bet_tour
        community_cards_count = len(self.community_cards)

        if (len(self.players) - len(self.folded_players)) == 1:
            return None

        if community_cards_count == 0:
            self.community_cards.extend([self.deck.draw() for _ in range(3)])
            return (f"Le flop a été révélé: {self.show_community_cards()}")
        elif community_cards_count == 3:
            self.community_cards.append(self.deck.draw())
            return (f"Le turn a été révélé: {self.show_community_cards()}")
        elif community_cards_count == 4:
            self.community_cards.append(self.deck.draw())
            return (f"Le river a été révélé: {self.show_community_cards()}")
        else:
            return None

    def show_community_cards(self):
        return ' '.join(str(card) for card in self.community_cards)

    def get_players_hands(self):
        return {
            player: ' '.join(str(card) for card in cards)
            for player, cards in self.player_hands.items()
        }

    def start_betting_round(self):
        self.reset_bets()
        return

    def get_player_bet(self, player):
        return self.players_bets.get(player, 0)

    def get_current_max_bet(self):
        return max(self.players_bets.values(), default=0)

    def start_game(self):
        self.status = GameStatus.RUNNING
        self.min_bet_tour = 20

        self._init_players()
        self.deal_cards()
        self.reset_current_player()

    def _init_players(self):
        for player in self.players:
            if not isinstance(player, FakeMember):
                self._db.user_ensure_exist(player)
                self.player_chips[player] = self._db.user_get_balance(player.id)  # Solde du joueur
            else:
                self.player_chips[player] = 500  # Jetons initiaux pour le joueur CPU

            self.players_bets[player] = 0  # Mise initiale de 0 pour chaque joueur

    def best_hand(self, hand):
        values = [card.value for card in hand]
        suits = [card.suit for card in hand]
        counts = Counter(values)
        sorted_counts = sorted(counts.items(), key=lambda x: (-x[1], -Card.values.index(x[0])))

        is_flush = len(set(suits)) == 1
        is_straight = False
        sorted_values = sorted([Card.values.index(v) for v in values])
        if sorted_values == list(range(sorted_values[0], sorted_values[0] + len(sorted_values))):
            is_straight = True

        if is_straight and is_flush:
            return (f"Quinte flush")
        if sorted_counts[0][1] == 4:
            return (f"Carré")
        if sorted_counts[0][1] == 3 and sorted_counts[1][1] == 2:
            return (f"Full")
        if is_flush:
            return (f"Couleur")
        if is_straight:
            return (f"Quinte")
        if sorted_counts[0][1] == 3:
            return (f"Brelan")
        if sorted_counts[0][1] == 2 and sorted_counts[1][1] == 2:
            return (f"Double paire")
        if sorted_counts[0][1] == 2:
            return (f"Paire")
        return (f"Hauteur")

    def evaluate_hands(self):
        player_hands = {
            player: self.player_hands[player] + self.community_cards
            for player in self.players if player not in self.folded_players
        }
        hand_rankings = {
            player: self.best_hand(hand)
            for player, hand in player_hands.items()
        }
        return hand_rankings

    def determine_winner(self):
        hand_rankings = self.evaluate_hands()
        best_rank = None
        self.winners = []
        self.winning_hand_type = ""

        for player, rank in hand_rankings.items():
            if best_rank is None or rank > best_rank:
                best_rank = rank
                self.winners = [player]
                self.winning_hand_type = rank
            elif rank == best_rank:
                self.winners.append(player)

    def end_game(self):
        self.status = GameStatus.ENDED
        self.determine_winner()
        if len(self.winners) > 0:
            gain = self.pot / len(self.winners)
            for player in self.winners:
                # Mise à jour des jetons du joueur
                self.player_chips[player] += gain
                if not isinstance(player, FakeMember):
                    self._db.user_add_balance(player.id, gain)

    def reset_game(self):
        self.status = GameStatus.INIT
        self.folded_players.clear()
        self.pot = 0
        self.community_cards.clear()
        self.players_bets.clear()
        self.player_chips.clear()
        self.deck = Deck()  # Crée un nouveau deck pour la prochaine partie
        self.game_id = random.randint(1000, 9999)  # Nouveau game_id pour la prochaine partie
        self.winners = []  # Liste vide de gagnants
        self.round_over = False  # Réinitialiser l'état de la partie

    def bet(self, player, amount):
        if player not in self.players:
            raise ValueError("Vous n'êtes pas dans cette partie!")

        if player in self.folded_players:
            raise ValueError("Vous vous êtes déjà couché!")

        if player != self.current_player:
            raise ValueError("Ce n'est pas votre tour de jouer")

        if amount <= 0:
            raise ValueError("La mise doit être supérieure à zéro.")

        min_bet = self.get_current_max_bet()

        amount_relative = amount + min_bet
        bet_relatif = amount_relative - self.players_bets[player]

        current_chips = self.player_chips[player]
        if current_chips < bet_relatif:
            raise ValueError(
                f"Vous n'avez pas assez de jetons. Vous avez {current_chips} jetons."
            )

        self.players_bets[player] += bet_relatif
        max_bet = max(self.players_bets.values(), default=0)

        if amount > max_bet:
            self.first_max_bet_player = player  # Nouveau joueur de référence

    def fold(self, player):
        if player not in self.players:
            raise ValueError("Vous n'êtes pas dans cette partie!")

        if player != self.current_player:
            raise ValueError("Ce n'est pas votre tour de jouer")

        if player in self.folded_players:
            raise ValueError("Vous vous êtes déjà couché!")

        self.folded_players.append(player)

    def leave_poker(self, player):
        if player not in self.players:
            raise ValueError("Vous n'êtes pas dans cette partie!")

        if player != self.current_player:
            raise ValueError("Ce n'est pas votre tour de jouer")

        if player in self.folded_players:
            raise ValueError("Vous vous êtes couché!")

        self.bot.game.players.remove(player)

    def check(self, player):
        if player not in self.players:
            raise ValueError("Vous n'êtes pas dans cette partie!")

        if player != self.current_player:
            raise ValueError("Ce n'est pas votre tour de jouer")

        if player in self.folded_players:
            raise ValueError("Vous vous êtes déjà couché!")

        playerbet = self.players_bets.get(player, 0)
        difference = 0

        min_bet = max(self.min_bet_tour, self.get_current_max_bet())

        if playerbet < min_bet:
            difference = min_bet - playerbet
            self.players_bets[player] += difference
            self.pot += difference
            self.player_chips[player] -= difference
            if not isinstance(player, FakeMember):
                self._db.user_add_balance(player.id, -difference)

    async def display_player_window(self, player):
        if isinstance(player, FakeMember):
            await self.display_cpu_window(player)
        else:
            await self.display_human_window(player)  # ta méthode pour afficher l'humain

        player_view = PlayerView(self.ctx, self, player)
        message = await self.ctx.send(f"c'est au tour de {player.name} :", view=player_view)
        player_view.start_countdown(message)

    async def display_entry_window(self, ctx):
        Joinpoker_view = JoinPokerView(self.ctx, self)
        message = await self.ctx.send(view=Joinpoker_view)

    async def display_cpu_window(self, ctx):
        Joincpu_view = JoinCpuView (self.ctx, self)
        message = await self.ctx.send(view=Joincpu_view)

    async def display_start_window(self, ctx):
        Start_view = StartView (self.ctx, self)
        message = await self.ctx.send(view=Start_view)


    async def handle_played(self, ctx):
        await self._compute_next_player(ctx)

        if self.current_player:
            if isinstance(self.current_player, FakeMember):
                action = self.current_player.decide_action(self)

                # 💬 Annonce dans le salon
                await ctx.send(f"🤖 **{self.current_player.name}** a choisi de **{action.upper()}**")

                await self.apply_action(self.current_player, action)
                await self.handle_played(ctx)  # continue boucle bots
            else:
                await self.display_player_window(self.current_player)
            return

        await ctx.send("🃏 Le tour est terminé")

        if self.only_bots_remaining():
            await ctx.send("⚠️ Tous les joueurs humains ont quitté ou se sont couchés. Le jeu continue avec les bots...")

        # Next card
        ret = self.next_card()
        if ret:
            await ctx.send(ret)
            self.reset_current_player()
            await self.handle_played(ctx)
        else:
            self.end_game()
            winners_text = ', '.join([winner.name for winner in self.winners])
            await ctx.send(
                f"🏁 Le jeu est terminé! Le gagnant est: **{winners_text}** avec une **{self.winning_hand_type}**. "
                f"Le pot de **{self.pot} jetons** a été distribué."
            )
            await self.display_entry_window(self.players[0])
            await self.display_cpu_window(self.players[0])
            await self.display_start_window(self.players[0])
            self.reset_game()


    async def apply_action(self, player, action):
        if action == "fold":
            self.folded_players.append(player)
        elif action == "call":
            await self.call(player)
        elif action == "check":
            await self.check(player)
        elif action == "raise":
            await self.raise_bet(player, amount=50)  # adapte le montant


    async def handle_fake_player_turn(self):
        await asyncio.sleep(1)  # petit délai pour le réalisme
        player = self.current_player
        action = player.decide_action(self)

        if action == "fold":
            self.fold(player)
        elif action == "check":
            self.check(player)
        elif action == "raise":
            try:
                self.bet(player, 40)  # ou adapter avec une logique de raise dynamique
            except ValueError:
                self.check(player)

        await self.handle_played(self.ctx)


    def _get_author_or_cpu_if_current(self):
        player = self.ctx.author
        expected_player = self.current_player
        if expected_player and isinstance(expected_player, FakeMember):
            player = expected_player
        return player

    def only_bots_remaining(self):
        return all(isinstance(p, FakeMember) or p in self.folded_players for p in self.players)


    def _get_human_player(self, player):
        if isinstance(player, FakeMember):
            return self.get_first_active_player()
        return player

    async def _compute_next_player(self, ctx):
        """Détermine le prochain joueur actif qui doit jouer ou termine le tour."""

        if not self.players:
            self.current_player = None
            return  # Aucun joueur

        # Si current_player est None, on prend le premier joueur non couché
        if self.current_player is None:
            #await ctx.send(f"pas de current player, recup first actif ")
            self.current_player = self.get_first_active_player()
            return

        # si tout les joueurs sont couchés, alors il n'y a plus de next player a jouer
        num_players = len(self.players)
        num_fold_players = len(self.folded_players)
        num_unfold_players = num_players - num_fold_players
        if num_unfold_players == 1:
            #await ctx.send(f"in compute next player : break : players={num_players} fold={num_fold_players} => unfold={num_unfold_players}==1 =>out")
            self.current_player = None
            return

        min_bet = max(self.min_bet_tour, self.get_current_max_bet())

        current_index = self.players.index(self.current_player)

        for _ in range(num_players):  # Boucle circulaire
            current_index = (current_index + 1) % num_players
            next_player = self.players[current_index]

            if next_player not in self.folded_players:
                # Si on revient à first_max_bet_player, on termine le tour
                if next_player == self.first_max_bet_player:
                    self.current_player = None
                    return  # Tour terminé

                # Si ce joueur doit encore miser, on l'assigne comme current_player
                player_bet = self.players_bets.get(next_player, 0)
                if (player_bet < min_bet) or (min_bet == 0):
                    self.current_player = next_player
                    return

        # Aucun joueur ne doit jouer, on passe au tour suivant
        await ctx.send(f"fin de la fonction _compute_next_player return none")
        self.current_player = None

    def reset_current_player(self):
        """Retourne le premier joueur qui n'est pas couché."""
        self.current_player = self.get_first_active_player()
        self.first_max_bet_player = self.current_player

    def get_first_active_player(self):
        """Retourne le premier joueur qui n'est pas couché."""
        for player in self.players:
            if player not in self.folded_players:
                return player
        return None

    def view_cards(self, player):
        """Affiche les cartes du joueur."""
        player_cards = self.player_hands[player]
        cards_str = ', '.join([str(card) for card in player_cards])
        return f"{player.name} a les cartes : {cards_str}"

class MockGame:
    def __init__(self):
        self.players = []

    def add_player(self, player):
        self.players.append(player)

    def create_cpu_player(self):
        return discord.Object(id=123456789)  # Un faux utilisateur CPU

    def can_start(self):
        if self.status == GameStatus.OFF or self.status == GameStatus.RUNNING:
            return False
        return len(self.players) >= MIN_PLAYERS


    def start_game(self):
        pass

    def start_betting_round(self):
        pass

    async def display_player_window(self, player):
        pass

class JoinPokerView(discord.ui.View):
    def __init__(self, ctx, game):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.game = game
        self.cpu_count = 0 

    @discord.ui.button(label="Rejoindre", style=discord.ButtonStyle.green)
    async def join_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        if self.game.status == GameStatus.RUNNING:
            await interaction.followup.send("La partie a déjà commencé ! Vous ne pouvez plus rejoindre.", ephemeral=True)
            return

        if interaction.user in self.game.players:
            await interaction.followup.send("Vous avez déjà rejoint la partie !", ephemeral=True)
            return

        self.game.add_player(interaction.user)
        await interaction.followup.send(f"{interaction.user.name} a rejoint la partie !", ephemeral=False)


class JoinCpuView(discord.ui.View):
    def __init__(self, ctx, game):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.game = game
        self.cpu_count = 0

    @discord.ui.button(label="Ajouter un CPU", style=discord.ButtonStyle.blurple)
    async def add_cpu_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        if len(self.game.players) >= 6:  # Un exemple de limite de joueurs
            await interaction.followup.send("Le nombre maximum de joueurs est atteint.", ephemeral=True)
            return

        cpu_player = self.game.create_cpu_player()
        self.game.add_player(cpu_player)
        self.cpu_count += 1
        total_players = len(self.game.players)

        # Confirme l'ajout du CPU et affiche le nombre total de joueurs
        await interaction.followup.send(
            f"Un CPU a rejoint la partie ! Nombre total de joueurs : {total_players}", ephemeral=False
        )


class StartView(discord.ui.View):
    def __init__(self, ctx, game):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.game = game
        self.cpu_count = 0

    @discord.ui.button(label="Démarrer la partie", style=discord.ButtonStyle.success)
    async def start_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        # Vérifiez si tous les joueurs ont bien rejoint
        if not self.game.can_start():
            await interaction.followup.send("Il faut au moins 2 joueurs pour démarrer la partie.", ephemeral=True)
            return

        # Si tout est OK, commencez la partie
        self.clear_items()  # Supprimer les boutons pour éviter d'ajouter de nouveaux joueurs
        self.game.start_game()  # Démarre réellement le jeu
        self.game.start_betting_round()  # Commence la première ronde de paris

        # Affiche les informations pour le premier joueur
        await self.game.display_player_window(self.game.players[0])

class PlayerView(discord.ui.View):

    def __init__(self, ctx, game, player):
        super().__init__()
        self.ctx = ctx
        self.game = game
        self.player = player
        self.countdown_button = discord.ui.Button(label="Décompte", style=discord.ButtonStyle.blurple, disabled=True)
        #self.countdown_button.callback = self.countdown_callback
        self.add_item(self.countdown_button)
        self._countdown_task = None
        self.running = True

###################################

    @discord.ui.button(label="Suivre", style=discord.ButtonStyle.success)
    async def follow_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if (interaction.user
                != self.player) and (not isinstance(self.player, FakeMember)):
            await interaction.response.send_message("Ce n'est pas votre tour !", ephemeral=True)
            await interaction.response.defer()
            return
        self.clear_items()
        await interaction.message.edit(view=self)

        try:
            await self.stop_countdown()
            difference = self.game.check(self.player)
            if difference != 0:
                await self.ctx.send(
                    f"{self.player.name} a complété sa mise avec {difference} jetons, mise totale: {self.game.get_player_bet(self.player)}."
                )
            else:
                await self.ctx.send(f"{self.player.name} a suivi.")
        except ValueError as e:
            await self.ctx.send(f"Erreur: {e}")

        await self.game.handle_played(self.ctx)
        self.game.next_turn()

###################################

    @discord.ui.button(label="Relancer", style=discord.ButtonStyle.green)
    async def custom_bet_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CustomBetModal(self.game, self.player))
        await interaction.response.defer()

        if (interaction.user != self.player) and (not isinstance(self.player, FakeMember)):
            await interaction.followup.send("Ce n'est pas votre tour !", ephemeral=True)
            return

        await self.game.handle_played(self.game.ctx)
        await self.game.next_turn()
        self.game.next_turn()

###################################

    @discord.ui.button(label="Coucher", style=discord.ButtonStyle.danger)
    async def fold_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if (interaction.user
                != self.player) and (not isinstance(self.player, FakeMember)):
            await interaction.response.send_message("Ce n'est pas votre tour !", ephemeral=True)

            return
        self.clear_items()
        await interaction.message.edit(view=self)

        try:
            await self.stop_countdown()
            self.game.fold(self.player)
        except ValueError as e:
            await self.ctx.send(f"{e}")
            return

        await self.ctx.send(f"{self.player.name} s'est couché.")
        await self.game.handle_played(self.ctx)
        self.game.next_turn()

###################################

    @discord.ui.button(label="Partir", style=discord.ButtonStyle.danger)
    async def leave_poker_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        if (interaction.user
                != self.player) and (not isinstance(self.player, FakeMember)):
            await interaction.response.send_message("Ce n'est pas votre tour !", ephemeral=True)
            return
        await interaction.message.edit(view=self)

        try:
            await self.stop_countdown()
            self.game.players.remove(self.player)
        except ValueError as e:
            await self.ctx.send(f"{e}")
            return

        await self.ctx.send(f"{self.player.name} as quitté la table.")
        await self.game.handle_played(self.ctx)
        self.game.next_turn()

###################################

    @discord.ui.button(label="voir cartes", style=discord.ButtonStyle.secondary)
    async def view_cards_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        if (interaction.user
                != self.player) and (not isinstance(self.player, FakeMember)):
            await interaction.response.send_message("Ce n'est pas votre tour !", ephemeral=True)
            return
        await interaction.message.edit(view=self)

        try:
            player_hands = self.game.get_players_hands()
            hand = player_hands.get(interaction.user, [])
            await interaction.followup.send(f"Votre main: {hand}",
                                            ephemeral=True)
        except ValueError as e:
            await interaction.followup.send(f"{e}", ephemeral=True)
        return

###################################

    def start_countdown(self, message: discord.Message):
        self._countdown_task = asyncio.create_task(self.countdown_task(message))


    async def countdown_task(self, message: discord.Message):

        try:
            for i in range(20, 0, -1):
                self.countdown_button.label = f"Décompte : {i}s"
                await message.edit(view=self)
                await asyncio.sleep(1)
            await self.ctx.send("Temps écoulé.")
            try:
                self.game.fold(self.player)
            except ValueError as e:
                await self.ctx.send(f"{e}")
                return

            await self.ctx.send(f"{self.player.name} s'est couché.")
            await self.game.handle_played(self.ctx)
            self.game.next_turn()
        except asyncio.CancelledError:
            return

    async def stop_countdown(self):
        if self._countdown_task:
            self._countdown_task.cancel()
            try:
                await self._countdown_task
            except asyncio.CancelledError:
                pass

###################################
class CustomBetModal(discord.ui.Modal, title="Mise personnalisée"):
    amount = discord.ui.TextInput(
        label="Entrez le montant à miser",
        placeholder="Ex : 150",
        min_length=1,
        max_length=10,
        required=True
    )

    def __init__(self, game, player):
        super().__init__()
        self.game = game
        self.player = player

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user != self.player:
            await interaction.response.send_message("Ce n'est pas votre tour !", ephemeral=True)
            return

        try:
            amount = int(self.amount.value)

            if amount <= 0:
                raise ValueError("Le montant doit être positif.")

            if amount > self.game.player_chips[self.player]:
                raise ValueError("Vous n'avez pas assez de jetons.")

            self.game.bet(self.player, amount)
            await interaction.response.send_message(
                f"✅ {self.player.name} a misé **{amount} jetons**.",
                ephemeral=False
            )
            await self.game.handle_played(self.game.ctx)

        except ValueError as e:
            await interaction.response.send_message(f"Erreur : {e}", ephemeral=True)




##################################

    async def interaction_check(self,
                                interaction: discord.Interaction) -> bool:
        if interaction.user != self.player:
            await interaction.response.send_message("Ce n'est pas ton tour !",
                                                    ephemeral=True)
            return False
        return True