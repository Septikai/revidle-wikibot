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


class FeedbackModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Feedback Form")

        self.feedback_type = None
        self.feedback_type_input = discord.ui.Select(options=[discord.SelectOption(label=option) for option in
                                                              ["Suggestion", "Bug Report"]],
                                                     placeholder="Feedback Type", min_values=1, max_values=1,
                                                     required=True)

        self.feedback_summary = None
        self.feedback_summary_input = discord.ui.TextInput(placeholder="Summarise your feedback...", required=True,
                                                           style=discord.TextStyle.short)

        self.feedback_description = None
        self.feedback_description_input = discord.ui.TextInput(placeholder="Explain your feedback...", required=True,
                                                               style=discord.TextStyle.long)

        self.add_item(discord.ui.Label(text="Feedback Type",
                                       description="Is your bot feedback a suggestion or bug report?",
                                       component=self.feedback_type_input))
        self.add_item(discord.ui.Label(text="Feedback Summary",
                                       description="Quickly summarise your feedback - what is your suggestion or bug report?",
                                       component=self.feedback_summary_input))
        self.add_item(discord.ui.Label(text="Feedback Description",
                                       description="Explain your feedback in detail - the more detail, the more likely "
                                                   "we are to be able to act on it.",
                                       component=self.feedback_description_input))

        self.response = None

    async def on_submit(self, interaction: discord.Interaction) -> None:
        self.feedback_type = self.feedback_type_input.values[0]
        self.feedback_summary = self.feedback_summary_input.value
        self.feedback_description = self.feedback_description_input.value
        self.response = interaction.response
        self.stop()
