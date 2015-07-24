
import asyncio
import asyncio_mongo
import hashlib
import pickle

from leela.core.sessions import Session, AbstractSessionsManager, DEFAULT_EXPIRE_TIME
from leela.core.orm import AbstractDatabase
from leela.core.orm import QueryResult
from leela.core.orm import model_iterator


class MongoQueryResult(QueryResult):
    def __init__(self, db, model_class, query):
        self.__query = query
        self.__filter = None
        self.__limit = None
        self.__skip = None
        self.__ret_cnt = False
        self.__find_one = False

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

    @asyncio.coroutine
    def remove(self):
        collection = self.__db[self.__metaname]
        result = yield from collection.remove(self.__query)
        return result

    def sort(self, **order):
        '''order = {field: ASC | DESC , ...}
        '''
        for field, direction in order.items():
            if field == self.__idkey:
                field = '_id'
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

    def skip(self, cnt):
        self.__skip = cnt
        return self

    def count(self):
        self.__ret_cnt = True
        return self

    def first(self):
        self.__find_one = True
        return self

    def __iter__(self):
        collection = self.__db[self.__metaname]
        params = {}
        if self.__limit:
            params['limit'] = self.__limit
        if self.__skip:
            params['skip'] = self.__skip
        if self.__filter:
            params['filter'] = self.__filter

        if self.__ret_cnt:
            cnt = yield from collection.count(self.__query)
            return cnt

        if self.__find_one:
            data = yield from collection.find(self.__query, **params)
            if not data:
                return None
            else:
                return list(model_iterator(self.__model_class, data))[0]

        data = yield from collection.find(self.__query, **params)

        return model_iterator(self.__model_class, data)


class MongoDB(AbstractDatabase):
    _query_result_class = MongoQueryResult
    __instance = None

    @classmethod
    def get_instance(cls):
        if not cls.__instance:
            raise RuntimeError('MongoDB instance does not initialized!')
        return cls.__instance

    @classmethod
    def initialize(cls, db_name):
        if cls.__instance:
            return cls.__instance

        return MongoDB(db_name)
        
    def __init__(self, db_name='leela'):
        super().__init__(db_name)
        self.__conn = None
        self.__db = None
        self.__class__.__instance = self

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



class MongoSessionsManager(AbstractSessionsManager):
    def __init__(self, expire_time=DEFAULT_EXPIRE_TIME):
        super().__init__(expire_time)
        self.__db = MongoDB.get_instance()

    @asyncio.coroutine
    def count(self):
        cnt = yield from self.__db['leela_sessions'].count({})
        return cnt

    @asyncio.coroutine
    def check_sessions(self):
        pass

    @asyncio.coroutine
    def get(self, session_id):
        session = yield from \
                  self.__db['leela_sessions'].find_one({'_id': session_id})

        if not session:
            return Session(None)
        return pickle.loads(session['data'])

    @asyncio.coroutine
    def set(self, session):
        session_id = session.get_id()
        if session_id is None:  # new session
            while True:
                session_id = self.random_uid()
                af = self.__db['leela_sessions'].find_one({'_id': session_id})
                if af:
                    break

        self.update_session_time(session)
        session.set_id(session_id)
        yield from self.__db['leela_sessions'].save(
                            {'_id': session_id, 'data': pickle.dumps(session)})
        session.modified = False

    @asyncio.coroutine
    def remove(self, session):
        session_id = session.get_id()
        if (session_id is None):
            return False

        yield from self.__db['leela_sessions'].remove({'_id': session_id})
        return True
