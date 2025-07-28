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
                    argent INTEGER DEFAULT 500,
                    niveau INTEGER DEFAULT 0,
                    discriminator TEXT,
                    joined_at TEXT,
                    roles TEXT
                )
                ''')
                
                # Table des items
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        price INTEGER NOT NULL
                    )
                ''')

                # Table des achats
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS purchases (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        item_id INTEGER,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                

                # Nettoyer d'abord tous les doublons existants
                cursor.execute("""
                    DELETE FROM items WHERE id NOT IN (
                        SELECT MIN(id) FROM items GROUP BY name, price
                    )
                """)
                
                # Ajouter les items par défaut seulement s'ils n'existent pas déjà
                default_items = [
                    ("Roulette russe", 200),
                    ("VIP", 500000)
                ]
                
                for item_name, item_price in default_items:
                    cursor.execute("SELECT COUNT(*) FROM items WHERE name = ? AND price = ?", (item_name, item_price))
                    if cursor.fetchone()[0] == 0:
                        cursor.execute("INSERT INTO items (name, price) VALUES (?, ?)", (item_name, item_price))

                conn.commit()
                print("Base de données initialisée avec succès.")
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

    # Créer un utilisateur simple
    def user_create(self, user_id):
        """Crée un utilisateur avec les valeurs par défaut."""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
                if cursor.fetchone() is None:
                    cursor.execute("INSERT INTO users (user_id, username, argent, niveau) VALUES (?, ?, ?, ?)",
                                   (user_id, f"User_{user_id}", 500, 0))
                    conn.commit()
                    print(f"✅ Utilisateur {user_id} créé avec 500 jetons.")
        except sqlite3.Error as e:
            print(f"Erreur SQLite : {e}")

    # Méthodes pour la boutique
    def get_all_items(self):
        """Retourne tous les articles de la boutique."""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, name, price FROM items")
                return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Erreur SQLite : {e}")
            return []

    def get_item(self, item_id):
        """Retourne les informations d'un article."""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name, price FROM items WHERE id = ?", (item_id,))
                return cursor.fetchone()
        except sqlite3.Error as e:
            print(f"Erreur SQLite : {e}")
            return None

    def add_item(self, name, price):
        """Ajoute un article à la boutique."""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO items (name, price) VALUES (?, ?)", (name, price))
                conn.commit()
                return True
        except sqlite3.Error as e:
            print(f"Erreur SQLite : {e}")
            return False

    def remove_item(self, item_id):
        """Supprime un article de la boutique."""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Erreur SQLite : {e}")
            return False

    def purchase_item(self, user_id, item_id, price):
        """Effectue l'achat d'un article."""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                # Débiter l'argent de l'utilisateur
                cursor.execute("UPDATE users SET argent = argent - ? WHERE user_id = ?", (price, user_id))
                # Enregistrer l'achat
                cursor.execute("INSERT INTO purchases (user_id, item_id) VALUES (?, ?)", (user_id, item_id))
                conn.commit()
                return True
        except sqlite3.Error as e:
            print(f"Erreur SQLite : {e}")
            return False

    def get_user_purchases(self, user_id):
        """Retourne l'historique des achats d'un utilisateur."""
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT items.name, purchases.timestamp 
                    FROM purchases 
                    JOIN items ON purchases.item_id = items.id 
                    WHERE purchases.user_id = ?
                    ORDER BY purchases.timestamp DESC
                """, (user_id,))
                return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Erreur SQLite : {e}")
            return []

    

async def setup(bot):
    """Ajoute le Cog au bot."""
    await bot.add_cog(DBManager(bot))
