import traceback

import discord
from discord import app_commands
from discord.ext import commands


def handle_message_command_error(ctx: commands.Context, err: commands.CommandError):
    """Handles errors raised during execution of message commands.

    :param ctx: The context the event is being invoked under.
    :param err: The exception that caused the event.
    """
    print("Error Caught:")
    print(traceback.format_exc())


def handle_app_command_error(interaction: discord.Interaction, err: app_commands.AppCommandError):
    """Handles errors raised during execution of application commands.

    :param interaction: The interaction that is being handled.
    :param err: The exception that was raised.
    """
    # TODO: uncomment this
    # print("Error Caught:")
    # print(traceback.format_exc())
