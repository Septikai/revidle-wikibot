from typing import List

import discord


class TagModal(discord.ui.Modal):
    def __init__(self, title: str, aliases: List[str], content: str = ""):
        super().__init__(title=title)

        self.aliases = None
        self.aliases_input = discord.ui.TextInput(label="Aliases (Comma-Separated)", placeholder="Tag Aliases",
                                                  required=False, style=discord.TextStyle.short,
                                                  default=", ".join(aliases))

        self.content = None
        self.content_input = discord.ui.TextInput(label="Content", placeholder="Tag Content", required=True,
                                                  style=discord.TextStyle.long, default=content)

        self.add_item(self.aliases_input)
        self.add_item(self.content_input)

        self.response = None

    async def on_submit(self, interaction: discord.Interaction) -> None:
        self.aliases = [alias.strip() for alias in self.aliases_input.value.split(",")]
        self.content = self.content_input.value
        self.response = interaction.response
        self.stop()
