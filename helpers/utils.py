import typing
from datetime import datetime

import discord
from discord.ext import commands

from data_management.data_protocols import ConstantsConfig


def dev_check(ctx: typing.Union[commands.Context, discord.Interaction]):
    """Ensures the person running a command is one of the bot devs"""
    constants_config: ConstantsConfig = ctx.bot.configs["constants"]
    return ctx.author.id in constants_config.dev_users

def host_check(ctx: typing.Union[commands.Context, discord.Interaction]):
    """Ensures the person running a command is the bot host"""
    constants_config: ConstantsConfig = ctx.bot.configs["constants"]
    return ctx.author.id == constants_config.host_user

dev_only = commands.check(dev_check)

host_only = commands.check(host_check)

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