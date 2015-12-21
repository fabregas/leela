
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
    {'endpoint': 'leela.middlewares.cors.CorsMiddleware',
     'rules': [{'url_regex': '.*/allallow', 'allow_credentials': True,
                'allow_methods': ['GET', 'POST', 'PUT',
                                  'PATCH', 'DELETE', 'OPTIONS', 'HEAD'],
                'allow_headers': ['content-type']},
               {'url_regex': '.*/readonly',
                'allow_methods': ['GET', 'OPTIONS', 'HEAD']},
               {'url_regex': '.*/echo',
                'allow_methods': ['POST', 'PUT', 'PATCH']},
               ]},
]
mw_list = []
for mw in middlewares:
    mw_list.append(loop.run_until_complete(app.init_middleware(mw)))
future = app.init_service('tests.services.CorsTest', {}, mw_list)
loop.run_until_complete(future)
app.handle_static('.')
srv = app.make_tcp_server('127.0.0.1', 6666)


def async_test(f):
    def wrapper(*args, **kwargs):
        coro = asyncio.coroutine(f)
        future = coro(*args, **kwargs)
        loop.run_until_complete(future)
    return wrapper


class TestCORS(unittest.TestCase):
    @async_test
    def test_cors(self):
        r = yield from aiohttp.options('http://0.0.0.0:6666/api/allallow')
        self.assertEqual(r.status, 200)
        yield from r.release()
        self.assertTrue('ALLOW' in r.headers)
        self.assertEqual(r.headers['ALLOW'],
                         'GET,POST,PUT,PATCH,DELETE,OPTIONS,HEAD',
                         r.headers['ALLOW'])
        self.assertEqual(r.headers['ACCESS-CONTROL-ALLOW-HEADERS'],
                         'content-type')
        self.assertEqual(r.headers['ACCESS-CONTROL-ALLOW-CREDENTIALS'],
                         'true')

        r = yield from aiohttp.options('http://0.0.0.0:6666/api/readonly')
        self.assertEqual(r.status, 200)
        yield from r.release()
        self.assertTrue('ALLOW' in r.headers)
        self.assertEqual(r.headers['ALLOW'], 'GET,OPTIONS,HEAD')
        self.assertEqual(r.headers['ACCESS-CONTROL-ALLOW-HEADERS'],
                         'x-requested-with, content-type, accept, origin, authorization, x-csrftoken')
        self.assertEqual(r.headers['ACCESS-CONTROL-ALLOW-CREDENTIALS'],
                         'false')

        r = yield from aiohttp.options('http://0.0.0.0:6666/api/echo')
        self.assertEqual(r.status, 200)
        yield from r.release()
        self.assertTrue('ALLOW' in r.headers)
        self.assertEqual(r.headers['ALLOW'], 'POST,PUT,PATCH')
        self.assertEqual(r.headers['ACCESS-CONTROL-ALLOW-HEADERS'],
                         'x-requested-with, content-type, accept, origin, authorization, x-csrftoken')
        self.assertEqual(r.headers['ACCESS-CONTROL-ALLOW-CREDENTIALS'],
                         'false')


if __name__ == '__main__':
    unittest.main()
    app.destroy()

