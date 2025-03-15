import random
from collections import Counter
from datetime import datetime
from enum import Enum

import discord

from db_manager import DBManager
MIN_PLAYERS=1

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
        self.cards = [Card(suit, value) for suit in Card.suits for value in Card.values]
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
        self.discriminator = f"{id % 9999:04d}"  # Simule un tag Discord aléatoire (0001-9999)
        self.roles = [discord.Object(id=123456)]  # Simule une liste de rôles
        self.joined_at = datetime.datetime.utcnow()  # Simule la date d'inscription


def __repr__(self):
        return f"<FakeMember name={self.name} id={self.id}>"

class PokerGame:
    def __init__(self, bot):
        self.bot = bot
        self.status:GameStatus = GameStatus.OFF
        self._db: DBManager | None = self.bot.get_cog("DBManager")
        self.players = []  # List of players
        self.deck = Deck()
        self.community_cards = []  # Community cards
        self.pot = 0  # The pot
        self.players_bets = {}  # Dictionary to track bets of players
        self.bet_tour = 0  # Current bet tour
        self.player_chips = {}  # Player's chips
        self.folded_players = []  # List of players who folded
        self.round_over = False  # End of round flag
        self.game_id = random.randint(1000, 9999)  # Unique game ID
        self.winners = []

    def initialize(self):
        self.status = GameStatus.INIT

    def can_start(self):
        if self.status==GameStatus.OFF or self.status==GameStatus.RUNNING:
            return False
        return len(self.bot.game.players) >= MIN_PLAYERS

    def add_player(self, player):
        if player not in self.players:
            self.players.append(player)

    def create_cpu_player(self):
        """Ajoute un joueur CPU."""
        num = len([p for p in self.players if isinstance(p, FakeMember)])
        cpu_id = 9000 + num
        cpu_player = FakeMember(self.bot, f"FakePlayer_{num}", cpu_id)
        return cpu_player

    def deal_cards(self):
        self.player_hands = {player: [self.deck.draw(), self.deck.draw()] for player in self.players if player not in self.folded_players}

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
                    self._db.user_update_balance(player.id, -bet)  # Update the player's balance

                self.players_bets[player] = 0

    def has_next_card(self):
        return len(self.community_cards) < 5

    def next_card(self):
        self.collect_bets()
        self.bet_tour = 0
        community_cards_count = len(self.community_cards);

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

    def show_player_hands(self):
        return {player: ' '.join(str(card) for card in cards) for player, cards in self.player_hands.items()}

    def start_betting_round(self):
        self.reset_bets()
        return

    def get_player_bet(self, player):
        return self.players_bets.get(player, 0)

    def start_game(self):
        self.status = GameStatus.RUNNING
        self.bet_tour = 20

        self._init_players()
        self.deal_cards()
        return self.show_community_cards(), self.show_player_hands()

    def _init_players(self):
        for player in self.players:
            if not isinstance(player, FakeMember):
                self._db.user_ensure_exist(player)
                self.player_chips[player] = self._db.user_get_balance(player.id)  # Get the player's balance from DB
            else :
                self.player_chips[player] = 500

            self.players_bets[player] = 0  # Initial bet of 0 for each player

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
        player_hands = {player: self.player_hands[player] + self.community_cards for player in self.players if player not in self.folded_players}
        hand_rankings = {player: self.best_hand(hand) for player, hand in player_hands.items()}
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
                    self._db.user_update_balance(player.id, gain)

    def reset_game(self):
        self.players.clear()
        self.folded_players.clear()
        self.pot = 0
        self.community_cards.clear()
        self.players_bets.clear()
        self.player_chips.clear()
        self.deck = Deck()  # Crée un nouveau deck pour la prochaine partie
        self.game_id = random.randint(1000, 9999)  # Nouveau game_id pour la prochaine partie
        self.winners = []  # Liste vide de gagnants
        self.round_over = False  # Réinitialiser l'état de la partie
