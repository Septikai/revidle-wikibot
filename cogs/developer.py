import ast
import subprocess

import discord
from discord.ext import commands

from bot import DiscordBot
from data_management.data_protocols import ConstantsConfig, GeneralConfig
from helpers.utils import host_only, dev_only


def insert_returns(body):
    # insert return stmt if the last expression is a expression statement
    if isinstance(body[-1], ast.Expr):
        body[-1] = ast.Return(body[-1].value)
        ast.fix_missing_locations(body[-1])


class Developer(commands.Cog):
    """Developer-only commands."""

    def __init__(self, bot: DiscordBot):
        """Initialise the Developer cog.

        :param bot: The DiscordBot instance.
        """
        self.bot = bot
        general_config: GeneralConfig = self.bot.configs["general"]
        self.prefix = general_config.default_settings["prefix"]
        super().__init__()

    @commands.command(name="eval", hidden=True, aliases=["eval_fn", "-e"])
    @host_only
    async def eval_fn_command(self, ctx: commands.Context, *, cmd: str):
        """Evaluates input. Will be removed when bot development is mostly complete.
        Input is interpreted as newline seperated statements.
        If the last statement is an expression, that is the return value.
        Usable globals:
        - `bot`: the bot instance
        - `discord`: the discord module
        - `commands`: the discord.ext.commands module
        - `ctx`: the invocation context
        - `configs`: the bot configs
        - `__import__`: the builtin `__import__` function
        Such that `>eval 1 + 1` gives `2` as the result.
        The following invocation will cause the bot to send the text '9'
        to the channel of invocation and return '3' as the result of evaluating
        >eval ```
        a = 1 + 2
        b = a * 2
        await ctx.send(a + b)
        a
        ```
        """
        constants_config: ConstantsConfig = self.bot.configs["constants"]
        if ctx.author.id == constants_config.host_user:
            fn_name = "_eval_expr"

            cmd = cmd.strip("`")

            # add a layer of indentation
            cmd = "\n".join(f"    {i}" for i in cmd.splitlines())

            # wrap in async def body
            body = f"async def {fn_name}():\n{cmd}"

            parsed = ast.parse(body)
            body = parsed.body[0].body

            insert_returns(body)

            env = {
                "bot": ctx.bot,
                "discord": discord,
                "commands": commands,
                "ctx": ctx,
                "configs": self.bot.configs,
                "__import__": __import__
            }

            try:
                exec(compile(parsed, filename="<ast>", mode="exec"), env)
                result = (await eval(f"{fn_name}()", env))
                await ctx.send(f"```py\n{result}\n```")
            except Exception as e:
                await ctx.send(f"An exception occurred:```py\n{e}\n```")

    @commands.command(name="host_eval", hidden=True, aliases=["-he"])
    @host_only
    async def host_eval_command(self, ctx: commands.Context, *, args):
        """Eval but straight into the host machine.
        Will be removed when bot development is mostly complete."""
        # Especially useful for pulling changes from discord without having to ssh into host machine
        constants_config: ConstantsConfig = self.bot.configs["constants"]
        if ctx.author.id == constants_config.host_user:
            await ctx.send(f"```\n{subprocess.check_output(args.split(' ')).decode('utf-8')[:1900]}\n```")

    @commands.command(name="update", hidden=True, aliases=["-u", "~u"])
    @dev_only
    async def update_bot(self, ctx: commands.Context, branch: str = "main"):
        """Update the bot from git"""
        constants_config: ConstantsConfig = self.bot.configs["constants"]
        if ctx.author.id in constants_config.dev_users:
            command = ['git', 'pull', 'origin', 'dev' if branch == 'dev' else 'main']
            await ctx.send(f"```\n{subprocess.check_output(command).decode('utf-8')[:1900]}\n```")


async def setup(bot: DiscordBot):
    """Add the Developer cog to the bot.

    :param bot: The DiscordBot instance.
    """
    await bot.add_cog(Developer(bot))
