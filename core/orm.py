
import inspect
import asyncio
from copy import copy



class ModelMeta(type):
    def __init__(cls, name, bases, dct):
        super(ModelMeta, cls).__init__(name, bases, dct)
        cls.__detect_f_keys()
        cls.set_f_keys(cls.__detect_f_keys())

        if cls._meta_name == 'model':
            cls._meta_name = cls.__name__.lower()

        if cls._id is None:
            cls._id = '_id'

    def __detect_f_keys(cls):
        f_keys = {}
        for key in dir(cls):
            if key[0] == '_':
                continue
            value = getattr(cls, key)
            if inspect.isroutine(value):
                continue
            f_keys[key] = value
        return f_keys


class Model(object, metaclass=ModelMeta):
    __db = None
    __query_result_class = None
    __f_keys = None
    
    _meta_name = 'model'
    _id = None
    
    @classmethod
    def init(cls, db):
        cls.__db = db
        cls.__query_result_class = db.get_query_result_class()

    @classmethod
    def set_f_keys(cls, f_keys):
        cls.__f_keys = f_keys

    def __init__(self, **args):
        self.__args = copy(self.__f_keys)
        for arg, val in args.items():
            if arg[0] != '_' and arg not in self.__f_keys:
                raise RuntimeError('"{}" attribute does not found for "{}"'.
                                    format(arg, self.__class__.__name__))
            if arg == '_id':
                arg = self._id
            self.__args[arg] = val

    @classmethod
    def find(cls, **query):
        for key in query:
            if key not in cls.__f_keys:
                raise RuntimeError('"{}" attribute does not found for "{}"'.
                                    format(key, cls.__name__))

        return cls.__query_result_class(cls.__db, cls, query)

    @classmethod
    def get(cls, obj_id):
        res = cls.__query_result_class(cls.__db, cls, {cls._id: obj_id})

        res = yield from res
        res = list(res)
        if not res:
            return None
        return res[0]

    def save(self):
        ret = self.__query_result_class(self.__db, self.__class__, self.__args)
        res = yield from ret.upsert()
        return res

    def __getattribute__(self, attr):
        if attr[0] == '_':
            return super(Model, self).__getattribute__(attr)

        if attr in self.__f_keys:
            return self.__args.get(attr, None)

        return super(Model, self).__getattribute__(attr)

    def __setattr__(self, attr, val):
        if attr[0] == '_':
            return super(Model, self).__setattr__(attr, val)

        if attr in self.__f_keys:
            self.__args[attr] = val
            return
        
        return super(Model, self).__setattr__(attr, val)

    def __repr__(self):
        return '<%s> %s'%(self.__class__.__name__, self.__args)


def model_iterator(model_class, data):
    for item in data:
        yield model_class(**item)


class QueryResult(object):
    def __init__(self, db, model_class, query):
        pass

    @asyncio.coroutine
    def upsert(self):
        pass

    def sort(self, **order):
        '''order = {field: ASC | DESC , ...}
        '''
        return self
        
    def hint(self, index):
        return self

    def explain(self):
        return self

    @asyncio.coroutine
    def __iter__(self):
        for i in range(0):
            yield i


class AbstractDatabase(object):
    _query_result_class = QueryResult

    @classmethod
    def get_query_result_class(cls):
        return cls._query_result_class

    def __init__(self, db_name):
        self.__db_name = db_name

    def db_name(self):
        return self.__db_name

    @asyncio.coroutine
    def connect(self, **conn_params):
        pass

    @asyncio.coroutine
    def drop_database(self):
        pass

