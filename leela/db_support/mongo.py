
import asyncio
import asyncio_mongo
import hashlib

from leela.core.sessions import Session
from leela.core.orm import AbstractDatabase
from leela.core.orm import QueryResult
from leela.core.orm import model_iterator


class MongoQueryResult(QueryResult):
    def __init__(self, db, model_class, query):
        self.__query = query
        self.__filter = None
        self.__limit = None

        self.__db = db
        self.__model_class = model_class
        self.__metaname = model_class._meta_name
        self.__idkey = model_class._id

        if self.__idkey in self.__query:
            idval = self.__query[self.__idkey]
            del self.__query[self.__idkey]
            self.__query['_id'] = idval

    @asyncio.coroutine
    def upsert(self):
        collection = self.__db[self.__metaname]
        result = yield from collection.save(self.__query)
        return result

    def sort(self, **order):
        '''order = {field: ASC | DESC , ...}
        '''
        for field, direction in order.items():
            if direction < 0:
                direct = asyncio_mongo.filter.DESCENDING
            else:
                direct = asyncio_mongo.filter.ASCENDING
            sf = asyncio_mongo.filter.sort(direct(field))
            if not self.__filter:
                self.__filter = sf
            else:
                self.__filter += sf
        return self

    def hint(self, index, direction=-1):
        if direction < 0:
            direct = asyncio_mongo.filter.DESCENDING
        else:
            direct = asyncio_mongo.filter.ASCENDING
        hint = asyncio_mongo.filter.hint(direct(index))
        if not self.__filter:
            self.__filter = hint
        else:
            self.__filter += hint
        return self

    def limit(self, cnt):
        self.__limit = cnt
        return self

    def __iter__(self):
        collection = self.__db[self.__metaname]
        params = {}
        if self.__limit:
            params['limit'] = self.__limit
        if self.__filter:
            params['filter'] = self.__filter

        data = yield from collection.find(self.__query, **params)

        return model_iterator(self.__model_class, data)


class MongoDB(AbstractDatabase):
    _query_result_class = MongoQueryResult

    def __init__(self, db_name='leela'):
        super().__init__(db_name)
        self.__conn = None
        self.__db = None

    def connect(self, host='localhost', port=27017, auto_reconnect=True):
        self.__conn = yield from \
            asyncio_mongo.Connection.create(host, port, None, auto_reconnect)
        self.__db = self.__conn[self.db_name()]
        return self

    def __getitem__(self, collection):
        if self.__conn is None:
            raise RuntimeError('MongoDB connection should be initialized!')
        return self.__db[collection]

    def __getattr__(self, collection):
        return self[collection]

    def __repr__(self):
        return repr(self.__conn)

    def drop_database(self):
        collections = yield from self.__db.collection_names()
        for collection in collections:
            yield from self.__db.drop_collection(collection)

    @asyncio.coroutine
    def disconnect(self):
        if self.__conn is not None:
            closed = yield from self.__conn.disconnect()


