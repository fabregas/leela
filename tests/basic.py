
import aiohttp
import asyncio
import unittest
import json

from core import *
from db_support.inmemory import InMemoryDatabase 
#from db_support.mongo import MongoDB as InMemoryDatabase 


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
    def __init__(self, db, a, b):
        super().__init__(db, a)
        self.__b = b
        

    @reg_get('test_path2')
    def test22(self, data, http_req):
        ret = self.test(data, http_req)
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

loop = asyncio.get_event_loop()
DB = InMemoryDatabase('leela_test')
conn = DB.connect()
loop.run_until_complete(conn)
loop.run_until_complete(DB.drop_database())

SM = InMemorySessionsManager()
srv = run_server(B(DB, 2222, 4444), '0.0.0.0', 6666,
                 sessions_manager=SM)

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
        self.assertEqual(SM.count(), 1)


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
        self.assertEqual(SM.count(), 2)

        r = yield from aiohttp.request('post', 'http://0.0.0.0:6666/api/__logout__') 
        self.assertEqual(r.status, 401, r.reason)

        r = yield from aiohttp.request('post', 'http://0.0.0.0:6666/api/__logout__', cookies=cookies) 
        self.assertEqual(r.status, 200, r.reason)
        self.assertEqual(SM.count(), 1)




if __name__ == '__main__':
    unittest.main()
    srv.close()

