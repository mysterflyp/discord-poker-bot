import discord
from discord.ui import View, Select


class TestView(discord.ui.View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label="Suivre", style=discord.ButtonStyle.success)
    async def follow_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"... a suivs la mise est maintenant de ✅")
        self.clear_items()
        await interaction.message.edit(view=self)

    @discord.ui.button(label="Relancer", style=discord.ButtonStyle.primary)
    async def retry_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"... as relancé de 🔄")
        self.clear_items()
        await interaction.message.edit(view=self)

    @discord.ui.button(label="Coucher", style=discord.ButtonStyle.danger)
    async def fold_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"c'est couché ❌")
        self.clear_items()
        await interaction.message.edit(view=self)
