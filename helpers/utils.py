from datetime import datetime

import discord


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
