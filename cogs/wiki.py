import re

from discord.ext import commands

from bot import DiscordBot
from helpers.views import SearchResultsView


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
    async def search(self, ctx, query: str):
        """Search for a specific page"""
        results = self.bot.wiki.search(query)
        view = SearchResultsView(results)
        result_str = "\n".join([f"- {result}" for result in results])
        if ctx.interaction is None:
            await ctx.reply(f"Found:\n{result_str}", view=view, mention_author=False)
        else:
            await ctx.reply(f"Found:\n{result_str}", view=view, ephemeral=True)
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
