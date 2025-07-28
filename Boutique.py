import discord
from discord.ext import commands
from discord.ui import View, Select, Button
import sqlite3

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
            for item_id, name, price, description in items_display:
                desc_text = f"Prix: {price} jetons"
                if description:
                    desc_text += f"\n📝 {description}"
                embed.add_field(name=f"{name}", value=desc_text, inline=False)

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

class PurchaseView(View):
    """Vue pour acheter des articles."""

    def __init__(self, db_manager, items):
        super().__init__(timeout=60)
        self.db = db_manager
        self.items = items

        # Créer un menu déroulant avec les articles (limité à 20 pour Discord)
        options = []
        items_limited = items[:20]  # Discord limite à 25 options max
        for item_id, name, price, description in items_limited:
            # Limiter la longueur du nom à 100 caractères (limite Discord)
            display_name = name[:100] if len(name) > 100 else name
            # Limiter la description à 100 caractères pour Discord
            desc_text = f"Prix: {price} jetons"
            if description:
                short_desc = description[:50] + "..." if len(description) > 50 else description
                desc_text = f"{short_desc} - {price} jetons"
            options.append(discord.SelectOption(
                label=display_name,
                description=desc_text[:100],  # Discord limite à 100 caractères
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

        item_name, item_price, item_description = item_info
        user_balance = self.db.user_get_balance(user_id)

        # Vérifier si l'utilisateur a assez d'argent
        if user_balance < item_price:
            desc_text = f"\n📝 {item_description}" if item_description else ""
            await interaction.response.send_message(
                f"❌ Vous n'avez pas assez de jetons!\n"
                f"**{item_name}**{desc_text}\n"
                f"Prix: {item_price} jetons\n"
                f"Votre solde: {user_balance} jetons",
                ephemeral=True
            )
            return

        # Effectuer l'achat
        success = self.db.purchase_item(user_id, item_id, item_price)
        if success:
            new_balance = user_balance - item_price
            desc_text = f"\n📝 {item_description}" if item_description else ""
            await interaction.response.send_message(
                f"✅ Achat réussi!\n"
                f"Vous avez acheté: **{item_name}**{desc_text}\n"
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
    async def add_item(self, ctx, price: int, name: str, *, description: str = ""):
        """Ajoute un article à la boutique. Usage: $add_item <prix> <nom> [description]"""
        if not self._db:
            await ctx.send("❌ La boutique n'est pas disponible.")
            return

        success = self._db.add_item(name, price, description)
        if success:
            desc_text = f" avec la description: {description}" if description else ""
            await ctx.send(f"✅ Article **{name}** ajouté à la boutique pour {price} jetons{desc_text}.")
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
        for item_id, name, price, description in items:
            desc_text = f"\n📝 {description}" if description else ""
            embed.add_field(name=f"ID: {item_id}", value=f"{name} - {price} jetons{desc_text}", inline=False)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Boutique(bot))