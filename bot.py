import os
import pathlib
import subprocess
import time
from datetime import datetime
from typing import Optional, Literal

import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ext.commands import Greedy

from data_management.config_manager import ConfigManager
from data_management.data_protocols import GeneralConfig, CogsConfig, BotSecretsConfig
from data_management.database_manager import DatabaseManager
from data_management.settings_interface import SettingsInterface
from data_management.wiki_interface import WikiInterface
from error_handlers import handle_message_command_error, handle_app_command_error
from helpers.graphics import print_coloured, Colour, print_startup_progress_bar
from helpers.utils import dev_only

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

BOT_CONFIGS = {
    "secrets",
    "general",
    "cogs",
    "constants"
}

MONGO_COLLECTIONS = {
    "settings",
    "tags"
}


class DiscordBot(commands.Bot):
    """The DiscordBot instance."""
    def __init__(self, configs: ConfigManager, collections: DatabaseManager, settings: SettingsInterface,
                 *args, **kwargs):
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
        self.settings: SettingsInterface = settings

        # Make the help command not be case-sensitive
        self._BotBase__cogs = commands.core._CaseInsensitiveDict()

        # Set time for DB clean
        # This could be set in the past to clean immediately, but that could cause issues if
        # restarting several times in quick succession
        self.last_database_clean = datetime.now()

    async def setup_hook(self):
        """Runs on bot startup to load cogs and initialise the bot."""

        print_coloured(Colour.Yellow, f"Loading the bot: {self.user.name}!\n")

        time.sleep(1)

        # initialise self.var = ...

        print_coloured(Colour.Yellow, f"Connecting to the wiki...\n")

        self.wiki = WikiInterface(self.configs["secrets"].user_agent, self.configs["constants"].max_mw_query_len,
                                  self.configs["constants"].wiki_base_url)

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

        # Start DB clean task loop
        clean_database.start()

        print_coloured(Colour.Green, f"Cogs loaded \"{general_config.default_settings['prefix']}\"")
        print_coloured(Colour.Green, f"√ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √ √")

async def get_prefix(_bot: DiscordBot, message: discord.Message):
    try:
        return (await _bot.settings.get_one(message.guild.id)).prefix
    except ValueError:
        return _bot.configs["general"].default_settings['prefix']



config_manager: ConfigManager = ConfigManager(pathlib.Path("config"), BOT_CONFIGS)

database_manager: DatabaseManager = DatabaseManager(config_manager["secrets"].db_connection_string,
                                                    config_manager["secrets"].db_name, MONGO_COLLECTIONS)

settings_manager: SettingsInterface = SettingsInterface(database_manager.get_settings(), config_manager["general"].default_settings)

bot: DiscordBot = DiscordBot(config_manager, database_manager, settings_manager,
                             command_prefix=get_prefix, case_insensitive=True, intents=intents)


@bot.check
async def global_permissions_check(ctx: commands.Context):
    check = await bot.settings.get_permissions_check(ctx)
    return True if check is None else check.evaluate(ctx)



@tasks.loop(hours=24)
async def clean_database():
    # Only clean the db if it's been 7 days since the last clean
    # Privacy Policy states 14 days, so this accounts for bot restarts delaying the clean by up to a week
    if (datetime.now() - bot.last_database_clean).days < 7:
        return
    # Get all settings
    settings = await bot.settings.get_all()
    to_remove = []
    # Find servers the bot is no longer in
    for entry in settings:
        guild = bot.get_guild(int(entry.id_))
        if guild is None:
            to_remove.append(int(entry.id_))
    # Remove data for servers the bot is no longer in
    for id_ in to_remove:
        await bot.settings.remove_one(id_)


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
    await handle_app_command_error(interaction, error)


@bot.command()
@commands.is_owner()
async def sync(ctx: commands.Context, guilds: Greedy[discord.Object],
               spec: Optional[Literal["~", "*", "^"]] = None) -> None:
    """Sync commands to discord.

    Umbra's sync command, found here: https://about.abstractumbra.dev/discord.py/2023/01/29/sync-command-example.html.
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


@bot.command(name="reload", aliases=["-r", "~r"])
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
    print_coloured(Colour.Green, f"Cogs loaded \"{bot.configs['general'].default_settings['prefix']}\"")
    await ctx.send(f"`Cogs reloaded by:` <@{ctx.author.id}>",
                   allowed_mentions=discord.AllowedMentions(users=False))

@bot.command(name="reloadconfig", aliases=["-rc", "~rc"])
@dev_only
async def reload_config(ctx: commands.Context):
    """Reloads configs while bot is still online"""
    bot.configs.reload()
    await ctx.send(f"`Configs reloaded by:` <@{ctx.author.id}>",
                   allowed_mentions=discord.AllowedMentions(users=False))

@bot.command(name="restart")
@dev_only
async def restart_bot(ctx: commands.Context):
    """Restarts the bot via a shell script"""
    await ctx.send("`Restarting bot...`")
    subprocess.Popen(["sh", "restart_bot.sh"], stdout=open("/dev/null", "w"), stderr=open("/dev/null", "w"),
                     preexec_fn=os.setpgrp)

if __name__ == "__main__":
    bot_secrets: BotSecretsConfig = config_manager["secrets"]
    bot.run(bot_secrets.token)
