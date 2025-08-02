from typing import Protocol


class BotSecretsConfig(Protocol):
    token: str
    db_connection_string: str
    user_agent: str


class CogsConfig(Protocol):
    cogs: list[str]


class GeneralConfig(Protocol):
    message_commands_prefix: str


class ConstantsConfig(Protocol):
    host_user: int


class TagCollectionEntry(Protocol):
    id_: str
    content: str
    aliases: list[str]
