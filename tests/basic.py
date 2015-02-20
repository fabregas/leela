
import aiohttp
import asyncio
import unittest

from core import *

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

loop = asyncio.get_event_loop()
DB = InMemoryDatabase()
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
                                        data=payload) 
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
                                data={'username': 'kst', 'password': '123'}) 
        self.assertEqual(r.status, 401, r.reason)
        self.assertEqual(r.reason, 'User does not found')

        DB.add_user(User.create('kst', '123', ['testrole']))
        r = yield from aiohttp.request('post', 'http://0.0.0.0:6666/api/__auth__',
                                data={'username': 'kst', 'password': '123'}) 
        self.assertEqual(r.status, 200, r.reason)
        cookies = r.cookies
        print('COOKIES 1:', r.cookies)

        r = yield from aiohttp.request('get', 'http://0.0.0.0:6666/api/secret') 
        self.assertEqual(r.status, 401)
        r = yield from aiohttp.request('get', 'http://0.0.0.0:6666/api/secret', cookies=cookies) 
        self.assertEqual(r.status, 200, r.reason)
        self.assertEqual(SM.count(), 1)


        r = yield from aiohttp.request('post', 'http://0.0.0.0:6666/api/__auth__',
                                data={'username': 'kst', 'password': '123'}) 
        self.assertEqual(r.status, 200, r.reason)
        cookies = r.cookies
        print('COOKIES 2:', r.cookies)
        self.assertEqual(SM.count(), 2)

        r = yield from aiohttp.request('post', 'http://0.0.0.0:6666/api/__terminate__') 
        self.assertEqual(r.status, 401, r.reason)

        r = yield from aiohttp.request('post', 'http://0.0.0.0:6666/api/__terminate__', cookies=cookies) 
        self.assertEqual(r.status, 200, r.reason)
        self.assertEqual(SM.count(), 1)




if __name__ == '__main__':
    unittest.main()
    srv.close()

