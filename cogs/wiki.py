import re

import discord
from discord.ext import commands
from discord import app_commands

from bot import DiscordBot
from helpers.views import SearchResultsView, PaginatedSearchView


class Wiki(commands.Cog):
    """Wiki commands and listeners."""

    def __init__(self, bot: DiscordBot):
        """Initialise the Wiki cog.

        :param bot: The DiscordBot instance.
        """
        self.bot = bot
        super().__init__()

    @commands.Cog.listener()
    async def on_message(self, payload):
        """Send links when prompted with a message containing text enclosed in [[]] or {{}}.

        [[]] will not embed, {{}} will.

        :param payload: the message payload"""
        if payload.author.bot:
            return
        msg = payload.content
        res = re.findall(r"(\[\[(.*?)\]\])|(\{\{(.*?)\}\})", msg)
        if len(res) == 0:
            return
        msg = ""
        for query in res:
            result = self.bot.wiki.page_search(query[1] if query[1] != "" else query[3])
            msg += f"<{result.url}>\n" if query[1] != "" else f"{result.url}\n"
        await payload.channel.send(msg, mention_author=False)

    @commands.hybrid_command(name="search")
    @app_commands.describe(query="The page to search for")
    async def search(self, ctx, *, query: str):
        """Search for a specific page"""
        results = self.bot.wiki.search(query)
        if len(results) == 0:
            return await ctx.reply(f"No results found for: {query}", mention_author=False, ephemeral=True,
                                   allowed_mentions=discord.AllowedMentions.none())
        view = SearchResultsView(results, author=ctx.author)
        result_str = "\n".join([f"- {result}" for result in results])
        await ctx.reply(f"Found:\n{result_str}", view=view, mention_author=False, ephemeral=True)
        await view.wait()
        if view.result is None:
            return
        result = self.bot.wiki.page_search(view.result)
        await ctx.reply(result.url)

    @commands.hybrid_command(name="advsearch")
    @app_commands.describe(query="The page to search for")
    async def advanced_search(self, ctx, *, query: str):
        """Search for a page, but with snippets"""
        results = self.bot.wiki.advanced_search(query)
        if len(results) == 0:
            return await ctx.reply(f"No results found for: {query}", mention_author=False, ephemeral=True,
                                   allowed_mentions=discord.AllowedMentions.none())
        view = PaginatedSearchView(results, author=ctx.author)
        # TODO: Implement search result message using sr.title and sr.snippet
        #  result content formatting moved to helpers/views.py Line 97
        view.message = await ctx.reply(view.pages[0], view=view, mention_author=False, ephemeral=True)
        await view.wait()
        if view.result is None:
            return
        result = self.bot.wiki.page_search(view.result)
        await ctx.reply(result.url)


async def setup(bot: DiscordBot):
    """Add the Wiki cog to the bot.

    :param bot: The DiscordBot instance.
    """
    await bot.add_cog(Wiki(bot))
