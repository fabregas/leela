
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
        self.__sort = []
        self.__hint = []
        self.__explain = False

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
        # for field, direction in order.items():
        #     self.__sort.append(asyncio_mongo.filter.DESCENDING("something"))
        return self

    def hint(self, index):
        return self

    def explain(self):
        return self

    def __iter__(self):
        collection = self.__db[self.__metaname]
        data = yield from collection.find(self.__query)
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

    def set_session(self, session):
        key = session.get_id()
        value = session.dump()
        yield from self['leela_sessions'].insert({'_id': key, 'value': value})

    def get_session(self, key, default=None):
        ret = yield from self['leela_sessions'].find_one({'_id': key})
        if len(ret) == 0:
            return default
        return Session.load(ret['value'])

    def del_session(self, session):
        key = session.get_id()
        yield from self['leela_sessions'].remove({'_id': key})

    def add_user(self, user):
        self['leela_users'].insert({'_id'})

    def get_user(self, username):
        pass

    def update_user(self, user):
        pass

    def delete_user(self, user):
        pass
