import typing

import discord
from discord import app_commands
from discord.ext import commands
from pymongo.errors import DuplicateKeyError

from data_management.data_protocols import TagCollectionEntry
from bot import DiscordBot
from helpers.modals import TextInputModal
from helpers.utils import Embed, create_pages
from helpers.views import PaginationView


class HelpCommand(commands.HelpCommand):
    """A custom implementation of the Help command"""
    # help
    async def send_bot_help(self, mapping):
        """Generic help overview"""
        help_embed = discord.Embed(title="Help",
                                   description=f"Use `{self.context.prefix}help [category|command]` for more information",
                                   colour=0x00FF00)
        for cog in mapping.keys():
            # if (cog.hidden and not staff_check(self.context)) or cog.get_commands() == []:
            #     continue
            if cog is not None:
                help_embed.add_field(name=f"__{cog.qualified_name.title()}:__", value=cog.__doc__, inline=False)
            else:
                help_embed.add_field(name=f"__Dev Commands:__", value="Development commands for bot control.",
                                     inline=False)
        help_embed.set_footer(text="Created by @septikai and @chillcatto")
        await self.send_help_embed(help_embed)

    # help <command>
    async def send_command_help(self, command: commands.Command):
        """Help for a specific command"""
        title = command.name.capitalize()
        if len(command.parents) > 0:
            parents = command.parents
            parents.reverse()
            title = f"{' '.join([parent.name.capitalize() for parent in parents])} {title}"
        help_embed = discord.Embed(title=title,
                                   description=command.help if command.help is not None else "No Information",
                                   colour=0x00FF00)
        help_embed.add_field(name="Usage:",
                             value=f"`{self.context.prefix}{command.qualified_name} {command.signature}"
                                   f"`\n\n`<>` represents required arguments\n`[]` represents optional arguments")
        await self.send_help_embed(help_embed)

    # help <group>
    async def send_group_help(self, group: commands.Group):
        """Help for a command group"""
        # TODO: implement this
        await self.context.send("This is help group.\n<@540939418933133312> implement this")

    # help <cog>
    async def send_cog_help(self, cog: commands.Cog):
        """Help for a cog"""
        help_embed = discord.Embed(title=cog.qualified_name.title(), description=cog.__doc__, colour=0x00FF00)
        cog_commands = []
        for command in cog.get_commands():
            try:
                if not await command.can_run(self.context):
                    continue
                cog_commands.append(command.name)
            except commands.CheckFailure:
                continue
        help_embed.add_field(name="Commands:", value=(", ".join(sorted(cog_commands))) if cog_commands else None)
        await self.send_help_embed(help_embed)

    async def send_help_embed(self, embed: Embed):
        """Send the help embed"""
        await self.context.send(embed=embed)


class Util(commands.Cog):
    """Utility commands for general use."""

    def __init__(self, bot: DiscordBot):
        """Initialise the Util cog.

        :param bot: The DiscordBot instance.
        """
        self.bot = bot
        super().__init__()

        self._original_help_command = bot.help_command
        self.bot.help_command = HelpCommand()
        bot.help_command.cog = self

    def cog_unload(self):
        """Called when the cog is unloaded"""
        self.bot.help_command = self._original_help_command

    @commands.command(name="ping")
    async def ping_command(self, ctx):
        """Pings the bot to show latency"""
        embed = discord.Embed(title="Pong!", description=f"That took {round(100 * self.bot.latency)} ms",
                              color=0x00FF00)
        embed.set_thumbnail(url="https://i.imgur.com/qbyZc2j.gif")
        await ctx.send(embed=embed)

    @commands.hybrid_group(name="tag", fallback="send")
    @app_commands.describe(name="The tag to send")
    async def tag_group(self, ctx, name: str = ""):
        """
        The tag command group

        Tags can be used to save a message to be sent later on request
        """
        if name == "":
            raise commands.UserInputError
        tag: TagCollectionEntry = await self.bot.collections["tags"].get_one(name)
        mentions = discord.AllowedMentions.none()
        await ctx.send(tag.content, allowed_mentions=mentions)

    @tag_group.command(name="create")
    @app_commands.describe(name="The name for the tag", link="The message to turn into a tag")
    async def tag_create(self, ctx, name: str, link: typing.Optional[str] = None):
        """
        Create a new tag
        """
        if not name.isalnum():
            raise commands.UserInputError

        async def make_tag(tag_name: str, content: str, aliases: typing.List[str] = None,
                           response: discord.InteractionResponse = None):
            if aliases is None:
                aliases = []
            if len(content) == 0:
                raise commands.UserInputError("Cannot make a tag with an empty body!")

            # Add tag, return with error message on duplicate
            try:
                await self.bot.collections["tags"].insert_one(tag_name, content=content, aliases=aliases)
            except DuplicateKeyError:
                if response is None:
                    return await ctx.reply("Cannot create tag!\n\nA tag with this name already exists.",
                                           mention_author=False)
                else:
                    return await response.send_message("Cannot create tag!\n\nA tag with this name already exists.",
                                                       ephemeral=True)

            # Confirm tag creation
            if response is None:
                await ctx.reply("Tag created!", mention_author=False)
            else:
                await response.send_message("Tag created!", ephemeral=True)

        # Create tag from link
        if link is not None:
            try:
                msg = await commands.MessageConverter().convert(ctx, link)
            except commands.MessageNotFound:
                raise commands.UserInputError
            await make_tag(name, msg.content, response=ctx.interaction.response if ctx.interaction else None)

        # Create tag with message command
        elif ctx.interaction is None:
            await ctx.send("What should the tag be?")
            msg = await self.bot.wait_for("message",
                                          check=lambda m: m.channel == ctx.channel and m.author == ctx.author)
            await make_tag(name, msg.content)

        # Create tag with modal via application command
        else:
            modal = TextInputModal(title="Tag Creation", label="Content", placeholder="Tag Content", long=True)
            await ctx.interaction.response.send_modal(modal)
            await modal.wait()
            await make_tag(name, modal.text, response=modal.response)

    @tag_group.command(name="delete", aliases=["remove"])
    @app_commands.describe(name="The tag to remove")
    async def tag_delete(self, ctx, name: str):
        """
        Delete a tag
        """
        await self.bot.collections["tags"].remove_one(name)
        await ctx.reply(f"Tag `{name}` deleted!")

    @tag_group.command(name="list")
    async def tag_list(self, ctx):
        """
        List all tags
        """
        tags: list[TagCollectionEntry] = await self.bot.collections["tags"].get_all()
        tag_names: list[str] = [tag.id_ for tag in tags]
        pages: list[discord.Embed] = create_pages(tag_names)
        view = PaginationView(pages, author=ctx.author)
        view.message = await ctx.reply(embed=pages[0], view=view)

    @tag_group.command(name="search", aliases=["find"])
    @app_commands.describe(name="The tag to search for")
    async def tag_search(self, ctx, name: str):
        """
        Search for a specific tag
        """
        if not name.isalnum():
            raise commands.UserInputError
        tags: list[TagCollectionEntry] = await self.bot.collections["tags"].search_all({"_id": name})
        tag_names: list[str] = [tag.id_ for tag in tags]
        pages: list[discord.Embed] = create_pages(tag_names)
        view = PaginationView(pages, author=ctx.author)
        view.message = await ctx.reply(embed=pages[0], view=view)


async def setup(bot: DiscordBot):
    """Add the Util cog to the bot.

    :param bot: The DiscordBot instance.
    """
    await bot.add_cog(Util(bot))
