import math

import discord
from discord import app_commands
from discord.ext import commands


async def handle_message_command_error(ctx: commands.Context, err: commands.CommandError):
    """Handles errors raised during execution of message commands.

    :param ctx: The context the event is being invoked under.
    :param err: The exception that caused the event.
    """
    # if command has local error handler, return
    if hasattr(ctx.command, "on_error"):
        return

    error = getattr(err, "original", err)

    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.BotMissingPermissions):
        missing = [perm.replace("_", " ").replace("guild", "server").title() for perm in error.missing_permissions]
        if len(missing) > 2:
            fmt = "{}, and {}".format("**, **".join(missing[:-1]), missing[-1])
        else:
            fmt = " and ".join(missing)
        _message = "I need the **{}** permission(s) to run this command.".format(fmt)
        return await ctx.send(_message)

    if isinstance(error, commands.MissingRole) or isinstance(error, commands.MissingAnyRole):
        if isinstance(error, commands.MissingAnyRole):
            roles = error.missing_roles
        else:
            roles = [error.missing_role]
        roles = [ctx.guild.get_role(z).mention for z in roles]
        embed = discord.Embed(title=":x: Error! You must have one of these roles: :x:",
                              description="\n".join(roles), colour=0xff0000)
        return await ctx.send(embed=embed)

    if isinstance(error, commands.DisabledCommand):
        return await ctx.send("This command has been disabled.")

    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send("This command is on cooldown, please retry in {}s.".format(math.ceil(error.retry_after)))
        return

    if isinstance(error, commands.MissingPermissions):
        return await ctx.send("You do not have permission to use this command.")

    if isinstance(error, commands.UserInputError):
        # await ctx.send_help(ctx.command)
        desc = f"Correct usage: `{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}`"
        if isinstance(ctx.command, (commands.Group, commands.HybridGroup)):
            subcommands = "`, `".join([command.name for command in ctx.command.commands])
            desc = desc + f"\nValid Subcommands:\n`{subcommands}`"
        if len(error.args) != 0:
            desc = f"{error.args[0]}\n\n" + desc
        embed = discord.Embed(title=":x: Invalid Input!",
                              description=desc,
                              color=0xff0000)
        return await ctx.send(embed=embed)

    if isinstance(error, commands.NoPrivateMessage):
        try:
            await ctx.author.send("This command cannot be used in direct messages.")
        except discord.Forbidden:
            pass
        return

    if isinstance(error, commands.CheckFailure):
        return

    if isinstance(error, discord.Forbidden):
        return await ctx.send("I do not have permission to perform an action for that command")

    print("Error Caught:")
    print(error)


def handle_app_command_error(interaction: discord.Interaction, err: app_commands.AppCommandError):
    """Handles errors raised during execution of application commands.

    :param interaction: The interaction that is being handled.
    :param err: The exception that was raised.
    """
    # if command has local error handler, return
    if hasattr(interaction.command, "on_error"):
        return

    error = getattr(err, "original", err)
    print("Error Caught:")
    print(error)
