import re
from typing import List, Union

import discord
from discord.ext import commands, tasks
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
        self.on_message_cache = {}
        super().__init__()
        self.clear_on_message_cache.start()

    def cog_unload(self) -> None:
        self.clear_on_message_cache.cancel()

    @tasks.loop(hours=24)
    async def clear_on_message_cache(self):
        """Clear the on_message cache to allow new results to be fetched"""
        self.on_message_cache.clear()

    @commands.Cog.listener()
    async def on_message(self, payload):
        """Send links when prompted with a message containing text enclosed in [[]] or {{}}.

        [[]] will not embed, {{}} will.

        :param payload: the message payload"""
        if payload.author.bot:
            return
        msg = payload.content

        # [[x]] = capture group g1, {{x}} = capture group g2
        res = re.findall(r"\[\[(?!\s+\])([\w\s]{3,})\]\]|\{\{(?!\s+\])([\w\s]{3,})\}\}", msg)

        # response_data is [(text, embed)] list, embed = True means link should have embed
        MIN_QUERY_LENGTH = 3
        MAX_EMBED_COUNT = 3
        MAX_RESULT_COUNT = 10

        response_data = []  
        for g1, g2 in res:
            text = g1 or g2 
            processed_text = re.sub(r"\s+", " ", text.strip())
            if len(processed_text) >= MIN_QUERY_LENGTH:
                response_data.append((processed_text, False if g1 else True))
        
        if len(response_data) == 0:
            return
        
        # Remove duplicate queries
        response_data = list(dict.fromkeys(response_data))

        # Local function to format the results message
        def format_msg(data: List[Union[str, bool]]):
            embedded_pages = []
            results = 0
            message = ""
            for (query, embed) in data:
                # Limit to 10 results
                if results >= MAX_RESULT_COUNT:
                    return message

                # Get result of query
                if query.lower() in self.on_message_cache:
                    result = self.on_message_cache[query.lower()]
                else:
                    result = self.bot.wiki.page_or_section_search(query)
                    self.on_message_cache[query.lower()] = result

                if result is None:
                    continue
                results += 1

                # Prevent more than 5 pages being embedded
                if (embed and not ((result in embedded_pages) or
                        ("#" in result and result.split("#")[0] in embedded_pages))):
                    if len(embedded_pages) < MAX_EMBED_COUNT:
                        embedded_pages.append(result.split("#")[0] if "#" in result else result)
                    else:
                        embed = False

                # Format message
                message += f"<{result}>\n" if not embed else f"{result}\n"
            return message

        # At least one query isn't cached
        if any([query.lower() not in self.on_message_cache for (query, _) in response_data]):
            async with (payload.channel.typing()):
                msg = format_msg(response_data)

        # All queries are cached
        else:
            msg = format_msg(response_data)

        if msg != "":
            await payload.channel.send(msg, mention_author=False)

    @commands.hybrid_command(name="search")
    @app_commands.describe(query="The page to search for")
    async def search(self, ctx, *, query: str):
        """Search for a specific page"""
        async with ctx.typing():
            results = self.bot.wiki.search(query)
        if len(results) == 0:
            return await ctx.reply(f"No results found for: {query}", mention_author=False, ephemeral=True,
                                   allowed_mentions=discord.AllowedMentions.none())
        view = SearchResultsView(results, author=ctx.author)
        result_str = "\n".join([f"- {result}" for result in results])
        view.message = await ctx.reply(f"Found:\n{result_str}", view=view, mention_author=False, ephemeral=True)
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
