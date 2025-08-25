import re
from typing import List, Union

import discord
from discord.ext import commands, tasks
from discord import app_commands

from bot import DiscordBot
from data_management.data_protocols import ConstantsConfig
from helpers.utils import stable_bot_check
from helpers.views import SearchResultsView, PaginatedSearchView

class Wiki(commands.Cog):
    """Wiki commands and listeners."""

    def __init__(self, bot: DiscordBot):
        """Initialise the Wiki cog.

        :param bot: The DiscordBot instance.
        """
        self.bot = bot
        self.on_message_cache = {}
        constants: ConstantsConfig = self.bot.configs["constants"]
        self.max_mw_query_len = constants.max_mw_query_len
        self.wiki_base_url = constants.wiki_base_url
        super().__init__()
        self.clear_on_message_cache.start()

    def cog_unload(self) -> None:
        self.clear_on_message_cache.cancel()

    @tasks.loop(hours=24)
    async def clear_on_message_cache(self):
        """Clear the on_message cache to allow new results to be fetched"""
        self.on_message_cache.clear()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Send links when prompted with a message containing text enclosed in [[]] or {{}}.

        [[]] will not embed, {{}} will.

        :param message: the message that was sent"""
        # Check if this message should be processed
        if message.author.bot:
            return
        ctx = await self.bot.get_context(message)
        if not stable_bot_check(ctx):
            return
        check = await self.bot.settings.get_permissions_check(ctx, event_type="on_message_wiki_links")
        if check is not None and not check.evaluate(ctx):
            return


        msg = message.content

        # [[x]] = capture group g1, {{x}} = capture group g2
        res = re.findall(
            r"\[\[(?!\s+\])((?:[\w\s]+:)?(?:[\w\s]{3,}))\]\]|\{\{(?!\s+\])((?:[\w\s]+:)?(?:[\w\s]{3,}))\}\}", msg)

        # response_data is [(text, embed)] list, embed = True means link should have embed
        MIN_QUERY_LENGTH = 3
        MAX_EMBED_COUNT = 3
        MAX_RESULT_COUNT = 10

        response_data = []  
        for g1, g2 in res:
            text = g1 or g2 
            processed_text = re.sub(r"\s+", " ", text.strip())
            if (len(processed_text) >= MIN_QUERY_LENGTH and
                    (":" not in processed_text or len(processed_text.split(":")[1]) >= MIN_QUERY_LENGTH)):
                response_data.append((processed_text, False if g1 else True))
        
        if len(response_data) == 0:
            return
        
        # Remove duplicate queries
        response_data = list(dict.fromkeys(response_data))

        # Local function to format the results message
        def format_msg(data: List[Union[str, bool]]):
            embedded_pages = []
            results = 0
            seen_queries = set()

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
                    if result is None and ":" in query and query.split(":")[0].lower() == "new":
                        result = f"{self.wiki_base_url}{query.split(':')[1]}?action=edit&redlink=1"
                    else:
                        self.on_message_cache[query.lower()] = result

                if result is None or result in seen_queries:
                    continue
                results += 1
                seen_queries.add(result)

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
            async with (message.channel.typing()):
                msg = format_msg(response_data)

        # All queries are cached
        else:
            msg = format_msg(response_data)

        if msg != "":
            await message.channel.send(msg, mention_author=False)

    @commands.hybrid_command(name="search")
    @app_commands.describe(query="The query to search for")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def search(self, ctx, *, query: str):
        """Search for a specific page"""
        if len(query) > self.max_mw_query_len:
            raise commands.UserInputError(f"Search queries cannot be over {self.max_mw_query_len} characters.")
        async with ctx.typing():
            results = self.bot.wiki.search(query)
        if len(results) == 0:
            await ctx.reply(f"No results found for: {query}", mention_author=False, ephemeral=True,
                            allowed_mentions=discord.AllowedMentions.none())
            return
        view = SearchResultsView(results, author=ctx.author)
        result_str = "\n".join([f"- {result}" for result in results]).replace("_", r"\_")
        view.message = await ctx.reply(f"Found:\n{result_str}", view=view, mention_author=False, ephemeral=True)
        await view.wait()
        if view.result is None:
            return
        result = self.bot.wiki.page_or_section_search(view.result)
        await ctx.reply(result)

    @commands.hybrid_command(name="advsearch", aliases=["advancedsearch"])
    @app_commands.describe(query="The query to search for")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def advanced_search(self, ctx, *, query: str):
        r"""Search for a page, but with snippets

        Allowed operators:
        - `*` acts as a wildcard
            - `A*` could match `AP`, `Achievements`, `Animals`, etc
        - `\?` acts as a single character wildcard
            - `A\?` could match `AP` or `An`, but not `Achievements` or `Animals`
        - Prepending your query with `Guide:` allows searching specifically for Guide pages.
            - `Guide:Unity` will match all Guide pages containing the word `unity`    
        """

        if len(query) > self.max_mw_query_len:
            raise commands.UserInputError(f"Search queries cannot be over {self.max_mw_query_len} characters.")
        results = self.bot.wiki.advanced_search(query)
        if len(results) == 0:
            await ctx.reply(f"No results found for: {query}", mention_author=False, ephemeral=True,
                            allowed_mentions=discord.AllowedMentions.none())
            return
        view = PaginatedSearchView(results, author=ctx.author)
        view.message = await ctx.reply(view.pages[0], view=view, mention_author=False, ephemeral=True)
        await view.wait()
        if view.result is None:
            return
        result = self.bot.wiki.page_search(view.result)
        await ctx.reply(result.url, ephemeral=True)


async def setup(bot: DiscordBot):
    """Add the Wiki cog to the bot.

    :param bot: The DiscordBot instance.
    """
    await bot.add_cog(Wiki(bot))
