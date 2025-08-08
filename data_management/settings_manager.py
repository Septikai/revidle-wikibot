import typing

from data_management.database_manager import MongoInterface, CollectionEntry


class SettingsInterface(MongoInterface):
    """A proxy to the database collection that keeps all data up-to-date on reloads."""
    def __init__(self, collection: str, defaults: dict):
        super().__init__(collection)
        self.defaults = defaults

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
