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


class PaginationView(discord.ui.View):
    def __init__(self, embeds):
        super().__init__(timeout=60)
        self.embeds = embeds
        self.current_page = 0

    @discord.ui.button(emoji="⏪")
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page != 0:
            self.current_page = 0
            await interaction.message.edit(embed=self.embeds[self.current_page])
        await interaction.response.defer()

    @discord.ui.button(emoji="⬅️")
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page - 1 >= 0:
            self.current_page = self.current_page - 1
            await interaction.message.edit(embed=self.embeds[self.current_page])
        await interaction.response.defer()

    @discord.ui.button(emoji="➡️")
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page + 1 < len(self.embeds):
            self.current_page = self.current_page + 1
            await interaction.message.edit(embed=self.embeds[self.current_page])
        await interaction.response.defer()

    @discord.ui.button(emoji="⏩")
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page != len(self.embeds) - 1:
            self.current_page = len(self.embeds) - 1
            await interaction.message.edit(embed=self.embeds[self.current_page])
        await interaction.response.defer()

    async def on_timeout(self) -> None:
        if self.message is not None:
            await self.message.edit(view=None)
