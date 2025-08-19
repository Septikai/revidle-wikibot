import typing

from discord.ext import commands

from data_management.database_manager import MongoInterface
from helpers import logic


class SettingsInterface(MongoInterface):
    """A proxy to the database collection that keeps all data up-to-date on reloads."""
    def __init__(self, collection: str, defaults: dict):
        super().__init__(collection)
        self.defaults = defaults
        self._cached_checks: dict[str, dict] = {}

    def __getitem__(self, id_: int):
        return self.__getattr__(str(id_))

    async def get_one(self, id_: int):
        try:
            return await super().get_one(str(id_))
        except ValueError:
            await self.insert_one(id_)
            return await super().get_one(str(id_))

    async def insert_one(self, id_: int, **kwargs):
        await super().insert_one(str(id_), **self.defaults)

    async def update_one(self, id_: int, **kwargs):
        await super().update_one(str(id_))

    async def get_all(self, filter_: dict[str, typing.Any] = None):
        return await super().get_all(filter_)

    async def search_all(self, filter_: dict[str, typing.Any] = None):
        return await super().search_all(filter_)

    async def remove_one(self, id_: int):
        await super().remove_one(str(id_))

    async def get_permissions_check(self, ctx: commands.Context, event_type: str = ""):
        # Initialise vars
        permissions = (await self.get_one(ctx.guild.id))["permissions"]
        to_cache = []
        parsed_all = None
        parsed_cog = None
        parsed_command = None
        parsed_event = None
        checks = []

        # Search cache
        if str(ctx.guild.id) in self._cached_checks:
            guild_cache = self._cached_checks[str(ctx.guild.id)]
            if "all" in guild_cache:
                parsed_all = guild_cache["all"]
            else:
                to_cache.append(1)
            if event_type == "":
                if "cogs" in guild_cache and ctx.command.cog_name in guild_cache["cogs"]:
                    parsed_cog = guild_cache["cogs"][ctx.command.cog_name]
                else:
                    to_cache.append(2)
                if "commands" in guild_cache and ctx.command.qualified_name in guild_cache["commands"]:
                    parsed_command = guild_cache["commands"][ctx.command.qualified_name]
                else:
                    to_cache.append(3)
            else:
                if event_type in guild_cache["events"]:
                    parsed_event = guild_cache["events"][event_type]
                else:
                    to_cache.append(4)

        else:
            to_cache.extend([0, 1, 2, 3, 4])

        # Parse checks from settings
        if event_type == "":
            if parsed_all is None and "all" in permissions and len(permissions["all"].items()) != 0:
                parsed_all = await logic.parse_dict(ctx, permissions["all"])
            if parsed_cog is None and "cogs" in permissions and ctx.command.cog_name in permissions["cogs"]:
                parsed_cog = await logic.parse_dict(ctx, permissions["cogs"][ctx.command.cog_name])
            if parsed_command is None and "commands" in permissions and ctx.command.qualified_name in permissions["cogs"]:
                parsed_command = await logic.parse_dict(ctx, permissions["commands"][ctx.command.qualified_name])
        else:
            if parsed_event is None and len(permissions["events"].items()) != 0:
                parsed_event = await logic.parse_dict(ctx, permissions["events"][event_type])

        # Append and cache checks
        if 0 in to_cache:
            self._cached_checks[str(ctx.guild.id)] = {
                "all": None,
                "cogs": {},
                "commands": {},
                "events": {}
            }
        if parsed_all is not None:
            checks.append(parsed_all)
            if 1 in to_cache:
                self._cached_checks[str(ctx.guild.id)]["all"] = parsed_all
        if parsed_cog is not None:
            checks.append(parsed_cog)
            if 2 in to_cache:
                self._cached_checks[str(ctx.guild.id)]["cogs"][ctx.command.cog_name] = parsed_cog
        if parsed_command is not None:
            checks.append(parsed_command)
            if 3 in to_cache:
                self._cached_checks[str(ctx.guild.id)]["commands"][ctx.command.qualified_name] = parsed_command
        if parsed_event is not None:
            checks.append(parsed_event)
            if 4 in to_cache:
                self._cached_checks[str(ctx.guild.id)]["events"][event_type] = parsed_event

        # Build and return check
        if len(checks) == 1:
            return checks[0]
        if len(checks) == 2:
            return logic.BooleanLogic.AndOperator(checks[0], checks[1])
        if len(checks) == 3:
            return logic.BooleanLogic.AndOperator(checks[0], logic.BooleanLogic.AndOperator(checks[1], checks[2]))
        return None


