
import discord
from discord.ext import commands
from discord.ui import View, Select, Button, Modal, TextInput
import sqlite3

class CommentModal(Modal):
    """Modal pour ajouter un commentaire."""
    
    def __init__(self, db_manager, item_id, item_name):
        super().__init__(title=f"Commenter: {item_name}")
        self.db = db_manager
        self.item_id = item_id
        self.item_name = item_name
        
        self.comment_input = TextInput(
            label="Votre commentaire",
            placeholder="Écrivez votre commentaire ici...",
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=True
        )
        self.add_item(self.comment_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        comment_text = self.comment_input.value.strip()
        
        if not comment_text:
            await interaction.response.send_message("❌ Le commentaire ne peut pas être vide.", ephemeral=True)
            return
        
        success = self.db.add_comment(
            interaction.user.id, 
            interaction.user.display_name, 
            self.item_id, 
            comment_text
        )
        
        if success:
            await interaction.response.send_message(f"✅ Commentaire ajouté à l'article **{self.item_name}**!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Erreur lors de l'ajout du commentaire.", ephemeral=True)

class ShopView(View):
    """Vue pour afficher et gérer la boutique."""
    
    def __init__(self, db_manager):
        super().__init__(timeout=60)
        self.db = db_manager
    
    @discord.ui.button(label="🛒 Voir les articles", style=discord.ButtonStyle.primary)
    async def view_items(self, interaction: discord.Interaction, button: Button):
        try:
            items = self.db.get_all_items()
            if not items:
                await interaction.response.send_message("❌ Aucun article disponible dans la boutique.", ephemeral=True)
                return
            
            # Limiter à 20 articles pour respecter les limites Discord (25 max)
            items_display = items[:20]
            
            embed = discord.Embed(title="🏪 Boutique", color=discord.Color.blue())
            for item_id, name, price in items_display:
                embed.add_field(name=f"{name}", value=f"Prix: {price} jetons", inline=False)
            
            if len(items) > 20:
                embed.set_footer(text=f"Affichage de 20 articles sur {len(items)} disponibles")
            
            await interaction.response.send_message(embed=embed, view=PurchaseView(self.db, items_display), ephemeral=True)
        except Exception as e:
            print(f"Erreur lors de l'affichage des articles: {e}")
            await interaction.response.send_message("❌ Erreur lors du chargement de la boutique.", ephemeral=True)
    
    @discord.ui.button(label="💰 Mon argent", style=discord.ButtonStyle.secondary)
    async def check_balance(self, interaction: discord.Interaction, button: Button):
        try:
            user_id = interaction.user.id
            # S'assurer que l'utilisateur existe
            if self.db.user_get_balance(user_id) is None:
                self.db.user_create(user_id)
            
            balance = self.db.user_get_balance(user_id)
            await interaction.response.send_message(f"💰 Vous avez **{balance}** jetons.", ephemeral=True)
        except Exception as e:
            print(f"Erreur lors de la vérification du solde: {e}")
            await interaction.response.send_message("❌ Erreur lors de la vérification du solde.", ephemeral=True)
    
    @discord.ui.button(label="💬 Voir commentaires", style=discord.ButtonStyle.secondary)
    async def view_comments(self, interaction: discord.Interaction, button: Button):
        try:
            items = self.db.get_all_items()
            if not items:
                await interaction.response.send_message("❌ Aucun article disponible.", ephemeral=True)
                return
            
            # Créer une vue pour sélectionner l'article dont voir les commentaires
            view = CommentSelectionView(self.db, items[:20])
            await interaction.response.send_message("📝 Sélectionnez un article pour voir ses commentaires:", view=view, ephemeral=True)
        except Exception as e:
            print(f"Erreur lors de l'affichage des commentaires: {e}")
            await interaction.response.send_message("❌ Erreur lors du chargement des commentaires.", ephemeral=True)tyle.secondary)
    async def check_balance(self, interaction: discord.Interaction, button: Button):
        balance = self.db.user_get_balance(interaction.user.id)
        if balance is None:
            self.db.user_create(interaction.user.id)
            balance = 100  # Valeur par défaut après création
        
        await interaction.response.send_message(f"💰 Vous avez **{balance}** jetons.", ephemeral=True)
    
    @discord.ui.button(label="📦 Mes achats", style=discord.ButtonStyle.success)
    async def my_purchases(self, interaction: discord.Interaction, button: Button):
        purchases = self.db.get_user_purchases(interaction.user.id)
        if not purchases:
            await interaction.response.send_message("📦 Vous n'avez encore rien acheté.", ephemeral=True)
            return
        
        embed = discord.Embed(title="📦 Mes achats", color=discord.Color.green())
        for item_name, timestamp in purchases:
            embed.add_field(name=item_name, value=f"Acheté le: {timestamp}", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class CommentSelectionView(View):
    """Vue pour sélectionner un article pour voir/ajouter des commentaires."""
    
    def __init__(self, db_manager, items):
        super().__init__(timeout=60)
        self.db = db_manager
        self.items = items
        
        # Menu déroulant pour sélectionner l'article
        options = []
        for item_id, name, price in items:
            display_name = name[:100] if len(name) > 100 else name
            options.append(discord.SelectOption(
                label=display_name,
                description=f"Prix: {price} jetons",
                value=str(item_id)
            ))
        
        if options:
            self.select_menu = Select(placeholder="Choisissez un article...", options=options)
            self.select_menu.callback = self.article_selected
            self.add_item(self.select_menu)
    
    async def article_selected(self, interaction: discord.Interaction):
        item_id = int(self.select_menu.values[0])
        
        # Trouver l'article sélectionné
        selected_item = None
        for item in self.items:
            if item[0] == item_id:
                selected_item = item
                break
        
        if not selected_item:
            await interaction.response.send_message("❌ Article introuvable.", ephemeral=True)
            return
        
        item_name = selected_item[1]
        comments = self.db.get_item_comments(item_id)
        
        embed = discord.Embed(
            title=f"💬 Commentaires: {item_name}",
            color=discord.Color.blue()
        )
        
        if comments:
            for username, comment_text, timestamp in comments[:10]:  # Limiter à 10 commentaires
                embed.add_field(
                    name=f"👤 {username}",
                    value=f"{comment_text}\n*{timestamp}*",
                    inline=False
                )
            if len(comments) > 10:
                embed.set_footer(text=f"Affichage de 10 commentaires sur {len(comments)}")
        else:
            embed.description = "Aucun commentaire pour cet article."
        
        # Créer une vue avec bouton pour ajouter un commentaire
        view = CommentActionView(self.db, item_id, item_name)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class CommentActionView(View):
    """Vue avec actions pour les commentaires."""
    
    def __init__(self, db_manager, item_id, item_name):
        super().__init__(timeout=60)
        self.db = db_manager
        self.item_id = item_id
        self.item_name = item_name
    
    @discord.ui.button(label="➕ Ajouter commentaire", style=discord.ButtonStyle.green)
    async def add_comment(self, interaction: discord.Interaction, button: Button):
        modal = CommentModal(self.db, self.item_id, self.item_name)
        await interaction.response.send_modal(modal)

class PurchaseView(View):
    """Vue pour acheter des articles."""
    
    def __init__(self, db_manager, items):
        super().__init__(timeout=60)
        self.db = db_manager
        self.items = items
        
        # Créer un menu déroulant avec les articles (limité à 20 pour Discord)
        options = []
        items_limited = items[:20]  # Discord limite à 25 options max
        for item_id, name, price in items_limited:
            # Limiter la longueur du nom à 100 caractères (limite Discord)
            display_name = name[:100] if len(name) > 100 else name
            options.append(discord.SelectOption(
                label=display_name,
                description=f"Prix: {price} jetons",
                value=str(item_id)
            ))
        
        if options:
            self.add_item(ItemSelect(self.db, options))

class ItemSelect(Select):
    """Menu déroulant pour sélectionner un article à acheter."""
    
    def __init__(self, db_manager, options):
        super().__init__(placeholder="Choisissez un article à acheter...", options=options)
        self.db = db_manager
    
    async def callback(self, interaction: discord.Interaction):
        item_id = int(self.values[0])
        user_id = interaction.user.id
        
        # Vérifier si l'utilisateur existe
        if self.db.user_get_balance(user_id) is None:
            self.db.user_create(user_id)
        
        # Obtenir les informations de l'article
        item_info = self.db.get_item(item_id)
        if not item_info:
            await interaction.response.send_message("❌ Article introuvable.", ephemeral=True)
            return
        
        item_name, item_price = item_info
        user_balance = self.db.user_get_balance(user_id)
        
        # Vérifier si l'utilisateur a assez d'argent
        if user_balance < item_price:
            await interaction.response.send_message(
                f"❌ Vous n'avez pas assez de jetons!\n"
                f"Prix: {item_price} jetons\n"
                f"Votre solde: {user_balance} jetons",
                ephemeral=True
            )
            return
        
        # Effectuer l'achat
        success = self.db.purchase_item(user_id, item_id, item_price)
        if success:
            new_balance = user_balance - item_price
            await interaction.response.send_message(
                f"✅ Achat réussi!\n"
                f"Vous avez acheté: **{item_name}**\n"
                f"Prix: {item_price} jetons\n"
                f"Nouveau solde: {new_balance} jetons",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("❌ Erreur lors de l'achat.", ephemeral=True)

class Boutique(commands.Cog):
    """Cog pour la gestion de la boutique."""
    
    def __init__(self, bot):
        self.bot = bot
        self._db = None
    
    async def cog_load(self):
        """Chargement du cog."""
        self._db = self.bot.get_cog("DBManager")
        if not self._db:
            raise RuntimeError("❌ DBManager doit être chargé avant la Boutique")
    
    @commands.command(name="boutique", aliases=["shop"])
    async def boutique(self, ctx):
        """Ouvre la boutique."""
        if not self._db:
            await ctx.send("❌ La boutique n'est pas disponible.")
            return
        
        embed = discord.Embed(
            title="🏪 Bienvenue dans la boutique!",
            description="Utilisez les boutons ci-dessous pour naviguer.",
            color=discord.Color.gold()
        )
        
        view = ShopView(self._db)
        await ctx.send(embed=embed, view=view)
    
    @commands.command(name="add_item")
    @commands.has_permissions(administrator=True)
    async def add_item(self, ctx, price: int, *, name: str):
        """Ajoute un article à la boutique. Usage: $add_item <prix> <nom>"""
        if not self._db:
            await ctx.send("❌ La boutique n'est pas disponible.")
            return
        
        success = self._db.add_item(name, price)
        if success:
            await ctx.send(f"✅ Article **{name}** ajouté à la boutique pour {price} jetons.")
        else:
            await ctx.send("❌ Erreur lors de l'ajout de l'article.")
    
    @commands.command(name="remove_item")
    @commands.has_permissions(administrator=True)
    async def remove_item(self, ctx, item_id: int):
        """Supprime un article de la boutique. Usage: $remove_item <id>"""
        if not self._db:
            await ctx.send("❌ La boutique n'est pas disponible.")
            return
        
        success = self._db.remove_item(item_id)
        if success:
            await ctx.send(f"✅ Article ID {item_id} supprimé de la boutique.")
        else:
            await ctx.send("❌ Erreur lors de la suppression de l'article.")
    
    @commands.command(name="list_items")
    @commands.has_permissions(administrator=True)
    async def list_items(self, ctx):
        """Liste tous les articles de la boutique avec leurs IDs."""
        if not self._db:
            await ctx.send("❌ La boutique n'est pas disponible.")
            return
        
        items = self._db.get_all_items()
        if not items:
            await ctx.send("❌ Aucun article dans la boutique.")
            return
        
        embed = discord.Embed(title="📋 Liste des articles", color=discord.Color.blue())
        for item_id, name, price in items:
            embed.add_field(name=f"ID: {item_id}", value=f"{name} - {price} jetons", inline=False)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Boutique(bot))
