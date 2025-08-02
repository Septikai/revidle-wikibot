from typing import List

import discord


class SearchResultsDropdown(discord.ui.Select):
    def __init__(self, results: List[str]):
        options = [discord.SelectOption(label=result) for result in results]
        super().__init__(placeholder="Which result would you like to view?",
                         max_values=1, min_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()


class SearchResultsView(discord.ui.View):
    def __init__(self, results: List[str]):
        super().__init__()
        self.dropdown = SearchResultsDropdown(results)
        self.add_item(self.dropdown)
        self.result = None

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.result = self.dropdown.values[0]
        self.stop()
