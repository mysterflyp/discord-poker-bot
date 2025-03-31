import discord
from discord.ui import View, Select

from poker_game import PokerGame


class TestView(discord.ui.View):
    def __init__(self,ctx,game:PokerGame,player):
        super().__init__()
        self.ctx = ctx
        self.game = game
        self.player = player
        
    @discord.ui.button(label="Suivre", style=discord.ButtonStyle.success)
    async def follow_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            difference = self.game.check(self.player)
            if difference != 0:
                await self.ctx.send(
                    f"{self.player.name} a complété sa mise avec {difference} jetons, mise totale: {self.game.get_player_bet(self.player)}."
                )
            else:
                await self.ctx.send(f"{self.player.name} a suivi.")
        except ValueError as e:
            await self.ctx.send(f"{e}")
        await self.game.handle_played(self.ctx)

        # Désactiver le bouton après clic
        self.clear_items()
        await interaction.message.edit(view=self)


    @discord.ui.button(label="Relancer", style=discord.ButtonStyle.primary)
    async def retry_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"{self.player.name} as relancé de 🔄")
        self.clear_items()
        await interaction.message.edit(view=self)

    @discord.ui.button(label="Coucher", style=discord.ButtonStyle.danger)
    async def fold_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            self.game.fold(self.player)
        except ValueError as e:
            await self.ctx.send(f"{e}")
            return

        await self.ctx.send(f"{self.player.name} s'est couché.")
        await self.game.handle_played(self.ctx)
        self.clear_items()
        await interaction.message.edit(view=self)
