
import aiohttp
import asyncio
import unittest
import json
import sys
import os
from datetime import datetime

sys.path.append(os.path.abspath('.'))

from leela.core import *
from leela.db_support.inmemory import InMemoryDatabase 
from leela.db_support.mongo import MongoDB as InMemoryDatabase 


class A(AService):
    def __init__(self, db, a):
        super().__init__(db)
        self.__a = a
        self.__incoming = {}

    @reg_get('test_path')
    def test(self, data, http_req):
        print('test func ...', data)
        ret = ['test sting', 1, self.__a]
        if data:
            ret.append(data)
        return ret

    @reg_post('incoming')
    def test2(self, data, http_req):
        print('POST test func ...', dict(data))
        self.__incoming.update(dict(data))
        return True

    @reg_get('incoming')
    def test3(self, data, http_req):
        return self.__incoming

class B(A):
    FNAME = None
    FCONT = None
    @classmethod
    @asyncio.coroutine
    def initialize(cls, config):
        return cls(DB, 2222, 4444)

    def __init__(self, db, a, b):
        super().__init__(db, a)
        self.__b = b
        

    @reg_get('test_path2')
    def test22(self, data, http_req):
        ret = yield from self.test(data, http_req)
        print('test22 func ...', data, ret)
        return ['test sting', 22, self.__b]

    @reg_get('secret', need_auth)
    def test_secret(self, data, http_req):
        return 'SECRET'

    @reg_get('top_secret', authorization('testrole', 'superrole'))
    def test_topsecret(self, data, http_req):
        return 'TOP SECRET'

    @reg_get('super_secret', authorization('superrole'))
    def test_supersecret(self, data, http_req):
        return 'SUPER SECRET'

    @reg_postfile('some_file')
    def test_upload(self, data, http_req):
        t0 = datetime.now()

        self.__class__.FNAME = data.file.filename
        self.__class__.FCONT = data.file.file.read()
        data.file.file.close()

        print('some_file proc time: %s'%(datetime.now()-t0))

    @reg_uploadstream('some_str_file')
    def test_uploadstr(self, data, http_req):
        t0 = datetime.now()

        h = hashlib.sha1()
        while True:
            chunk = yield from data.stream.readany()
            if not chunk:
                break
            h.update(chunk)
        self.__class__.STREAM_SHA1 = h.hexdigest()

        print('some_str_file proc time: %s'%(datetime.now()-t0))


loop = asyncio.get_event_loop()
DB = InMemoryDatabase('leela_test')
conn = DB.connect()
loop.run_until_complete(conn)
loop.run_until_complete(DB.drop_database())

app = Application()
loop.run_until_complete(app.init_service_class(B, {}))
app.handle_static('.')
#SM = app.setup_sessions_manager('leela.core.sessions.InMemorySessionsManager')
SM = app.setup_sessions_manager('leela.db_support.mongo.MongoSessionsManager')
srv = app.make_tcp_server('127.0.0.1', 6666)

def async_test(f):
    def wrapper(*args, **kwargs):
        coro = asyncio.coroutine(f)
        future = coro(*args, **kwargs)
        loop.run_until_complete(future)
    return wrapper

class TestBasicAPI(unittest.TestCase):
    @async_test
    def test_post(self):
        r = yield from aiohttp.request('post', 'http://0.0.0.0:6666/') 
        self.assertEqual(r.status, 405)

        payload = {'key1': 'value1', 'key2': 'value2'}
        r = yield from aiohttp.request('post', 'http://0.0.0.0:6666/api/incoming', 
                                        data=json.dumps(payload)) 
        self.assertEqual(r.status, 200)
        data = yield from r.json()
        self.assertEqual(data, True)

        r = yield from aiohttp.request('get', 'http://0.0.0.0:6666/api/incoming') 
        data = yield from r.json()
        self.assertEqual(data, payload)


    @async_test
    def test_get(self):
        r = yield from aiohttp.request('get', 'http://0.0.0.0:6666/') 
        self.assertEqual(r.status, 404)

        r = yield from aiohttp.request('get', 'http://0.0.0.0:6666/api/test_path') 
        self.assertEqual(r.status, 200)
        data = yield from r.json()
        self.assertEqual(len(data), 3)
        self.assertEqual(data, ['test sting', 1, 2222])
        
        payload = {'key1': 'value1', 'key2': 'value2'}
        r = yield from aiohttp.request('get', 'http://0.0.0.0:6666/api/test_path',
                                        params=payload) 
        self.assertEqual(r.status, 200)
        data = yield from r.json()
        self.assertEqual(len(data), 4)
        self.assertEqual(data, ['test sting', 1, 2222, payload])

        r = yield from aiohttp.request('get', 'http://0.0.0.0:6666/api/test_path2') 
        self.assertEqual(r.status, 200)
        data = yield from r.json()
        self.assertEqual(len(data), 3)
        self.assertEqual(data, ['test sting', 22, 4444])


    @async_test
    def test_auth(self):
        r = yield from aiohttp.request('get', 'http://0.0.0.0:6666/api/secret') 
        self.assertEqual(r.status, 401)

        r = yield from aiohttp.request('post', 'http://0.0.0.0:6666/api/__auth__') 
        self.assertEqual(r.status, 400)
        print (r.reason)

        r = yield from aiohttp.request('post', 'http://0.0.0.0:6666/api/__auth__',
                                data=json.dumps({'username': 'kst', 'password': '123'})) 
        self.assertEqual(r.status, 401, r.reason)
        self.assertEqual(r.reason, 'User does not found')

        user = User.create('kst', '123', ['testrole'])
        yield from user.save()

        r = yield from aiohttp.request('post', 'http://0.0.0.0:6666/api/__auth__',
                                data=json.dumps({'username': 'kstt', 'password': '123'})) 
        self.assertEqual(r.status, 401, r.reason)

        r = yield from aiohttp.request('post', 'http://0.0.0.0:6666/api/__auth__',
                                data=json.dumps({'username': 'kst', 'password': '1223'})) 
        self.assertEqual(r.status, 401, r.reason)

        r = yield from aiohttp.request('post', 'http://0.0.0.0:6666/api/__auth__',
                                data=json.dumps({'username': 'kst', 'password': '123'})) 
        self.assertEqual(r.status, 200, r.reason)
        cookies = r.cookies
        print('COOKIES 1:', r.cookies)

        r = yield from aiohttp.request('get', 'http://0.0.0.0:6666/api/secret') 
        self.assertEqual(r.status, 401)
        r = yield from aiohttp.request('get', 'http://0.0.0.0:6666/api/secret', cookies=cookies) 
        self.assertEqual(r.status, 200, r.reason)
        count = yield from SM.count()
        self.assertEqual(int(count), 1)


        r = yield from aiohttp.request('get', 'http://0.0.0.0:6666/api/top_secret', cookies=cookies) 
        self.assertEqual(r.status, 200, r.reason)

        r = yield from aiohttp.request('get', 'http://0.0.0.0:6666/api/super_secret', cookies=cookies) 
        self.assertEqual(r.status, 401, r.reason)
        self.assertEqual(r.reason, 'Permission denied')

        r = yield from aiohttp.request('post', 'http://0.0.0.0:6666/api/__auth__',
                                data=json.dumps({'username': 'kst', 'password': '123'})) 
        self.assertEqual(r.status, 200, r.reason)
        cookies = r.cookies
        print('COOKIES 2:', r.cookies)
        count = yield from SM.count()
        self.assertEqual(int(count), 2)

        r = yield from aiohttp.request('post', 'http://0.0.0.0:6666/api/__logout__') 
        self.assertEqual(r.status, 401, r.reason)

        r = yield from aiohttp.request('post', 'http://0.0.0.0:6666/api/__logout__', cookies=cookies) 
        self.assertEqual(r.status, 200, r.reason)
        count = yield from SM.count()
        self.assertEqual(int(count), 1)


    @async_test
    def test_fileupload(self):
        files = {'file': open(__file__, 'rb')}
        r = yield from aiohttp.request('post', 'http://0.0.0.0:6666/api/some_file', 
                                        data=files) 
        self.assertEqual(r.status, 200)

        self.assertEqual(B.FNAME, 'basic.py')
        self.assertEqual(B.FCONT, open(__file__, 'rb').read())


        with  open(__file__, 'rb') as f:
            r = yield from aiohttp.request('post', 'http://0.0.0.0:6666/api/some_str_file',
                    data = f)

        self.assertEqual(r.status, 200)

        self.assertEqual(B.FNAME, 'basic.py')
        self.assertEqual(B.STREAM_SHA1, hashlib.sha1(open(__file__, 'rb').read()).hexdigest())


if __name__ == '__main__':
    unittest.main()
    app.destroy()

