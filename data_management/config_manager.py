import json
import pathlib
from typing import Set


class ConfigView:
    """
    A proxy to the config file that keeps all data up-to-date on reloads.

    It's not recommended to refer to this class directly; prefer defining a Protocol class with your config values for
    better type hinting in your IDE.
    """

    def __init__(self, filepath: pathlib.Path):
        self._filepath: pathlib.Path = filepath
        self._data: dict = _load_config_data(filepath)

    def __getattr__(self, item: str):
        value = self._data.get(item)
        if value is None:
            raise ValueError(f"Invalid config key: {item}")

        return value

    def __reload(self):
        self._data = _load_config_data(self._filepath)


class ConfigManager:
    """
    Base class for working with configuration files.

    Configs are immutable and can only be read by the bot.

    Reloading the manager automatically reloads all used configs; don't call ``__reload()`` on configs directly.

    Basic use (for adding a config to a cog):

    - Make a Protocol class that will define the type hints for your config file.

    - Add your config file to the list of loaded configs; see bot.py

    - Retrieve your config in cog's __init__ method::

        self.config: MyCogConfig = bot.configs["my_cog"]

    - Use the values in your code like::

        print(f"The answer to Life, the Universe, and Everything: {self.config.the_answer}")
    """

    def __init__(self, base_directory: pathlib.Path, to_load: Set[str]):
        self._base_directory: pathlib.Path = base_directory

        self._loaded_configs: dict[str, ConfigView] = {}

        for config_id in to_load:
            self.load(config_id)

    def __getitem__(self, item: str):
        """
        Get a config proxy for a specified id.

        :param item: The config id to retrieve.
        :return: The config. That config is refreshed automatically on reload.
        """
        config = self._loaded_configs.get(item)
        if config is None:
            raise ValueError(f"Invalid config id: {item}")

        return config

    def load(self, config_id: str):
        """
        Loads a **new** config file.

        :param config_id: The new config id to load into the internal cache.
        :return: The newly loaded config. That config is refreshed automatically on reload.
        :raise RuntimeError: when the config with that id already exists.
        """
        if config_id in self._loaded_configs:
            raise RuntimeError(f"Config {config_id} is already loaded")

        new_config = ConfigView(self._base_directory / f"{config_id}.json")
        self._loaded_configs[config_id] = new_config
        return new_config

    def reload(self) -> None:
        """
        Reloads all configs currently managed by this manager.
        """
        for config in self._loaded_configs.values():
            config.__reload()


def _read_json_file(filepath: pathlib.Path) -> dict:
    """Reads a JSON file"""
    with filepath.open("r") as f:
        obj = json.load(f)

    return obj


def _load_config_data(filepath: pathlib.Path) -> dict:
    """Loads a JSON file"""
    try:
        return _read_json_file(filepath)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Failed to load config data from {filepath}") from e
