import pathlib
import subprocess
import time
from typing import Optional, Literal

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Greedy

from data_management.config_manager import ConfigManager
from data_management.data_protocols import GeneralConfig, CogsConfig, BotSecretsConfig
from data_management.database_manager import DatabaseManager
from data_management.wiki_interface import WikiInterface
from error_handlers import handle_message_command_error, handle_app_command_error
from helpers.graphics import print_coloured, Colour, print_startup_progress_bar
from helpers.utils import dev_only

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

BOT_CONFIGS = {
    "secrets",
    "cogs",
    "general",
    "constants"
}

MONGO_COLLECTIONS = {
    "tags"
}


# TODO: add some form of logging somewhere
# TODO: add a cog for runtime config control


class DiscordBot(commands.Bot):
    """The DiscordBot instance."""
    def __init__(self, configs: ConfigManager, collections: DatabaseManager, *args, **kwargs):
        """Initialise the DiscordBot instance.

        :param configs: The ConfigManager to handle bot config files.
        :param args: A variable length argument list.
        :param kwargs: Arbitrary keyword arguments.
        """
        super().__init__(*args, **kwargs)

        # define self.var = ...

        self.configs: ConfigManager = configs
        self.collections: DatabaseManager = collections
        self.wiki: WikiInterface = None

        # Make the help command not be case-sensitive
        self._BotBase__cogs = commands.core._CaseInsensitiveDict()

    async def setup_hook(self):
        """Runs on bot startup to load cogs and initialise the bot."""

        print_coloured(Colour.Yellow, f"Loading the bot: {self.user.name}!\n")

        time.sleep(1)

        # initialise self.var = ...

        print_coloured(Colour.Yellow, f"Connecting to the wiki...\n")

        self.wiki = WikiInterface(self.configs["secrets"].user_agent)

        general_config: GeneralConfig = self.configs["general"]

        cogs_config: CogsConfig = self.configs["cogs"]
        cogs = cogs_config.cogs

        if len(cogs) > 0:
            print_startup_progress_bar(0, len(cogs), f"\nInitializing cogs:           ")
            for i, cog in enumerate(cogs):
                time.sleep(0.3)
                print_startup_progress_bar(i + 1, len(cogs), f"Loading:{' ' * (20 - len(cog))} {cog}")
                await self.load_extension(f"cogs.{cog}")

        time.sleep(0.3)
        print_coloured(Colour.Yellow, f"\n\nInitialising bot, please wait...\n")

        # initialise tickets

        print_coloured(Colour.Green, f"Cogs loaded \"{general_config.message_commands_prefix}\"")
        print_coloured(Colour.Green, f"√ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √")


config_manager: ConfigManager = ConfigManager(pathlib.Path("config"), BOT_CONFIGS)

database_manager: DatabaseManager = DatabaseManager(config_manager["secrets"].db_connection_string,
                                                    "revidle-wikibot", MONGO_COLLECTIONS)

prefix = config_manager["general"].message_commands_prefix

bot: DiscordBot = DiscordBot(config_manager, database_manager, command_prefix=prefix,
                             case_insensitive=True, intents=intents)


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    """Handles errors raised during execution of message commands.

    :param ctx: The context the event is being invoked under.
    :param error: The exception that caused the event.
    """
    await handle_message_command_error(ctx, error)


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Handles errors raised during execution of application commands.

    :param interaction: The interaction that is being handled.
    :param error: The exception that was raised.
    """
    handle_app_command_error(interaction, error)


@bot.command()
@commands.is_owner()
async def sync(ctx: commands.Context, guilds: Greedy[discord.Object], spec: Optional[Literal["~", "*"]] = None):
    """Sync commands to discord.

    Umbra's sync command, found with `?tag umbras sync command` in dpy discord.
    Used to sync app commands from the bot to discord.

    How it works:
    -sync -> global sync.
    -sync ~ -> sync all guild commands for the current guild.
    -sync * -> copies all global app commands to current guild and syncs.
    -sync ^ -> clears all guild commands from the tree and syncs, removing all commands from the guild.
    -sync 123 456 789 -> syncs guilds with ids 123, 456 and 789, only syncing their guilds and guild-bound commands.

    :param ctx: The context the command was invoked under.
    :param guilds: The guilds to be synced.
    :param spec: Defines the behaviour and scope to be synced.
    """
    if not guilds:
        if spec == "~":
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "*":
            ctx.bot.tree.copy_global_to(guild=ctx.guild)
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "^":
            ctx.bot.tree.clear_commands(guild=ctx.guild)
            await ctx.bot.tree.sync(guild=ctx.guild)
            synced = []
        else:
            synced = await ctx.bot.tree.sync()

        await ctx.send(f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}")
        return

    ret = 0
    for guild in guilds:
        try:
            await ctx.bot.tree.sync(guild=guild)
        except discord.HTTPException:
            pass
        else:
            ret += 1

    await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")


@bot.command(name="reload", aliases=["-r"])
@dev_only
async def reload_cogs(ctx: commands.Context):
    """Reloads cogs while bot is still online."""
    cogs = bot.configs["cogs"].cogs
    if len(cogs) > 0:
        print_startup_progress_bar(0, len(cogs), f"\nInitializing cogs:                ")
        for i, cog in enumerate(cogs):
            time.sleep(0.4)
            print_startup_progress_bar(i + 1, len(cogs), f"Loading:{' ' * (20 - len(cog))} {cog}")
            await bot.reload_extension(f"cogs.{cog}")
    print_coloured(Colour.Yellow, f"\n\nInitialising bot, please wait...\n")
    print_coloured(Colour.Green, f"Cogs loaded \"{bot.configs['general'].message_commands_prefix}\"")
    await ctx.send(f"`Cogs reloaded by:` <@{ctx.author.id}>", allowed_mentions=discord.AllowedMentions(users=False))

@bot.command(name="restart")
@dev_only
async def restart_bot(ctx: commands.Context):
    """Restarts the bot via a shell script"""
    subprocess.Popen(["sh", "restart_bot.sh"])


# TODO: add a global check to restrict command usage outside of allowed areas for people without specific roles
# see previous codebase for details

if __name__ == "__main__":
    bot_secrets: BotSecretsConfig = config_manager["secrets"]
    bot.run(bot_secrets.token)
