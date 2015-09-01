#!/usr/bin/python

import os
import sys
import logging
import logging.config
import asyncio
import aiohttp
import signal
import json
import functools
import yaml

from leela.core.application import Application
from leela.utils.logger import logger

CONFIG = '''
version: 1
formatters:
    verbose:
        format: '%(levelname)s %(module)s %(process)d %(message)s'
    simple:
        format: '%(levelname)s %(message)s'
handlers:
    console:
        level: INFO
        class: logging.StreamHandler
        formatter: simple
    syslog:
        level: INFO
        class: logging.handlers.SysLogHandler
        address: '/dev/log'
        formatter: verbose
loggers:
    leela:
        handlers: [console, syslog]
        level: INFO
    {}:
        handlers: [console, syslog]
        level: INFO
'''

class TestLeelaServer(object):
    def __init__(self, loop=None, custom_logger_name='test'):
        self.loop = loop or asyncio.get_event_loop()
        self.app = Application()

        logging.config.dictConfig(yaml.load(CONFIG.format(custom_logger_name)))

    def add_service(self, service_class, config):
        logger.info('starting test service {}...'.format(service_class))
        future = self.app.init_service(service_class, config)
        self.loop.run_until_complete(future)

    def add_activity(self, activity_class, config):
        logger.info('starting test activity {}...'.format(activity_class))
        future = self.app.init_activity(activity_class, config)
        self.loop.run_until_complete(future)

    def start(self, port):
        self.port = port
        logger.info('starting test TCP server at 127.0.0.1:{}...'.format(port))
        self.app.make_tcp_server('127.0.0.1', port)

    def stop(self):
        logger.info('stoping test application...')
        future = self.app.destroy()
        self.loop.run_until_complete(future)

    @asyncio.coroutine
    def call_api(self, method, params={}, http_method='GET'):
        url = 'http://127.0.0.1:{}/api/{}'.format(self.port, method)
        response = yield from aiohttp.request(http_method, url, params=params)
        if response.status != 200:
            data = yield from response.text()
            raise RuntimeError('ERROR while call {}: [{}]'.format(url, data))

        data = yield from response.json()
        return data




if __name__ == '__main__':
    tls = TestLeelaServer()

    from leela.core import *
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

    tls.add_service(A, {'a': 32555})
    tls.start(44444)
    
    import aiohttp
    def get_body(url):
        response = yield from aiohttp.request('GET', url)
        return (yield from response.read())

    raw_html = tls.loop.run_until_complete(get_body('http://127.0.0.1:44444/api/test_path'))
    print(raw_html)
    assert raw_html == b'["test sting", 1, 32555]'
 
    tls.stop()
    
