
import aiohttp
import asyncio
import unittest
import json

from leela.core import *
from leela.db_support.mongo import MongoDB, MongoQueryResult

loop = asyncio.get_event_loop()

def async_test(f):
    def wrapper(*args, **kwargs):
        coro = asyncio.coroutine(f)
        future = coro(*args, **kwargs)
        loop.run_until_complete(future)
    return wrapper

class TestMongoBackend(unittest.TestCase):
    @async_test
    def test_dbops(self):
        db = MongoDB('leela_test_db')
        conn = yield from db.connect()
        yield from db.drop_database()
        test = db.test
        in_res = yield from test.insert({"src":"Wordpress", "content":"some comments"}, safe=True)
        result = yield from test.group(keys=["src"], initial={"count":0},
                                       reduce="function(obj,prev){prev.count++;}")
        print(in_res)
        print(result)
        results = yield from test.find({'_id': in_res})
        results = list(results)
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result['src'], 'Wordpress')
        self.assertEqual(result['content'], 'some comments')
        db.disconnect()

    @async_test
    def test_orm(self):
        db = MongoDB('leela_test_db')
        conn = yield from db.connect()
        yield from db.drop_database()
        Model.init(conn)

        class User(Model):
            _id = 'username'

            username = None
            password = None
            roles = []
            additional_info = None
            _ignore_me = 44

        user = User(username='kss34', password='dfassded')
        self.assertEqual(user.username, 'kss34')
        self.assertEqual(user.password, 'dfassded')
        self.assertEqual(user.roles, [])

        ret = yield from user.save()
        print(ret)

        user = yield from User.get('kss34')
        self.assertEqual(user.username, 'kss34')
        self.assertEqual(user.password, 'dfassded')
        self.assertEqual(user.roles, [])

        class Log(Model):
            log_level = 0
            log_msg = ''

        yield from Log(log_msg='first msg').save()
        yield from Log(log_msg='second msg').save()
        yield from Log(log_msg='third msg').save()
        log_objs = yield from Log.find()
        log_objs = list(log_objs)
        self.assertEqual(len(log_objs), 3, log_objs)
        self.assertEqual(log_objs[0].log_msg, 'first msg')
        self.assertEqual(log_objs[1].log_msg, 'second msg')
        self.assertEqual(log_objs[2].log_msg, 'third msg')

        log_objs[1].log_level = 3
        yield from log_objs[1].save()

        log_objs = yield from Log.find(log_level=3)
        log_objs = list(log_objs)
        self.assertEqual(len(log_objs), 1, log_objs)
        self.assertEqual(log_objs[0].log_msg, 'second msg')

        log_objs = yield from Log.find()
        self.assertEqual(len(list(log_objs)), 3, log_objs)

        with self.assertRaises(RuntimeError):
            yield from Log.find(some_other=4)

        
        #filters
        for i in range(100):
            yield from Log(log_msg='msg #%i'%i, log_level=4).save()

        log_objs = yield from Log.find().sort(log_level=1)
        log_objs = list(log_objs)
        self.assertEqual(len(list(log_objs)), 103, log_objs)
        self.assertEqual(log_objs[0].log_msg, 'first msg')
        self.assertEqual(log_objs[1].log_msg, 'third msg')
        self.assertEqual(log_objs[2].log_msg, 'second msg')

        log_objs = yield from Log.find().sort(log_msg=-1).skip(1).limit(1)
        log_objs = list(log_objs)
        self.assertEqual(len(log_objs), 1, log_objs)
        self.assertEqual(log_objs[0].log_msg, 'second msg')

        log_objs = yield from Log.find(log_level={'$lt': 4})
        log_objs = list(log_objs)
        self.assertEqual(len(log_objs), 3, log_objs)

        #remove
        log_objs = yield from Log.find(log_level={'$gt': 3}).remove()
        log_objs = yield from Log.find()
        log_objs = list(log_objs)
        self.assertEqual(len(log_objs), 3, log_objs)
        yield from log_objs[0].remove()
        log_objs = yield from Log.find()
        log_objs = list(log_objs)
        self.assertEqual(len(log_objs), 2, log_objs)

if __name__ == '__main__':
    unittest.main()
