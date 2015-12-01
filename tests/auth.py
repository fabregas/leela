
import aiohttp
import asyncio
import unittest
import json
import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from leela.core import *

loop = asyncio.get_event_loop()
app = Application()
middlewares = [
    {'endpoint': 'leela.middlewares.session.SessionMiddleware'},
    {'endpoint': 'leela.middlewares.auth.AuthMiddleware'}
]
mw_list = []
for mw in middlewares:
    mw_list.append(loop.run_until_complete(app.init_middleware(mw)))
SM = mw_list[0].session_manager
future = app.init_service('tests.services.B', {'a': 2222, 'b': 4444},
                          mw_list)
loop.run_until_complete(future)
app.handle_static('.')
srv = app.make_tcp_server('127.0.0.1', 6666)

def async_test(f):
    def wrapper(*args, **kwargs):
        coro = asyncio.coroutine(f)
        future = coro(*args, **kwargs)
        loop.run_until_complete(future)
    return wrapper


class TestAuthAPI(unittest.TestCase):
    @async_test
    def test_auth(self):
        r = yield from aiohttp.get('http://0.0.0.0:6666/api/secret')
        self.assertEqual(r.status, 401)
        yield from r.release()

        r = yield from aiohttp.post('http://0.0.0.0:6666/api/__auth__')
        self.assertEqual(r.status, 400)
        yield from r.release()

        r = yield from aiohttp.post(
            'http://0.0.0.0:6666/api/__auth__',
            data=json.dumps({'username': 'some', 'password': '123'}))
        self.assertEqual(r.status, 401, r.reason)
        self.assertEqual(r.reason, 'User does not found')
        yield from r.release()

        r = yield from aiohttp.post(
            'http://0.0.0.0:6666/api/__auth__',
            data=json.dumps({'username': 'kstt', 'password': '123'}))
        self.assertEqual(r.status, 401, r.reason)
        yield from r.release()

        r = yield from aiohttp.post(
            'http://0.0.0.0:6666/api/__auth__',
            data=json.dumps({'username': 'kst', 'password': '1223'}))
        self.assertEqual(r.status, 401, r.reason)
        yield from r.release()

        r = yield from aiohttp.post(
            'http://0.0.0.0:6666/api/__auth__',
            data=json.dumps({'username': 'kst', 'password': '123'}))
        self.assertEqual(r.status, 200, r.reason)
        cookies = r.cookies
        print('COOKIES 1:', r.cookies)
        yield from r.release()

        r = yield from aiohttp.get('http://0.0.0.0:6666/api/secret')
        self.assertEqual(r.status, 401)
        yield from r.release()

        r = yield from aiohttp.get('http://0.0.0.0:6666/api/secret',
                                   cookies=cookies)
        self.assertEqual(r.status, 200, r.reason)
        yield from r.release()
        count = SM.count()
        self.assertEqual(int(count), 1)


        r = yield from aiohttp.get('http://0.0.0.0:6666/api/top_secret',
                                   cookies=cookies)
        self.assertEqual(r.status, 200, r.reason)
        yield from r.release()

        r = yield from aiohttp.get('http://0.0.0.0:6666/api/super_secret',
                                   cookies=cookies)
        self.assertEqual(r.status, 401, r.reason)
        self.assertEqual(r.reason, 'Permission denied')
        yield from r.release()

        r = yield from aiohttp.post(
            'http://0.0.0.0:6666/api/__auth__',
            data=json.dumps({'username': 'kst', 'password': '123'}))
        self.assertEqual(r.status, 200, r.reason)
        yield from r.release()
        cookies = r.cookies
        print('COOKIES 2:', r.cookies)
        count = SM.count()
        self.assertEqual(int(count), 2)

        r = yield from aiohttp.post('http://0.0.0.0:6666/api/__logout__')
        self.assertEqual(r.status, 401, r.reason)
        yield from r.release()

        r = yield from aiohttp.post('http://0.0.0.0:6666/api/__logout__',
                                    cookies=cookies)
        self.assertEqual(r.status, 200, r.reason)
        yield from r.release()
        count = SM.count()
        self.assertEqual(int(count), 1)



if __name__ == '__main__':
    unittest.main()
    app.destroy()

