import asyncio
import typing
from datetime import datetime

import discord
from discord.ext import commands

from data_management.data_protocols import ConstantsConfig, GeneralConfig


def tag_editor_check(ctx: typing.Union[commands.Context, discord.Interaction]):
    """Ensures the person running a command is allowed to modify tags"""
    constants_config: ConstantsConfig = ctx.bot.configs["constants"]
    if not str(ctx.guild.id) in constants_config.tag_editors:
        return False
    roles = role_ids(ctx.author.roles)
    return list_one(roles, *constants_config.tag_editors[str(ctx.guild.id)])

def dev_check(ctx: typing.Union[commands.Context, discord.Interaction]):
    """Ensures the person running a command is one of the bot devs"""
    constants_config: ConstantsConfig = ctx.bot.configs["constants"]
    return ctx.author.id in constants_config.dev_users

def host_check(ctx: typing.Union[commands.Context, discord.Interaction]):
    """Ensures the person running a command is the bot host"""
    constants_config: ConstantsConfig = ctx.bot.configs["constants"]
    return ctx.author.id == constants_config.host_user

def stable_bot_check(ctx: typing.Union[commands.Context, discord.Interaction]):
    """Ensures the running bot is not the development bot"""
    # This is done by checking the default prefix is "-"
    general_config: GeneralConfig = ctx.bot.configs["constants"]
    return general_config.default_settings["prefix"] == "-"

tag_editors_only = commands.check(tag_editor_check)

dev_only = commands.check(dev_check)

host_only = commands.check(host_check)

stable_bot_only = commands.check(stable_bot_check)


class Embed(discord.Embed):
    """Used for creating an easily customisable discord.Embed object"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def embed_colour(self):
        """Assign a colour to the embed"""
        # optionally get a custom colour
        # if there is no custom colour:
        self.colour = 0x006798
        return self

    def timestamp_now(self):
        """Add a current timestamp to the embed"""
        self.timestamp = datetime.now()


class RoleConverter(commands.Converter):
    abbreviations = {}

    async def convert(self, ctx: commands.Context, argument: str) -> discord.Role:
        role = None
        try:
            role = await commands.RoleConverter().convert(ctx, argument)
        except commands.RoleNotFound:
            if argument.lower() in self.abbreviations:
                role = ctx.guild.get_role(self.abbreviations[argument.lower()])
            else:
                role_list_lower = {z.name.lower(): z for z in ctx.guild.roles}
                if argument.lower() in role_list_lower:
                    role = role_list_lower[argument.lower()]
                else:
                    candidates = []
                    for name in role_list_lower:
                        if argument.lower() in name:
                            candidates.append(role_list_lower[name])
                    if len(candidates) == 1:
                        role = candidates[0]
                    elif len(candidates) > 1:
                        decision_msg = await ctx.send(
                            embed=discord.Embed(title="Which role?",
                                                description="\n".join([f"{i + 1} : {z.mention}" for i, z in
                                                                       enumerate(candidates)]),
                                                colour=discord.Colour.green()))
                        try:
                            res = await ctx.bot.wait_for("message", check=lambda
                                  msg: msg.author.id == ctx.author.id and msg.channel.id == ctx.channel.id, timeout=60)
                            number = int(res.content)
                            role = candidates[number - 1]
                            await decision_msg.delete()
                            await res.delete()
                        except asyncio.TimeoutError:
                            await ctx.send("Timed out")
                        except (ValueError, TypeError, IndexError):
                            await ctx.send("Invalid index")
        finally:
            if role:
                return role
            raise commands.RoleNotFound(argument)


def create_pages(data: list[str]):
    items = []
    count = 1
    for i, item in enumerate(data):
        items.append(f"{count}. {item}\n")
        count += 1
    pages = [discord.Embed(colour=0x006798)]
    values = [""]
    page_index = 0
    for i, item in enumerate(items):
        values[page_index] += item
        if not ((i + 1) % 15) and i != 0:
            pages.append(discord.Embed(colour=0x006798))
            page_index += 1
            values.append("")
    pages = pages[:10]
    for i, page in enumerate(pages):
        page.set_footer(text=f"page {i + 1} of {len(pages)}")
        page.add_field(name="", value=values[i], inline=False)
    return pages

def role_ids(roles):
    return [z.id for z in roles]

def list_one(_list, *items):
    for item in items:
        if item in _list:
            return True
    return False
