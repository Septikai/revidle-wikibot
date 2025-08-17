import random
import typing
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

from data_management.data_protocols import TagCollectionEntry
from bot import DiscordBot
from helpers.modals import TagModal
from helpers.utils import Embed, create_pages, dev_only
from helpers.views import PaginationView#, SettingsMenuView


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
            try:
                any_runnable = any([await command.can_run(self.context) for command in mapping.get(cog)])
            except commands.CheckFailure:
                continue
            if any_runnable:
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
        if not await command.can_run(self.context):
            raise commands.CommandNotFound
        title = command.name.capitalize()
        if len(command.parents) > 0:
            parents = command.parents
            parents.reverse()
            title = f"{' '.join([parent.name.capitalize() for parent in parents])} {title}"
        help_embed = discord.Embed(title=title,
                                   description=command.help if command.help is not None else "No Information",
                                   colour=0x00FF00)
        help_embed.add_field(name="Usage:",
                             value=f"`{self.context.prefix}{command.qualified_name}"
                                   f"{(' ' + command.signature) if command.signature != '' else ''}"
                                   f"`\n\n`<>` represents required arguments\n`[]` represents optional arguments")
        await self.send_help_embed(help_embed)

    # help <group>
    async def send_group_help(self, group: commands.Group):
        """Help for a command group"""
        if not await group.can_run(self.context):
            raise commands.CommandNotFound
        title = group.name.capitalize()
        if len(group.parents) > 0:
            parents = group.parents
            parents.reverse()
            title = f"{' '.join([parent.name.capitalize() for parent in parents])} {title}"
        help_embed = discord.Embed(title=title,
                                   description=group.help if group.help is not None else "No Information",
                                   colour=0x00FF00)
        help_embed.add_field(name="Usage:",
                             value=f"`{self.context.prefix}{group.qualified_name}"
                                   f"{(' ' + group.signature) if group.signature != '' else ''}"
                                   f"`\n\n`<>` represents required arguments\n`[]` represents optional arguments")
        subcommands = [command.qualified_name for command in group.commands if await command.can_run(self.context)]
        help_embed.add_field(name="Subcommands:",
                             value=f"`{'`, `'.join(subcommands)}`",
                             inline=False)
        await self.send_help_embed(help_embed)

    # help <cog>
    async def send_cog_help(self, cog: commands.Cog):
        """Help for a cog"""
        any_runnable = False
        try:
            any_runnable = any([await command.can_run(self.context) for command in cog.get_commands()])
        except commands.CheckFailure:
            pass
        if not any_runnable:
            raise commands.CommandNotFound
        help_embed = discord.Embed(title=cog.qualified_name.title(), description=cog.__doc__, colour=0x00FF00)
        cog_commands = [command.qualified_name for command in cog.get_commands() if await command.can_run(self.context)]
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

        self.auto_toggle_status.start()

    def cog_unload(self):
        """Called when the cog is unloaded"""
        self.bot.help_command = self._original_help_command

    @tasks.loop(minutes=30)
    async def auto_toggle_status(self):
        await self.toggle_bot_status()

    @auto_toggle_status.before_loop
    async def before_auto_toggle_status(self):
        await self.bot.wait_until_ready()

    async def toggle_bot_status(self):
        options = ["Watching discord.gg/apEk7SUCTB", "Watching discord.gg/onigaming", "Playing Revolution Idle", "Reading Revolution Idle Wiki", "Writing Revolution Idle Wiki", "Maintaining Revolution Idle Wiki"]
        await self.bot.change_presence(activity=discord.CustomActivity(name=random.choice(options)))

    @commands.command(name="ping")
    async def ping_command(self, ctx: commands.Context):
        """Pings the bot to show latency"""
        embed = discord.Embed(title="Pong!", description=f"That took {round(100 * self.bot.latency)} ms",
                              color=0x00FF00)
        embed.set_thumbnail(url="https://i.imgur.com/qbyZc2j.gif")
        await ctx.send(embed=embed)

    async def tag_check(self, tag_name: str, content: str, aliases: typing.List[str] = None,
                        response: discord.InteractionResponse = None, editing: bool = False):
        """Prevents all invalid tags

        :type tag_name: the name of the tag
        :param content: the content of the tag
        :param aliases: the aliases of the tag
        :param response: the discord.InteractionResponse that triggered this, if it exists
        :raises: commands.UserInputError"""
        # Prevent empty tags
        if len(content) == 0:
            raise commands.UserInputError("Cannot make a tag with an empty body!")

        # Prevent duplicate names and aliases across tags
        all_tags = await self.bot.collections["tags"].get_all()
        duplicates = [name_alias for tag in all_tags
                      for name_alias in [tag["id_"], *tag["aliases"]]
                      if (name_alias in aliases or name_alias == tag_name)
                      and (not editing or tag_name != tag["id_"])]
        if len(duplicates) > 0:
            if response is not None:
                await response.defer()
            raise commands.UserInputError(f"A tag already exists with name or alias: `{duplicates[0]}`")

        # Prevent a tag having the same name and alias
        if tag_name in aliases:
            if response is not None:
                await response.defer()
            raise commands.UserInputError(f"A tag cannot have its own name as an alias!")

    @commands.hybrid_group(name="tag", fallback="send")
    @app_commands.describe(name="The tag to send")
    async def tag_group(self, ctx: commands.Context, name: str = ""):
        """The tag command group

        Tags can be used to save a message to be sent later on request"""
        if name == "":
            raise commands.UserInputError
        mentions = discord.AllowedMentions.none()
        try:
            tag: TagCollectionEntry = await self.bot.collections["tags"].get_one(name)
        except ValueError:
            # No tag with `name` as its ID, check all tags to find aliases
            all_tags = await self.bot.collections["tags"].get_all()
            tags = [z for z in all_tags if name in z["aliases"]]
            if len(tags) == 0:
                return await ctx.send(f"Tag `{name}` does not exist!", allowed_mentions=mentions)
            tag = tags[0]
        await ctx.send(tag.content, allowed_mentions=mentions)

    @tag_group.command(name="create")
    @app_commands.describe(name="The name for the tag", link="The message to turn into a tag")
    async def tag_create(self, ctx: commands.Context, name: str, link: typing.Optional[str] = None):
        """Create a new tag"""
        if not name.isalnum():
            raise commands.UserInputError

        async def make_tag(tag_name: str, content: str, aliases: typing.List[str] = None,
                           response: discord.InteractionResponse = None):
            if aliases is None:
                aliases = []

            # Prevent invalid tags
            await self.tag_check(tag_name, content, aliases, response)

            # Add tag, return with error message on duplicate
            await self.bot.collections["tags"].insert_one(tag_name, content=content, aliases=aliases,
                                                          author=ctx.author.id, created_at=round(time.time()),
                                                          last_editor=ctx.author.id, last_edit=round(time.time()))

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
            modal = TagModal(title="Tag Creation", aliases=[])
            await ctx.interaction.response.send_modal(modal)
            await modal.wait()
            await make_tag(name, modal.content, modal.aliases, response=modal.response)

    @tag_group.command(name="delete", aliases=["remove"])
    @app_commands.describe(name="The tag to remove")
    async def tag_delete(self, ctx: commands.Context, name: str):
        """Delete a tag"""
        await self.bot.collections["tags"].remove_one(name)
        await ctx.reply(f"Tag `{name}` deleted!", ephemeral=True)

    @tag_group.command(name="list")
    async def tag_list(self, ctx: commands.Context):
        """List all tags"""
        tags: list[TagCollectionEntry] = await self.bot.collections["tags"].get_all()
        tag_names: list[str] = [tag.id_ for tag in tags]
        pages: list[discord.Embed] = create_pages(tag_names)
        view = PaginationView(pages, author=ctx.author)
        view.message = await ctx.reply(embed=pages[0], view=view, ephemeral=True)

    @tag_group.command(name="search", aliases=["find"])
    @app_commands.describe(name="The tag to search for")
    async def tag_search(self, ctx: commands.Context, name: str):
        """Search for a specific tag"""
        if not name.isalnum():
            raise commands.UserInputError
        tags: list[TagCollectionEntry] = await self.bot.collections["tags"].search_all({"_id": name})
        tag_names: list[str] = [tag.id_ for tag in tags]
        pages: list[discord.Embed] = create_pages(tag_names)
        view = PaginationView(pages, author=ctx.author)
        view.message = await ctx.reply(embed=pages[0], view=view, ephemeral=True)

    @tag_group.group(name="alias")
    async def tag_alias_group(self, ctx: commands.Context):
        """The tag aliases command group

        Aliases can be used to refer to a tag by another name for ease of access."""
        raise commands.UserInputError

    @tag_alias_group.command(name="list", aliases=["ls"])
    @app_commands.describe(name="The tag to check aliases of")
    async def tag_alias_list(self, ctx: commands.Context, name: str):
        """Check aliases for a tag"""
        if name == "":
            raise commands.UserInputError
        mentions = discord.AllowedMentions.none()
        try:
            tag: TagCollectionEntry = await self.bot.collections["tags"].get_one(name)
        except ValueError:
            return await ctx.send(f"Tag `{name}` does not exist!", allowed_mentions=mentions)
        msg = f"Aliases of tag `{tag.id_}`:\n`" + ("`, `".join(tag.aliases) if len(tag.aliases) >= 1 else "None") + "`"
        await ctx.send(msg, allowed_mentions=mentions, ephemeral=True)

    @tag_group.command(name="edit")
    @app_commands.describe(name="The tag to edit")
    async def tag_edit(self, ctx: commands.Context, name: str):
        """Edit an existing tag"""

        # Create tag with message command
        if ctx.interaction is None:
            return await ctx.send("Tags can only be edited via Application (Slash) Commands.")

        mentions = discord.AllowedMentions.none()
        try:
            tag: TagCollectionEntry = await self.bot.collections["tags"].get_one(name)
        except ValueError:
            return await ctx.send(f"Tag `{name}` does not exist!", allowed_mentions=mentions)

        async def edit_tag(tag_name: str, content: str, aliases: typing.List[str],
                           response: discord.InteractionResponse):
            if aliases is None:
                aliases = []

            # Prevent invalid tags
            await self.tag_check(tag_name, content, aliases, response, editing=True)

            # Modify tag
            await self.bot.collections["tags"].update_one(tag_name, content=content, aliases=aliases,
                                                          last_editor=ctx.author.id, last_edit=round(time.time()))

            # Confirm tag modification
            await response.send_message("Tag edited successfully!", ephemeral=True)

        # Edit tag with modal via application command
        modal = TagModal(title="Tag Modification", aliases=tag.aliases, content=tag.content)
        await ctx.interaction.response.send_modal(modal)
        await modal.wait()
        await edit_tag(name, modal.content, modal.aliases, response=modal.response)

    @tag_group.command(name="info")
    @app_commands.describe(name="The tag to edit")
    async def tag_info(self, ctx: commands.Context, name: str):
        try:
            tag: TagCollectionEntry = await self.bot.collections["tags"].get_one(name)
        except ValueError:
            # No tag with `name` as its ID, check all tags to find aliases
            all_tags = await self.bot.collections["tags"].get_all()
            tags = [z for z in all_tags if name in z["aliases"]]
            if len(tags) == 0:
                return await ctx.send(f"Tag `{name}` does not exist!",
                                      allowed_mentions=discord.AllowedMentions.none())
            tag = tags[0]

        embed = (discord.Embed(title="Tag Info", description=f"**{tag.id_}**")
                 .add_field(name="Aliases", value=", ".join(tag.aliases) if len(tag.aliases) > 0 else "None",
                            inline=False)
                 .add_field(name="Creator", value=ctx.guild.get_member(tag.author).mention)
                 .add_field(name="Creation Date", value=f"<t:{tag.created_at}:F>")
                 .add_field(name="", value="")
                 .add_field(name="Last Editor", value=ctx.guild.get_member(tag.last_editor).mention)
                 .add_field(name="Edit Date", value=f"<t:{tag.last_edit}:F>")
                 .add_field(name="", value=""))
        await ctx.send(embed=embed, ephemeral=True)

    # @commands.hybrid_command(name="settings", aliases=["options"])
    # @dev_only
    # async def edit_settings(self, ctx: commands.Context):
    #     """Provides an interactive settings editor to allow you to edit bot settings at runtime
    #
    #     This enables more useful and configurable settings to exist, and for the bot to behave differently in different
    #     servers."""
    #     embed = discord.Embed(title="Settings",
    #                           description="Interactive settings editor. Allows modification of bot settings for the"
    #                                       "server at runtime, enabling more useful and configurable settings to exist.",
    #                           colour=0x00FF00)
    #     view = SettingsMenuView(author=ctx.author)
    #     view.message = await ctx.reply(embed=embed, view=view, ephemeral=True,
    #                                    allowed_mentions=discord.AllowedMentions.none())
    #     await view.wait()
    #     await view.message.delete()
    #     self.bot.configs.reload()


async def setup(bot: DiscordBot):
    """Add the Util cog to the bot.

    :param bot: The DiscordBot instance.
    """
    await bot.add_cog(Util(bot))
