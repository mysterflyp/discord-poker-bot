import sqlite3
import discord
from discord.ext import commands

DB_PATH = "shops.db"  # Centralisation du chemin de la DB

class DBManager(commands.Cog):
    """Cog gérant les interactions avec la base de données."""

    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        """Méthode appelée automatiquement lors du chargement du Cog."""
        self.create_db();

    def drop_db(self):
        """Drope la table users si elle existe."""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("DROP TABLE IF EXIST users")
                print("✅ Table `users` droppée si existante avec succès.")
        except sqlite3.Error as e:
            print(f"⚠️ Erreur lors de la vérification d'existance/drop de la tale `users` : {e}")

    def create_db(self):
        """Crée la table users si elle n'existe pas."""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute('''
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
                print("✅ Table `users` vérifiée/créée avec succès.")
        except sqlite3.Error as e:
            print(f"⚠️ Erreur lors de la création de la base : {e}")

    # Obtenir la balance (argent) d'un utilisateur
    def user_get_balance(self, user_id):
        """Obtenir la balance (argent) d'un utilisateur"""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT argent FROM users WHERE user_id = ?", (user_id,))
                result = cursor.fetchone()
                if result:
                    return result[0]
                else:
                    print(f"⚠️ Erreur lors de la récupération du user id=`{user_id}`")
                    return None
        except sqlite3.Error as e:
            print(f"Erreur SQLite : {e}")
            return None

    # Ajouter de l'argent à un utilisateur
    def user_add_balance(self, user_id, amount):
        """Ajouter de l'argent à un utilisateur."""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT argent FROM users WHERE user_id = ?", (user_id,))
                result = cursor.fetchone()
                if result:
                    new_balance = result[0] + amount
                    cursor.execute("UPDATE users SET argent = ? WHERE user_id = ?", (new_balance, user_id))
                    conn.commit()
                    return new_balance
                else:
                    print(f"⚠️ Erreur lors de la récupération du user id=`{user_id}`")
                    return None
        except sqlite3.Error as e:
            print(f"Erreur SQLite : {e}")
            return None

    # Reset l'argent d'un utilisateur
    def user_reset_balance(self, user_id):
        """Reset l'argent d'un utilisateur."""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT argent FROM users WHERE user_id = ?", (user_id,))
                result = cursor.fetchone()
                if result:
                    cursor.execute("UPDATE users SET argent = ? WHERE user_id = ?", (0, user_id))
                    conn.commit()
                    return 0
                else:
                    print(f"⚠️ Erreur lors de la récupération du user id=`{user_id}`")
                    return None
        except sqlite3.Error as e:
            print(f"Erreur SQLite : {e}")
            return None

    # Obtenir le niveau d'un utilisateur
    def user_get_niveau(self, user_id):
        """Retourne le niveau d'un utilisateur."""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT niveau FROM users WHERE user_id = ?", (user_id,))
                result = cursor.fetchone()
                if result:
                    return result[0]
                else:
                    print(f"⚠️ Erreur lors de la récupération du user id=`{user_id}`")
                    return None
        except sqlite3.Error as e:
            print(f"Erreur SQLite : {e}")
            return None

    # Ajouter des niveaux à un utilisateur
    def user_add_niveau(self, user_id, amount):
        """Ajoute des niveaux à un utilisateur."""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT niveau FROM users WHERE user_id = ?", (user_id,))
                result = cursor.fetchone()

                if result:
                    new_niveau = result[0] + amount
                    cursor.execute("UPDATE users SET niveau = ? WHERE user_id = ?", (new_niveau, user_id))
                    conn.commit()
                    return new_niveau
                else:
                    print(f"⚠️ Erreur lors de la récupération du user id=`{user_id}`")
                    return None
        except sqlite3.Error as e:
            print(f"Erreur SQLite : {e}")
            return None

    # Reset le niveau d'un utilisateur
    def user_reset_niveau(self, user_id):
        """Reset le niveau d'un utilisateur."""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT niveau FROM users WHERE user_id = ?", (user_id,))
                result = cursor.fetchone()

                if result:
                    new_niveau = 0
                    cursor.execute("UPDATE users SET niveau = ? WHERE user_id = ?", (new_niveau, user_id))
                    conn.commit()
                    return new_niveau
                else:
                    print(f"⚠️ Erreur lors de la récupération du user id=`{user_id}`")
                    return None
        except sqlite3.Error as e:
            print(f"Erreur SQLite : {e}")
            return None

    # Créer un utilisateur s'il n'existe pas
    def user_ensure_exist(self, member: discord.Member):
        """Ajoute un utilisateur dans la base de données s'il n'existe pas."""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (member.id,))
                if cursor.fetchone() is None:
                    roles = ", ".join([role.name for role in member.roles if role.name != "@everyone"])
                    cursor.execute("INSERT INTO users (user_id, username, discriminator, joined_at, roles) VALUES (?, ?, ?, ?, ?)",
                                   (member.id, member.name, member.discriminator, str(member.joined_at), roles))
                    conn.commit()
        except sqlite3.Error as e:
            print(f"Erreur SQLite : {e}")

async def setup(bot):
    """Ajoute le Cog au bot."""
    await bot.add_cog(DBManager(bot))
