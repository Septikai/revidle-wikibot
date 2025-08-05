from functools import wraps
from typing import List, Union

import discord

from helpers.wiki_lib_patch import SearchResult


class SearchResultsDropdown(discord.ui.Select):
    def __init__(self, results: List[str]):
        options = [discord.SelectOption(label=result) for result in results]
        super().__init__(placeholder="Which result would you like to view?",
                         max_values=1, min_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()


class BaseView(discord.ui.View):
    def __init__(self, author: Union[discord.Member, discord.User] = None, timeout: int = 60, *args, **kwargs):
        super().__init__(timeout=timeout)
        self.message: discord.Message = None
        self.author = author

    async def update(self, *args, **kwargs):
        if self.message is not None:
            await self.message.edit(*args, **kwargs)

    async def on_timeout(self) -> None:
        await self.update(view=None)

    async def interaction_check(self, interaction: discord.Interaction, /) -> bool:
        if self.author is not None and interaction.user != self.author:
            return False
        return True


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


class PaginationView(BaseView):
    def __init__(self, pages: List[Union[discord.Embed, str]], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pages = pages
        self.current_page = 0
        self.message: discord.Message = None

    async def update(self, *args, **kwargs):
        if isinstance(self.pages[self.current_page], discord.Embed):
            await super().update(content="", embed=self.pages[self.current_page], *args, **kwargs)
        else:
            await super().update(content=str(self.pages[self.current_page]), embed=None, *args, **kwargs)

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


class PaginatedSearchView(SearchResultsView, PaginationView):
    def __init__(self, results: List[SearchResult], *args, **kwargs):
        self.results = results
        self.result_list = [f"## {sr.title}\n{sr.snippet or '*No snippet available*'}" for sr in results]
        pages = ["\n\n".join(self.result_list[z:z + 5] if z + 5 <= len(results) else self.result_list[z:len(results)])
                 for z in range(0, len(results), 5)]
        super().__init__([sr.title for sr in results][:5], pages, *args, **kwargs)

    async def update(self, *args, **kwargs):
        if "view" in kwargs.keys() and kwargs["view"] is None:
            return await super().update(*args, **kwargs)
        self.remove_item(self.dropdown)
        self.dropdown = SearchResultsDropdown(
            [result.title for result in (self.results[self.current_page*5:(self.current_page*5 + 5 if
             self.current_page*5 + 5 < len(self.results) else len(self.results))])])
        self.add_item(self.dropdown)
        await super().update(view=self, *args, **kwargs)
