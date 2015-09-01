
import aiohttp
import asyncio
import unittest
import json
import sys
import os
from datetime import datetime

sys.path.append(os.path.abspath('.'))

from leela.core import *
from leela.utils.test_utils import TestLeelaServer


class A(AService):
    @classmethod
    @asyncio.coroutine
    def initialize(cls, configuration):
        return cls(None, configuration.get('a', 0))

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


class TestUtilsAPI(unittest.TestCase):
    def test_utiltests(self):
        tls = TestLeelaServer()
        tls.add_service(A, {'a': 32555})
        tls.start(44444)
        
        def get_body(url):
            response = yield from aiohttp.request('GET', url)
            return (yield from response.read())

        raw_html = tls.loop.run_until_complete(get_body('http://127.0.0.1:44444/api/test_path'))
        print(raw_html)
        assert raw_html == b'["test sting", 1, 32555]'

        data = tls.loop.run_until_complete(tls.call_api('test_path', {'sss': 33}))
        self.assertEqual(data, ['test sting', 1, 32555, {'sss': '33'}])
     
        tls.stop()


if __name__ == '__main__':
    unittest.main()
    app.destroy()

