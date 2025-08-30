from typing import Protocol, Union


class BotSecretsConfig(Protocol):
    token: str
    db_connection_string: str
    db_name: str
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
    tag_editors: dict[str, list[int]]


class TagCollectionEntry(Protocol):
    id_: str
    content: str
    aliases: list[str]
    author: int
    created_at: int
    last_editor: int
    last_edit: int


class SettingsEntry(Protocol):
    class PermissionsCondition(Protocol):
        condition: str
        left: Union[str, "PermissionsCondition"]
        right: Union[str, "PermissionsCondition"]

    id_: str
    prefix: str
    disabled_commands: list[str]
    disabled_events: list[str]
    permissions: dict[str, Union[PermissionsCondition,
                                dict[str, PermissionsCondition]]]
