from typing import Protocol, Union


class BotSecretsConfig(Protocol):
    token: str
    db_connection_string: str
    user_agent: str


class GeneralConfig(Protocol):
    default_settings: dict[str, Union[str, list, dict]]


class CogsConfig(Protocol):
    cogs: list[str]


class ConstantsConfig(Protocol):
    host_user: int
    dev_users: list[int]
    wiki_base_url: str
    max_mw_query_len: int


class TagCollectionEntry(Protocol):
    id_: str
    content: str
    aliases: list[str]
