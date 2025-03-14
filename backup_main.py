import os
import discord
from discord.ext import commands, tasks
from discord.ui import View, Select
import asyncio
import sqlite3
import aiosqlite
import json
import random
from collections import Counter

# Définir les intentions du bot
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.members = True
bot = commands.Bot(command_prefix="$", intents=intents)
client = discord.Client(intents=discord.Intents.all())

# Constantes de rôle
ROLE_ID = 1279001249022476342  # Role en vocal
ROLE_ID2 = 1271165198392365207  # Role global


def create_shops_db():
    conn = sqlite3.connect('shops.db')
    c = conn.cursor()
   # c.execute("Drop table if exists users")
    # Création de la table users
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT NOT NULL,
        argent INTEGER DEFAULT 0,
        niveau INTEGER DEFAULT 0,
        discriminator TEXT,
        joined_at TEXT,
        roles TEXT
    )
    ''')
    #c.execute("Drop table if exists bets")
    c.execute('''
    CREATE TABLE IF NOT EXISTS bets (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        bet_amount INTEGER,
        game_id INTEGER
    )
    ''')

    # Liste des tables à vérifier
    tables_to_check = ['users', 'bets']
    c.execute("SELECT name FROM sqlite_master WHERE type='table';")
    existing_tables = [row[0] for row in c.fetchall()]
    for table in tables_to_check:
        if table in existing_tables:
            print(f"La table '{table}' existe.")
        else:
            print(f"La table '{table}' n'a pas été créée.")
    conn.commit()
    conn.close()

# Ajouter de l'argent à un utilisateur
def add_balance(user_id, amount):
    conn = sqlite3.connect('shops.db')
    c = conn.cursor()
    c.execute('SELECT argent FROM users WHERE user_id = ?', (user_id, ))
    result = c.fetchone()
    if result:
        new_balance = result[0] + amount
        c.execute('UPDATE users SET argent = ? WHERE user_id = ?',
                  (new_balance, user_id))
    conn.commit()
    conn.close()


# Ajouter des niveaux à un utilisateur
def add_niveau(user_id, amount):
    conn = sqlite3.connect('shops.db')
    c = conn.cursor()
    c.execute('SELECT niveau FROM users WHERE user_id = ?', (user_id, ))
    result = c.fetchone()

    if result:
        new_balance = result[0] + amount
        c.execute('UPDATE users SET niveau = ? WHERE user_id = ?',
                  (new_balance, user_id))
    conn.commit()
    conn.close()


# Obtenir les niveaux d'un utilisateur
def get_niveau(user_id):
    conn = sqlite3.connect('shops.db')
    c = conn.cursor()
    c.execute('SELECT niveau FROM users WHERE user_id = ?', (user_id, ))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def create_user(member: discord.Member):
    conn = sqlite3.connect("shops.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (member.id,))
    if cursor.fetchone() is None:
        roles = ", ".join([role.name for role in member.roles if role.name != "@everyone"])
        cursor.execute("INSERT INTO users (user_id, username, discriminator, joined_at, roles) VALUES (?, ?, ?, ?, ?)",
                       (member.id, member.name, member.discriminator, str(member.joined_at), roles))
        conn.commit()
        print(f"Utilisateur {member.name} ajouté à la base de données.")
    conn.close()



# Lancer le bot lorsque l'on est prêt
@bot.event
async def on_ready():
    create_shops_db()
    give_money_periodically.start()
    give_level_periodically.start()
    print(f"Connecté en tant que {bot.user}")
    for guild in bot.guilds:
        for member in guild.members:
            create_user(member)


# Lancer un envoi périodique d'argent
# FIXME : Il faut verifier que les users existent sinon les get/add_balance vont crasher
@tasks.loop(seconds=10)
async def give_money_periodically():
    for guild in bot.guilds:
        for member in guild.members:
            role = discord.utils.get(member.roles, id=ROLE_ID)
            if role:
                current_balance = get_balance(member.id)
                add_balance(member.id, 25)
                print(
                    f"{member.name} a gagné 25 unités de Jetons (total: {current_balance + 25})"
                )


# Lancer un envoi périodique de niveaux
# FIXME : Il faut verifier que les users existent sinon les get/add_balance vont crasher
@tasks.loop(seconds=10)                
async def give_level_periodically():
    for guild in bot.guilds:
        for member in guild.members:
            role = discord.utils.get(member.roles, id=ROLE_ID)
            if role:
                current_level = get_niveau(member.id)
                add_niveau(member.id, 0.25)
                print(
                    f"{member.name} a gagné 0,25 d'expérience (total: {current_level + 0.25})"
                )


# Commande pour gérer les gains d'argent et de niveau via messages
# FIXME : Il faut verifier que les users existent sinon les get/add_balance vont crasher
@bot.event
async def on_message(message):
    if message.content.startswith(bot.command_prefix):
        amount = 0
        level = 0
    elif message.type == discord.MessageType.default:
        amount = 5
        level = 0.25
        user_id = message.author.id
        add_balance(user_id, amount)
        add_niveau(user_id, level)
    await bot.process_commands(message)


# Commande pour afficher le solde
# FIXME : Il faut verifier que les users existent sinon les get/add_balance vont crasher
@bot.command()
async def solde(ctx, membre: discord.Member = None):
    if membre is None:
        membre = ctx.author

    argent = get_balance(membre.id)
    await ctx.send(f"{membre.mention} a {argent}Jetons.")


# Commande pour afficher les niveaux
# FIXME : Il faut verifier que les users existent sinon les get/add_balance vont crasher
@bot.command()
async def niveau(ctx, membre: discord.Member = None):
    if membre is None:
        membre = ctx.author

    niveau = get_niveau(membre.id)
    await ctx.send(f"{membre.mention} a {niveau} % d'expérience.")


# Commande pour payer une personne
# FIXME : Il faut verifier que les users existent sinon les get/add_balance vont crasher
@bot.command()
async def payer(ctx, membre: discord.Member, montant: int):
    user_balance = get_balance(ctx.author.id)
    if user_balance < montant:
        await ctx.send(
            f"{ctx.author.mention}, vous n'avez pas assez d'argent pour effectuer ce paiement."
        )
        return
    add_balance(ctx.author.id, -montant)
    add_balance(membre.id, montant)
    await ctx.send(
        f"{ctx.author.mention} a payé {montant}Jetons à {membre.mention}. Nouveau solde: {get_balance(ctx.author.id)}Jetons"
    )


# Commande pour donner de l'argent à un autre utilisateur (réservée aux admins)
# FIXME : Il faut verifier que les users existent sinon les get/add_balance vont crasher
@bot.command()
@commands.has_permissions(administrator=True)
async def donner(ctx, membre: discord.Member, montant: int):
    old_balance = get_balance(membre.id)
    add_balance(membre.id, montant)
    new_balance = get_balance(membre.id)

    await ctx.send(
        f"{membre.mention} a reçu {montant}Jetons ! Ancien solde {old_balance} Nouveau solde: {new_balance}Jetons."
    )


# Commande pour remettre à zéro l'expérience (niveau) d'un utilisateur
# FIXME : il faut differencier le fait que le user n'existe pas du niveau 0
@bot.command()
@commands.has_permissions(administrator=True)
async def reset_niveau(ctx, membre: discord.Member):
    conn = sqlite3.connect('shops.db')
    c = conn.cursor()
    c.execute('SELECT niveau FROM users WHERE user_id = ?', (membre.id, ))
    result = c.fetchone()
    if result:
        c.execute('UPDATE users SET niveau = ? WHERE user_id = ?',
                  (0, membre.id))
        conn.commit()
        await ctx.send(f"L'expérience de {membre.mention} a été remise à zéro."
                       )
    else:
        await ctx.send(f"{membre.mention} n'a pas d'expérience enregistrée.")

    conn.close()


# Commande pour remettre à zéro l'argent d'un utilisateur
# FIXME : il faut differencier le fait que le user n'existe pas du montant 0
@bot.command()
@commands.has_permissions(administrator=True)
async def reset_balance(ctx, membre: discord.Member):
    conn = sqlite3.connect('shops.db')
    c = conn.cursor()
    c.execute('SELECT argent FROM users WHERE user_id = ?', (membre.id, ))
    result = c.fetchone()
    if result:
        c.execute('UPDATE users SET argent = ? WHERE user_id = ?',
                  (0, membre.id))
        conn.commit()
        await ctx.send(f"L'argent de {membre.mention} a été remise à zéro.")
    else:
        await ctx.send(f"{membre.mention} n'a pas d'argent enregistrée.")

    conn.close()


# Gestion des erreurs pour les commandes nécessitant des permissions administratives
@donner.error
async def donner_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            "Vous n'avez pas la permission d'utiliser cette commande.")


# Gestion des erreurs pour la commande de remise à zéro level
# FIXME : Dans le else utiliser error.toStr....
@reset_niveau.error
async def reset_niveau_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Tu n'as pas la permission d'utiliser cette commande.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            "Tu dois spécifier un membre pour réinitialiser son expérience.")
    else:
        await ctx.send("Une erreur est survenue.")


# Gestion des erreurs pour la commande de remise à zéro argent
@reset_balance.error
async def reset_balance_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Tu n'as pas la permission d'utiliser cette commande.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            "Tu dois spécifier un membre pour réinitialiser son argent.")
    else:
        await ctx.send("Une erreur est survenue.")

# Commande pour bannir un utilisateur par ID
@bot.command()
async def ban_id(ctx,
                 user_id: int,
                 *,
                 reason: str = "Aucune raison spécifiée"):
    if not ctx.author.guild_permissions.ban_members:
        await ctx.send("Tu n'as pas la permission de bannir des membres.")
        return
    user = await bot.fetch_user(user_id)
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
@bot.command()
async def userinfo(ctx, user: discord.User):
    embed = discord.Embed(
        title=f"Infos de {user.name}",
        description=f"Voici les informations sur {user.name}",
        color=discord.Color.blue())
    embed.add_field(name="Nom d'utilisateur", value=user.name)
    embed.add_field(name="ID", value=user.id)
    embed.set_thumbnail(url=user.avatar.url)
    await ctx.send(embed=embed)


@bot.command()
async def aide(ctx):
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

############################################################################################################################################

class MyView(discord.ui.View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label="Suivre", style=discord.ButtonStyle.success)
    async def follow_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"{player.name} as suivis la mise est maintenant de ✅")
        self.clear_items()
        await interaction.message.edit(view=self)

    @discord.ui.button(label="Relancer", style=discord.ButtonStyle.primary)
    async def retry_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"{player.name} as relancé de 🔄")
        self.clear_items()
        await interaction.message.edit(view=self)

    @discord.ui.button(label="Coucher", style=discord.ButtonStyle.danger)
    async def fold_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"c'est coucher ❌")
        self.clear_items()
        await interaction.message.edit(view=self)

@bot.command()
async def start(ctx):
    """Commande pour envoyer un message avec un bouton."""
    view = MyView()
    await ctx.send("Commencer le poker:", view=view)
    ############################################################################################################################################


my_secret = os.environ['TOKEN_BOT']
bot.run(my_secret)
