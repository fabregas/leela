#!/usr/bin/python

import os
import yaml
import logging
import logging.config
import importlib
import asyncio
from aiohttp import web

from leela.core.core import reg_api
from leela.core.service import AService


class Application(object):
    def __init__(self):
        self.__app = web.Application()
        self.__service = None

    def set_logger_config(self, logger_config_path):
        try:
            config = yaml.load(open(logger_config_path))

            logging.config.dictConfig(config)
        except Exception as err:
            raise RuntimeError('Invalid logger config file: {}'
                               .format(err))

    @asyncio.coroutine
    def init_service(self, service_name, config):
        if service_name.endswith('.py'):
            service_name = service_name.rstrip('.py')

        try:
            service = importlib.import_module(service_name)
        except ImportError:
            raise RuntimeError('Service "{}" does not found!'.
                               format(service_name))

        class_o = None
        for attr in dir(service):
            if attr.startswith('_'):
                continue

            class_o = getattr(service, attr)
            try:
                if class_o != AService and issubclass(class_o, AService):
                    break
            except TypeError:
                continue
        else:
            raise RuntimeError('No one service class found in "{}"'.
                               format(service_name))

        print('-> found service class {}'.format(class_o))

        yield from self.init_service_class(class_o, config)

    @asyncio.coroutine
    def init_service_class(self, service_class, config):
        s_instance = yield from service_class.initialize(config)

        reg_api.setup_service(s_instance)

        for method, path, handle, _ in reg_api.get_routes():
            self.__app.router.add_route(method, path, handle)

        self.__service = s_instance

    def handle_static(self, static_path):
        self.__app.router.add_static('/static', static_path)

        @asyncio.coroutine
        def root_handler(request):
            idx_path = os.path.join(static_path, 'index.html')
            if not os.path.exists(idx_path):
                raise web.HTTPNotFound()
            data = open(idx_path).read()
            return web.Response(body=data.encode())

        self.__app.router.add_route('GET', '/', root_handler)

    def make_tcp_server(self, host, port):
        loop = asyncio.get_event_loop()
        future = loop.create_server(self.__app.make_handler(), host, port)
        return loop.run_until_complete(future)

    def make_unix_server(self, path):
        loop = asyncio.get_event_loop()
        future = loop.create_unix_connection(self.__app.make_handler(), path)
        return loop.run_until_complete(future)

    def destroy(self):
        if not self.__service:
            return
        loop = asyncio.get_event_loop()
        cor = self.__service.destroy()
        loop.run_until_complete(cor)
        self.__service = None
