import typing
from typing import Set

from motor.motor_asyncio import AsyncIOMotorClient


class CollectionEntry:
    """
    A proxy to a collection entry that keeps all data up-to-date on reloads.

    It's not recommended to refer to this class directly; prefer defining a Protocol class with your entry values for
    better type hinting in your IDE.
    """

    def __init__(self, data: dict):
        data["id_"] = data["_id"]
        self._data: dict = data

    def __getattr__(self, key: str):
        value = self._data.get(key)
        if value is None:
            raise ValueError(f"Invalid entry key: {key}")

        return value

    def __getitem__(self, key: str):
        value = self._data.get(key)
        if value is None:
            raise ValueError(f"Invalid entry key: {key}")

        return value


class MongoInterface:
    """
    A proxy to the database collection that keeps all data up-to-date on reloads.
    """
    def __init__(self, collection):
        self._collection = collection
        self._all_loaded = False
        self._data: dict[str, CollectionEntry] = {}

    def __getattr__(self, id_: str):
        entry = self._data.get(id_)
        if entry is None:
            raise ValueError(f"Invalid database entry ID: {id_}\nAccessing in this method only includes cached entries"
                             f"\nPlease use {self.get_one.__qualname__} to avoid that")

        return entry

    def get_collection(self):
        return self._collection

    def reload(self):
        self._data = {}
        self._all_loaded = False

    async def get_one(self, id_: str):
        if id_ in self._data:
            return self._data[id_]

        raw_entry = await self._collection.find_one({"_id": id_})
        if raw_entry is None:
            raise ValueError(f"Invalid database entry ID: {id_}")

        entry = CollectionEntry(raw_entry)
        self._data[id_] = entry
        return entry

    async def get_all(self, filter_: dict[str, typing.Any] = None):
        if filter_ is None:
            filter_ = {}

        if self._all_loaded:
            return [entry[1] for entry in self._data.items() if
                    len([False for key, val in filter_ if entry[key] != val]) == 0]

        data = {entry["_id"]: CollectionEntry(entry) async for entry in self._collection.find(filter_)}

        if len(filter_) == 0:
            self._data = data
            self._all_loaded = True

        return data.values()

    async def search_all(self, filter_: dict[str, typing.Any] = None):
        if filter_ is None:
            filter_ = {}

        if self._all_loaded:
            return [entry[1] for entry in self._data.items() if
                    len([False for key, val in filter_.items() if val not in entry[1][key]]) == 0]

        query = {key: {"$regex": val} for key, val in filter_.items()}
        data = {entry["_id"]: CollectionEntry(entry) async for entry in self._collection.find(query)}

        if len(filter_) == 0:
            self._data = data
            self._all_loaded = True

        return data.values()

    async def insert_one(self, id_: str, **kwargs):
        if id_ != "":
            if id_ in self._data:
                raise ValueError(f"Entry already exists with ID: {id_}")
            kwargs["_id"] = id_
        # TODO: insert into database
        #  raise error if it fails to add
        if "_id" in kwargs:
            self._data[kwargs["_id"]] = CollectionEntry(kwargs)
        self._all_loaded = False
        await self._collection.insert_one(kwargs)
        if "_id" not in kwargs:
            # TODO: use the id mongo generates
            pass

    async def update_one(self, id_: str, **kwargs):
        if id_ not in self._data:
            raw_entry = await self._collection.find_one({"_id": id_})
            if raw_entry is None:
                raise ValueError(f"Invalid database entry ID: {id_}")
        entry = await self._collection.update_one({"_id": id_}, {"$set": kwargs})
        self._data[id_] = CollectionEntry(await self._collection.find_one({"_id": id_}))

    async def remove_one(self, id_: str):
        if id_ not in self._data:
            raw_entry = await self._collection.find_one({"_id": id_})
            if raw_entry is None:
                raise ValueError(f"Invalid database entry ID: {id_}")
        if id_ in self._data:
            del self._data[id_]
        await self._collection.delete_one({"_id": id_})


class DatabaseManager:
    """
    Base class for working with MongoDB databases.

    Reloading the manager automatically reloads all used databases; don't call ``__reload__()`` on collections directly.

    Basic use (for adding a database to a cog):

    - Make a Protocol class that will define the type hints for your collection entries.

    - Add your collection to the list of loaded collections; see bot.py

    - Retrieve your collection in cog's __init__ method::

        self.collection: MyCollection = bot.collections["my_collection"]

    - Use the values in your code like::

        print(f"The answer to Life, the Universe, and Everything: {self.collection.the_answer}")
    """

    def __init__(self, connection_string: str, db_name: str, to_load: Set[str]):
        self._loaded_collections: dict[str, MongoInterface] = {}
        self.settings_initialised = False

        self._cluster = AsyncIOMotorClient(connection_string)
        self._db = self._cluster[db_name]

        for collection_id in to_load:
            self.load(collection_id)

    def __getitem__(self, item: str):
        """
        Get a collection proxy for a specified id.

        :param item: The collection id to retrieve.
        :return: The collection. That collection is refreshed automatically on reload.
        """
        if item == "settings" and self.settings_initialised:
            raise ValueError("Settings can only be accessed through `bot.settings`, not through `bot.collections`.")
        database = self._loaded_collections.get(item)
        if database is None:
            raise ValueError(f"Invalid database id: {item}")

        return database

    def get_settings(self):
        settings = self["settings"]
        self.settings_initialised = True
        return settings.get_collection()

    def load(self, collection_id: str):
        """
        Loads a **new** database collection.

        :param collection_id: The new collection id to load into the internal cache.
        :return: The newly loaded collection. That collection is refreshed automatically on reload.
        :raise RuntimeError: when the collection with that id already exists.
        """
        if collection_id in self._loaded_collections:
            raise RuntimeError(f"Collection {collection_id} is already loaded")

        new_collection = MongoInterface(self._db[collection_id])
        self._loaded_collections[collection_id] = new_collection
        return new_collection

    def __reload__(self) -> None:
        """
        Reloads all collections currently managed by this manager.
        """
        for collection in self._loaded_collections.values():
            collection.reload()
