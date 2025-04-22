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


MIN_PLAYERS = 2


# Define the classes for the poker game
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
    """Classe simulant un joueur CPU en imitant discord.Member."""

    def __init__(self, bot, name: str, id: int):
        self.bot = bot
        self.name = name
        self.id = id
        self.display_name = name  # Pour correspondre à Member
        self.mention = f"🤖 {name}"  # Simule la mention d'un joueur CPU
        self.hand = []

    def __repr__(self):
        return f"<FakeMember name={self.name} id={self.id}>"

    def decide_action(self, game):
        """Décide l'action que le FakeMember doit prendre."""
        # Logique simple pour décider de l'action
        hand_strength = self.evaluate_hand_strength(game)

        # Calcul du montant à suivre (relancer ou se coucher)
        min_bet = game.get_current_max_bet()
        player_bet = game.players_bets.get(self, 0)

        # Si la main est forte, relancer
        if hand_strength > 7:
            # Relance avec un montant plus élevé
            return 'raise', random.randint(min_bet, min_bet * 2)
        # Si la main est faible, coucher
        elif hand_strength < 3:
            return 'fold', None
        # Sinon, suivre
        else:
            return 'call', min_bet - player_bet

    def evaluate_hand_strength(self, game):
        """Évalue la force de la main du FakeMember."""
        return random.randint(1, 10)


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
        self.rounds = []  # Historique des tours (optionnel)

    def get_first_active_player(self):
        """Retourne le premier joueur qui n'est pas couché."""
        for player in self.players:
            if player not in self.folded_players:
                return player
        return None
        
    def get_current_max_bet(self):
        """Retourne la mise maximum actuelle du jeu."""
        return max(self.players_bets.values(), default=0)

    def is_folded(self, player):
        """Retourne si un joueur s'est couché."""
        return self.players_bets.get(player, None) is None

    async def bet(self, player, amount):
        """Traitement d'une mise."""
        self.players_bets[player] = self.players_bets.get(player, 0) + amount

    async def fold(self, player):
        """Le joueur se couche."""
        self.players_bets[player] = None

    async def display_player_window(self, player):
        """Afficher la fenêtre de jeu pour un joueur humain."""
            # Cette méthode peut afficher des boutons ou d'autres éléments pour un joueur humain.
        pass

    def add_fake_member(self, bot, name: str, id: int):
        """Ajoute un FakeMember à la liste des joueurs."""
        fake_member = FakeMember(bot, name, id)
        self.players.append(fake_member)



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
        return len(self.players) >= 1

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
        cpu_player = self.game.create_cpu_player()
        self.game.add_player(cpu_player)
        self.cpu_count += 1
        total_players = len(self.game.players)
        await interaction.followup.send(
            f"Un CPU a rejoint la partie ! Nombre total de CPU : {self.cpu_count}", ephemeral=False
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
        if not self.game.can_start():
            await interaction.followup.send("La partie ne peut pas être démarrée !", ephemeral=False)
            return
        self.clear_items()
        self.game.start_game()
        self.game.start_betting_round()
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