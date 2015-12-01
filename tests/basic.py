
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
future = app.init_service('tests.services.B', {'a': 2222, 'b': 4444}, [])
loop.run_until_complete(future)
app.handle_static('.')
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
        r = yield from aiohttp.post('http://0.0.0.0:6666/')
        self.assertEqual(r.status, 405)
        yield from r.release()

        payload = {'key1': 'value1', 'key2': 'value2'}
        r = yield from aiohttp.post('http://0.0.0.0:6666/api/incoming',
                                    data=json.dumps(payload))
        self.assertEqual(r.status, 200)
        data = yield from r.json()
        self.assertEqual(data, True)

        r = yield from aiohttp.get('http://0.0.0.0:6666/api/incoming')
        data = yield from r.json()
        self.assertEqual(data, payload)

        r = yield from aiohttp.put(
            'http://0.0.0.0:6666/api/incoming',
            data=json.dumps({'key':'NEW_KEY', 'value': 33.3}))
        self.assertEqual(r.status, 200)
        data = yield from r.json()
        self.assertEqual(data, True)

        r = yield from aiohttp.get('http://0.0.0.0:6666/api/incoming')
        data = yield from r.json()
        payload['NEW_KEY'] = 33.3
        self.assertEqual(data, payload)

        #delete...
        r = yield from aiohttp.delete(
            'http://0.0.0.0:6666/api/incoming',
            data=json.dumps({'key':'key2'}))
        self.assertEqual(r.status, 200)
        data = yield from r.json()
        self.assertEqual(data, True)

        r = yield from aiohttp.get('http://0.0.0.0:6666/api/incoming')
        data = yield from r.json()
        del payload['key2']
        self.assertEqual(data, payload)

    @async_test
    def test_get(self):
        r = yield from aiohttp.get('http://0.0.0.0:6666/')
        self.assertEqual(r.status, 404)
        yield from r.release()

        r = yield from aiohttp.get('http://0.0.0.0:6666/api/test_path')
        self.assertEqual(r.status, 200, r.reason)
        data = yield from r.json()
        self.assertEqual(len(data), 3)
        self.assertEqual(data, ['test sting', 1, 2222])

        payload = {'key1': 'value1', 'key2': 'value2'}
        r = yield from aiohttp.get('http://0.0.0.0:6666/api/test_path',
                                   params=payload)
        self.assertEqual(r.status, 200)
        data = yield from r.json()
        self.assertEqual(len(data), 4)
        self.assertEqual(data, ['test sting', 1, 2222, payload])

        r = yield from aiohttp.get('http://0.0.0.0:6666/api/test_path2')
        self.assertEqual(r.status, 200)
        data = yield from r.json()
        self.assertEqual(len(data), 3)
        self.assertEqual(data, ['test sting', 22, 4444])

    @async_test
    def test_fileupload(self):
        with open(__file__, 'rb') as fdesc:
            files = {'file': fdesc}
            r = yield from aiohttp.post('http://0.0.0.0:6666/api/some_file',
                                        data=files)
            data = yield from r.read()
        self.assertEqual(r.status, 200, data)

        r = yield from aiohttp.get('http://0.0.0.0:6666/api/some_file')
        data = yield from r.read()
        self.assertEqual(r.status, 200, data)
        data = yield from r.json()

        self.assertEqual(data[0], 'basic.py')
        with open(__file__, 'rb') as rfile:
            self.assertEqual(data[1], rfile.read().decode())


        with open(__file__, 'rb') as fdesc:
            r = yield from aiohttp.post(
                'http://0.0.0.0:6666/api/some_str_file', data=fdesc)

        self.assertEqual(r.status, 200)
        yield from r.release()

        r = yield from aiohttp.get('http://0.0.0.0:6666/api/some_file')
        self.assertEqual(r.status, 200)
        data = yield from r.json()

        self.assertEqual(data[0], 'basic.py')
        with open(__file__, 'rb') as rfile:
            self.assertEqual(data[2], hashlib.sha1(rfile.read()).hexdigest())



if __name__ == '__main__':
    unittest.main()
    app.destroy()

