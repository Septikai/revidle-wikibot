from functools import wraps
from typing import List

import discord


class SearchResultsDropdown(discord.ui.Select):
    def __init__(self, results: List[str]):
        options = [discord.SelectOption(label=result) for result in results]
        super().__init__(placeholder="Which result would you like to view?",
                         max_values=1, min_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()


class BaseView(discord.ui.View):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message: discord.Message = None

    async def update(self, message, *args, **kwargs):
        if self.message is not None:
            await self.message.edit(*args, **kwargs)


class SearchResultsView(BaseView):
    def __init__(self, results: List[str], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dropdown = SearchResultsDropdown(results)
        self.add_item(self.dropdown)
        self.result = None

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.dropdown.values) == 0:
            return await interaction.response.send_message("Please select an option.", ephemeral=True)
        await interaction.response.defer()
        self.result = self.dropdown.values[0]
        self.stop()

    async def on_timeout(self) -> None:
        await self.update(self.message, view=None)


class PaginationView(BaseView):
    def __init__(self, pages: List[discord.Embed, str]):
        super().__init__(timeout=60)
        self.pages = pages
        self.current_page = 0
        self.message: discord.Message = None
        self.update = self.update_results(self.update)

    def update_results(self, func):
        @wraps(func)
        async def inner(*args, **kwargs):
            if isinstance(self.pages[self.current_page], discord.Embed):
                await func(self.message, content="", embed=self.pages[self.current_page])
            else:
                await func(self.message, content=str(self.pages[self.current_page]), embed=None)
        return inner

    @discord.ui.button(emoji="⏪")
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page != 0:
            self.current_page = 0
            await self.update()
        await interaction.response.defer()

    @discord.ui.button(emoji="⬅️")
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page - 1 >= 0:
            self.current_page = self.current_page - 1
            await self.update()
        await interaction.response.defer()

    @discord.ui.button(emoji="➡️")
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page + 1 < len(self.pages):
            self.current_page = self.current_page + 1
            await self.update()
        await interaction.response.defer()

    @discord.ui.button(emoji="⏩")
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page != len(self.pages) - 1:
            self.current_page = len(self.pages) - 1
            await self.update()
        await interaction.response.defer()

    async def on_timeout(self) -> None:
        await self.update(view=None)


class PaginatedSearchResultsView(SearchResultsView, PaginationView):
    def __init__(self, results: List[str]):
        super().__init__(results, None)
        self.update = self.update_dropdown(self.update)

    def update_dropdown(self, func):
        @wraps(func)
        async def inner(*args, **kwargs):
            # TODO: update dropdown
            func()
        return inner
