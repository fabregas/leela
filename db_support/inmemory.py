

import asyncio
from core.orm import AbstractDatabase, QueryResult, model_iterator

class InMemoryQueryResult(QueryResult):
    def __init__(self, db, model_class, query):
        self.__query = query
        self.__db = db
        self.__model_class = model_class
        self.__idkey = self.__model_class._id

    @asyncio.coroutine
    def upsert(self):
        key = None
        if self.__idkey in self.__query:
            key = self.__query[self.__idkey]
        return self.__db.save(self.__model_class._meta_name, key, self.__query)

    @asyncio.coroutine
    def __iter__(self):
        key = None
        if self.__idkey in self.__query:
            key = self.__query[self.__idkey]

        ret = self.__db.get(self.__model_class._meta_name, key)
        yield
        if not ret:
            ret = []
        else:
            ret = [ret]
        return model_iterator(self.__model_class, ret)


class InMemoryDatabase(AbstractDatabase):
    _query_result_class = InMemoryQueryResult

    def __init__(self, db_name=''):
        super().__init__(db_name)

        self.__data = {}

    def save(self, model_name, key, value):
        if model_name not in self.__data:
            self.__data[model_name] = {}

        if key is None:
            while True:
                key = getid(32)
                if key not in self.__data[model_name]:
                    break

        self.__data[model_name][key] = value

    def get(self, model_name, key):
        if model_name not in self.__data:
            return None
        return self.__data[model_name].get(key, None)

