def get_mises(user_id):
    try:
        conn = sqlite3.connect('shops.db')
        cursor = conn.cursor()
        cursor.execute('SELECT bet_amount FROM bets WHERE user_id=?', (user_id, bet_amount,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return result[0]
        else:
            return 0  # Solde initial si le joueur n'est pas trouvé dans la base
    except sqlite3.Error as e:
        print(f"Erreur lors de la récupération du solde pour l'utilisateur {user_id}: {e}")
        return 0


def get_balance(user_id):
    try:
        conn = sqlite3.connect('shops.db')
        cursor = conn.cursor()
        cursor.execute('SELECT argent FROM users WHERE user_id=?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return result[0]
        else:
            return 0  # Solde initial si le joueur n'est pas trouvé dans la base
    except sqlite3.Error as e:
        print(f"Erreur lors de la récupération du solde pour l'utilisateur {user_id}: {e}")
        return 0

def update_balance(user_id, amount):
    try:
        conn = sqlite3.connect('shops.db')
        cursor = conn.cursor()
        cursor.execute('SELECT argent FROM users WHERE user_id=?', (user_id, ))
        result = cursor.fetchone()
        if result:
            new_balance = result[0] + amount
            cursor.execute('UPDATE users SET argent=? WHERE user_id=?', (new_balance, user_id))
            conn.commit()
    except sqlite3.Error as e:
        print(f"Erreur lors de la mise à jour du solde pour l'utilisateur {user_id}: {e}")
    finally:
        conn.close()

def record_bet(user_id, bet_amount, game_id):
    conn = sqlite3.connect('shops.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO bets (user_id, bet_amount, game_id) VALUES (?, ?, ?)', 
                   (user_id, bet_amount, game_id))
    conn.commit()
    conn.close()

# Define the classes for the poker game
class Card:
    suits = ['♠', '♥', '♦', '♣']
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

class PokerGame:
    def __init__(self, bot):
        self.bot = bot
        self.players = []  # List of players
        self.deck = Deck()
        self.community_cards = []  # Community cards
        self.pot = 0  # The pot
        self.bets = {}  # Dictionary to track bets of players
        self.bet_tour = 0  # Current bet tour
        self.player_chips = {}  # Player's chips
        self.folded_players = []  # List of players who folded
        self.round_over = False  # End of round flag
        self.game_id = random.randint(1000, 9999)  # Unique game ID
        self.winners = []

    def add_player(self, player):
        if player not in self.players:
            self.players.append(player)
            create_user(player)
            argent = get_balance(player.name)  # Get the player's balance from DB
            self.player_chips[player] = argent
            self.bets[player] = 0  # Initial bet of 0 for each player

    def deal_cards(self):
        self.player_hands = {player: [self.deck.draw(), self.deck.draw()] for player in self.players if player not in self.folded_players}

    def reset_bets(self):
        self.bets = {player: 0 for player in self.players}

    def collect_bets(self):
        # Collecting players' bets into the pot
        for player, bet in self.bets.items():
            if player not in self.folded_players:
                self.pot += bet
                self.player_chips[player] -= bet
                self.bets[player] = 0
                update_balance(player.id, -bet)  # Update the player's balance

    def next_card(self):

        self.collect_bets()
        self.bet_tour = 0
        if len(self.community_cards) == 0:
            self.flop()
            return (f"Le flop a été révélé: {self.show_community_cards()}")
        elif len(self.community_cards) == 3:
            self.turn()
            return (f"Le turn a été révélé: {self.show_community_cards()}")
        elif len(self.community_cards) == 4:
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
        return self.bets.get(player, 0)

    def start_game(self):
        self.deal_cards()
        self.bet_tour = 20 
        return self.show_community_cards(), self.show_player_hands()

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
        winners = []
        for player, rank in hand_rankings.items():
            if best_rank is None or rank > best_rank:
                best_rank = rank
                winners = [player]
            elif rank == best_rank:
                winners.append(player)
        return winners

    def end_game(self):
        winners = self.determine_winner()
        gain = self.pot / len(winners)
        for winner in winners:
            update_balance(winner.id, gain)
        self.winners = winners

    def reset_game(self):
        self.players.clear()
        self.folded_players.clear()
        self.pot = 0
        self.community_cards.clear()
        self.bets.clear()
        self.player_chips.clear()
        self.deck = Deck()  # Crée un nouveau deck pour la prochaine partie
        self.game_id = random.randint(1000, 9999)  # Nouveau game_id pour la prochaine partie
        self.winners = []  # Liste vide de gagnants
        self.round_over = False  # Réinitialiser l'état de la partie

# Define your bot commands here
@bot.command(name='start_poker')
async def start_poker(ctx):
    if hasattr(bot, 'game') and bot.game is not None:
        await ctx.send("Un jeu de poker est déjà en cours!")
        return

    # Initialize a new poker game
    bot.game = PokerGame(bot)
    bot.game.add_player(ctx.author)
    await ctx.send(f"{ctx.author.name} a rejoint la table!")


@bot.command(name="join_poker")
async def join_poker(ctx):
    if ctx.author in bot.game.players:
        await ctx.send(f"{ctx.author.name}, vous avez déjà rejoint la partie !")
        return

    bot.game.add_player(ctx.author)
    message = f"{ctx.author.name} a rejoint la partie !"

    if len(bot.game.players) >= 1:
        message += "La partie peut maintenant commencer ! Utilisez la commande $start pour démarrer."
    else:
        message += f"Il y a actuellement {len(bot.game.players)} joueur(s) dans la partie. Plus de joueurs sont nécessaires."
    await ctx.send(message)


@bot.command(name="start")
async def start(ctx):
    if ctx.author != bot.game.players[0]:  # Only the first player can start
        await ctx.send("Seul le premier joueur peut démarrer la partie.")
        return

    if len(bot.game.players) < 1:
        await ctx.send("Il faut au moins 2 joueurs pour démarrer la partie.")
        return

    await ctx.send("La partie commence maintenant !")
    community_cards, player_hands = bot.game.start_game()
    for player in bot.game.players:
        hand = player_hands.get(player, [])
        bot.game.start_betting_round()
        await ctx.send ("La phase de mise commence! Chaque joueur peut miser, suivre, relancer ou se coucher")
        await player.send(f"Main de {player.name}: {hand}")

# Commande pour miser, suivre, relancer
@bot.command(name='miser')
async def bet(ctx, amount: int):
    if not hasattr(bot, 'game') or bot.game is None:
        await ctx.send("Aucun jeu n'est en cours!")
        return

    if ctx.author not in bot.game.players:
        await ctx.send("Vous n'êtes pas dans cette partie!")
        return

    if ctx.author in bot.game.folded_players:
        await ctx.send("Vous vous êtes déjà couché!")
        return

    if amount <= 0:
        await ctx.send("La mise doit être supérieure à zéro.")
        return

    # Le montant relatif c'est "coller" + la relance
    amount_relative = amount + bot.game.bet_tour

    # Maintenant, à combien cela revient-il par rapport a son bet actuel
    bet_relatif = amount_relative - bot.game.bets[ctx.author]

    # On verifie qu'il a assez
    # FIXME : ne pas utiliser les get_balance pais les game.player.chips
    if get_balance(ctx.author.id) < bet_relatif:
        await ctx.send(f"Vous n'avez pas assez de jetons. Vous avez {get_balance(ctx.author.id)} jetons.")
        return
#Mettre un timer de 20secondes qui dans le cas ou le joueur n'a pas misé, il se couche et le tour passe au joueur suivant
    # on ajoute le montant relatif au bet tour
    bot.game.bet_tour += amount_relative

    # on affecte le bet tour au bet du joueur (puis que c'est)
    bot.game.bets[ctx.author] = bot.game.bet_tour
    await ctx.send(f"{ctx.author.name} a misé {amount} jetons.")

# Commande pour se coucher
@bot.command(name='coucher')
async def fold(ctx):
    if not hasattr(bot, 'game') or bot.game is None:
        await ctx.send("Aucun jeu n'est en cours!")
        return

    if ctx.author not in bot.game.players:
        await ctx.send("Vous n'êtes pas dans cette partie!")
        return

    bot.game.folded_players.append(ctx.author)
    await ctx.send(f"{ctx.author.name} s'est couché.")


# Commande pour quitter la partie
@bot.command(name='partir')
async def leave_poker(ctx):
    if not hasattr(bot, 'game') or bot.game is None:
        await ctx.send("Aucun jeu n'est en cours!")
        return

    if ctx.author in bot.game.players:
        bot.game.players.remove(ctx.author)
        bot.game.player_chips[ctx.author] = 0  # Réinitialiser les crédits
        await ctx.send(f"{ctx.author.name} a quitté la partie.")
    else:
        await ctx.send("Vous n'êtes pas dans cette partie!")


# Commande pour passer à la phase suivante (flop, turn, river)
@bot.command(name='check')
async def check(ctx):

    if not hasattr(bot, 'game') or bot.game is None:
        await ctx.send("Aucun jeu n'est en cours!")
        return
    if ctx.author not in bot.game.players:
        await ctx.send("Vous n'êtes pas dans cette partie!")
        return
    if len(bot.game.winners) > 0:
        await ctx.send("la partie est terminée!")
        return

    # Vérifier si la mise du joueur est bien celle du maximum du tour, sinon l'appliquer
    playerbet = bot.game.bets.get(ctx.author, 0)
    if playerbet < bot.game.bet_tour:
        difference = bot.game.bet_tour - playerbet
        bot.game.bets[ctx.author] = bot.game.bet_tour
        bot.game.player_chips[ctx.author] -= difference
        await ctx.send(f"{ctx.author.name} a complété sa mise avec {difference} jetons, mise totale: {bot.game.bet_tour}.")
    else:
        return

    ret = bot.game.next_card()
    if ret: 
        await ctx.send(ret)
    else :
        bot.game.end_game()
        await ctx.send(f"Le jeu est terminé! Le gagnant est: {', '.join([winner.name for winner in bot.game.winners])}. Le pot de {bot.game.pot} jetons a été distribué.") 
        bot.game.reset_game()
        bot.game = None

@bot.command(name='mises')
async def get_mises(ctx):
    # Vérifier si un jeu est en cours
    if not hasattr(bot, 'game') or bot.game is None:
        await ctx.send("Aucun jeu n'est en cours!")
        return
    else:    
        await ctx.send(f"Mise actuelle du tour : {bot.game.bet_tour}")
        for player in bot.game.players:
            await ctx.send(f"Mise de {player.name}: {bot.game.bets[player]} jetons.")

@bot.command(name='pot')
async def get_pot(ctx):
    # Vérifier si un jeu est en cours
    if not hasattr(bot, 'game') or bot.game is None:
        await ctx.send("Aucun jeu n'est en cours!")
        return
    else:    
        await ctx.send(f"Mises actuelles : {bot.game.pot}")