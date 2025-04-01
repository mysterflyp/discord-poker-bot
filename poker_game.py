import random
from collections import Counter
from datetime import datetime
from enum import Enum

import discord
from discord.ui import View, Select

from db_manager import DBManager

MIN_PLAYERS = 1


# Define the classes for the poker game
class Card:
    suits = ['♠', '♥', '♦', '♣']
    #suits = ['♠️', '♥️', '♦️', '♣️']
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
    """Classe simulant un joueur CPU en imitant discord.Member."""

    def __init__(self, bot, name: str, id: int):
        self.bot = bot
        self.name = name
        self.id = id
        self.display_name = name  # Pour correspondre à Member
        self.mention = f"🤖 {name}"  # Simule la mention d'un joueur CPU


def __repr__(self):
    return f"<FakeMember name={self.name} id={self.id}>"


class PokerGame:

    def __init__(self, bot):
        self.bot = bot
        self.status: GameStatus = GameStatus.OFF
        self._db: DBManager = self.bot.get_cog("DBManager")
        self.players = []  # List of players
        self.deck = Deck()
        self.community_cards = []  # Community cards
        self.pot = 0  # The pot
        self.players_bets = {}  # Dictionary to track bets of players
        self.min_bet_tour = 0  # Current bet tour
        self.player_chips = {}  # Player's chips
        self.folded_players = []  # List of players who folded
        self.round_over = False  # End of round flag
        self.game_id = random.randint(1000, 9999)  # Unique game ID
        self.winners = []
        self.current_player = None
        self.first_max_bet_player = None

    def initialize(self, ctx):
        self.status = GameStatus.INIT
        self.ctx = ctx

    def can_start(self):
        if self.status == GameStatus.OFF or self.status == GameStatus.RUNNING:
            return False
        return len(self.bot.game.players) >= MIN_PLAYERS

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
        # Collecting players' bets into the pot
        for player, bet in self.players_bets.items():
            if player not in self.folded_players:
                self.pot += bet
                #FIXME balance or chips
                self.player_chips[player] -= bet
                if not isinstance(player, FakeMember):
                    self._db.user_add_balance(
                        player.id, -bet)  # Update the player's balance

                self.players_bets[player] = 0

    def has_next_card(self):
        return len(self.community_cards) < 5

    def next_card(self):
        self.collect_bets()
        self.min_bet_tour = 0  # min_bet_tour reset
        community_cards_count = len(self.community_cards)
        if community_cards_count == 0:
            self.flop()
            return (f"Le flop a été révélé: {self.show_community_cards()}")
        elif community_cards_count == 3:
            self.turn()
            return (f"Le turn a été révélé: {self.show_community_cards()}")
        elif community_cards_count == 4:
            self.river()
            return (f"Le river a été révélé: {self.show_community_cards()}")
        else:
            return None

    def flop(self):
        self.community_cards.extend([self.deck.draw() for _ in range(3)])

    def turn(self):
        self.community_cards.append(self.deck.draw())

    def river(self):
        self.community_cards.append(self.deck.draw())

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
                self.player_chips[player] = self._db.user_get_balance(
                    player.id)  # Get the player's balance from DB
            else:
                self.player_chips[player] = 500

            self.players_bets[player] = 0  # Initial bet of 0 for each player

    def best_hand(self, hand):
        values = [card.value for card in hand]
        suits = [card.suit for card in hand]
        counts = Counter(values)
        sorted_counts = sorted(counts.items(),
                               key=lambda x: (-x[1], -Card.values.index(x[0])))

        is_flush = len(set(suits)) == 1
        is_straight = False
        sorted_values = sorted([Card.values.index(v) for v in values])
        if sorted_values == list(
                range(sorted_values[0],
                      sorted_values[0] + len(sorted_values))):
            is_straight = True

        if is_straight and is_flush:
            return "Quinte flush"
        if sorted_counts[0][1] == 4:
            return "Carré"
        if sorted_counts[0][1] == 3 and sorted_counts[1][1] == 2:
            return "Full"
        if is_flush:
            return "Couleur"
        if is_straight:
            return "Quinte"
        if sorted_counts[0][1] == 3:
            return "Brelan"
        if sorted_counts[0][1] == 2 and sorted_counts[1][1] == 2:
            return "Double paire"
        if sorted_counts[0][1] == 2:
            return "Paire"
        return "Hauteur"

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
        for player, rank in hand_rankings.items():
            if best_rank is None or rank > best_rank:
                best_rank = rank
                self.winners = [player]
            elif rank == best_rank:
                self.winners.append(player)

    def end_game(self):
        self.status = GameStatus.ENDED
        self.determine_winner()
        if len(self.winners) > 0:
            gain = self.pot / len(self.winners)
            for player in self.winners:
                #FIXME update balance or chips ?
                self.player_chips[player] += gain
                if not isinstance(player, FakeMember):
                    self._db.user_add_balance(player.id, gain)

    def reset_game(self):
        #self.players.clear()
        self.status = GameStatus.INIT
        self.folded_players.clear()
        self.pot = 0
        self.community_cards.clear()
        self.players_bets.clear()
        #self.player_chips.clear()
        self.deck = Deck()  # Crée un nouveau deck pour la prochaine partie
        self.game_id = random.randint(
            1000, 9999)  # Nouveau game_id pour la prochaine partie
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

        # Le montant relatif c'est "coller" + la relance
        amount_relative = amount + min_bet

        # Maintenant, à combien cela revient-il par rapport a son bet actuel
        bet_relatif = amount_relative - self.players_bets[player]

        # On verifie qu'il a assez
        # FIXME : ne pas utiliser les get_balance pais les game.player.chips
        current_chips = self.player_chips[player]
        if current_chips < bet_relatif:
            raise ValueError(
                f"Vous n'avez pas assez de jetons. Vous avez {current_chips} jetons."
            )

        #Mettre un timer de 20secondes qui dans le cas ou le joueur n'a pas misé, il se couche et le tour passe au joueur suivant
        # on ajoute le montant relatif au bet tour
        min_bet += amount_relative

        # on affecte le bet tour au bet du joueur (puis que c'est)
        self.players_bets[player] = self.min_bet_tour

        # Mettre à jour max_bet et le premier joueur ayant misé ce montant
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
        self.current_player = None

        # FIXME : update first_max_ber_player ??

    def check(self, player):
        if player not in self.players:
            raise ValueError("Vous n'êtes pas dans cette partie!")

        if player != self.current_player:
            raise ValueError("Ce n'est pas votre tour de jouer")

        if player in self.folded_players:
            raise ValueError("Vous vous êtes déjà couché!")

        # Vérifier si la mise du joueur est bien celle du maximum du tour, sinon l'appliquer
        playerbet = self.players_bets.get(player, 0)
        difference = 0

        # Compute the current min bet : min_bet_tour or current max
        min_bet = max(self.min_bet_tour, self.get_current_max_bet())

        if playerbet < min_bet:
            difference = min_bet - playerbet
            self.players_bets[player] = min_bet
            self.player_chips[player] -= difference

        if min_bet > 0:
            self.first_max_bet_player = player

        return difference

    async def display_player_window(self, player):
        view = PlayerView(self.ctx, self, player)
        await self.ctx.send(f"C'est à {player.name} de jouer", view=view)

    async def handle_played(self, ctx):
        await self._compute_next_player(ctx)
        if self.current_player:
            await self.display_player_window(self.current_player)
            return

        await ctx.send(f"Le tour est terminé ")

        # No next player, reveal next card
        ret = self.next_card()
        if ret:
            await ctx.send(ret)
            self.reset_current_player()
            await self.display_player_window(self.current_player)
        else:
            self.end_game()
            winners_text = ', '.join([winner.name for winner in self.winners])
            await ctx.send(
                f"Le jeu est terminé! Le gagnant est: {winners_text}. Le pot de {self.pot} jetons a été distribué."
            )
            self.reset_game()
            await ctx.send(f"Démarrez une nouvelle partie avec $start")

    def _get_author_or_cpu_if_current(self):
        player = self.ctx.author
        expected_player = self.current_player
        if expected_player and isinstance(expected_player, FakeMember):
            player = expected_player
        return player

    def _get_human_player(self, player):
        if isinstance(player, FakeMember):
            return self.get_first_active_player()
        return player
        
    
    async def _compute_next_player(self, ctx):
        """Détermine le prochain joueur actif qui doit jouer ou termine le tour."""

        if not self.players:
            self.current_player = None
            return None  # Aucun joueur

        # Si current_player est None, on prend le premier joueur non couché
        if self.current_player is None:
            await ctx.send(f"pas de current player, recup first actif ")
            self.current_player = self.get_first_active_player()
            return self.current_player
            

        num_players = len(self.players)
        num_fold_players = len(self.folded_players)
        num_unfold_players = num_players - num_fold_players
        if num_unfold_players == 1:
            return None
            return None
        
        min_bet = max(self.min_bet_tour, self.get_current_max_bet())

        current_index = self.players.index(self.current_player)

        for _ in range(num_players):  # Boucle circulaire
            current_index = (current_index + 1) % num_players
            next_player = self.players[current_index]

            if next_player not in self.folded_players:
                # Si on revient à first_max_bet_player, on termine le tour
                if next_player == self.first_max_bet_player:
                    self.current_player = None
                    return None  # Tour terminé

                # Si ce joueur doit encore miser, on l'assigne comme current_player
                player_bet = self.players_bets.get(next_player, 0)
                if (player_bet < min_bet) or (min_bet == 0):
                    self.current_player = next_player
                    return next_player

        # Aucun joueur ne doit jouer, on passe au tour suivant
        await ctx.send(f"fin de la fonction _compute_next_player return none")
        self.current_player = None
        return None

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


class PlayerView(discord.ui.View):

    def __init__(self, ctx, game, player):
        super().__init__()
        self.ctx = ctx
        self.game = game
        self.player = player

    @discord.ui.button(label="Suivre", style=discord.ButtonStyle.success)
    async def follow_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Vérifier que seul le joueur en cours peut interagir
        if (interaction.user != self.player) and (not isinstance(self.player, FakeMember)):
            await interaction.response.send_message("Ce n'est pas votre tour !", ephemeral=True)
            return  # Empêche l'exécution du reste du code
        # Désactiver le bouton après clic
        self.clear_items()
        await interaction.message.edit(view=self)

        try:
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


    @discord.ui.button(label="Coucher", style=discord.ButtonStyle.danger)
    async def fold_callback(self, interaction: discord.Interaction,
                            button: discord.ui.Button):
        if (interaction.user != self.player) and (not isinstance(self.player, FakeMember)):
            await interaction.response.send_message("Ce n'est pas votre tour !", ephemeral=True)
            return
        self.clear_items()
        await interaction.message.edit(view=self)
            
        try:
            self.game.fold(self.player)
        except ValueError as e:
            await self.ctx.send(f"{e}")
            return
            
        await self.ctx.send(f"{self.player.name} s'est couché.")
        await self.game.handle_played(self.ctx)

    


    @discord.ui.button(label="Relancer", style=discord.ButtonStyle.primary)
    async def retry_callback(self, interaction: discord.Interaction,
                             button: discord.ui.Button):
        if (interaction.user != self.player) and (not isinstance(self.player, FakeMember)):
            await interaction.response.send_message("Ce n'est pas votre tour !", ephemeral=True)
            return  # Empêche l'exécution du reste du code

        await interaction.response.send_message(
            f"{self.player.name} as relancé de 🔄")
        self.clear_items()
        await interaction.message.edit(view=self)










