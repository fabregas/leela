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
from leela.core.activity import AActivity


class Application(object):
    def __init__(self):
        self.__app = web.Application()
        self.__services = []
        self.__activities = []
        self.__unixsocket = None

    def set_http_config(self, htt_config):
        reg_api.set_default_headers(htt_config.get('headers', {}))

    def set_logger_config(self, logger_config_path):
        try:
            config = yaml.load(open(logger_config_path))

            logging.config.dictConfig(config)
        except Exception as err:
            raise RuntimeError('Invalid logger config file: {}'
                               .format(err))

    def _init_module(self, module_name, base_class):
        if module_name.endswith('.py'):
            module_name = module_name[:-3]

        try:
            service = importlib.import_module(module_name)
        except ImportError:
            raise RuntimeError('Module "{}" does not found!'.
                               format(module_name))

        class_o = None
        for attr in dir(service):
            if attr.startswith('_'):
                continue

            class_o = getattr(service, attr)
            try:
                if class_o != base_class and issubclass(class_o, base_class):
                    break
            except TypeError:
                continue
        else:
            raise RuntimeError('No one {} class found in "{}"'.
                               format(base_class, module_name))

        print('-> found class {}'.format(class_o))
        return class_o

    @asyncio.coroutine
    def init_service(self, service_name, config):
        service_class = self._init_module(service_name, AService)

        yield from self.init_service_class(service_class, config)

    @asyncio.coroutine
    def init_service_class(self, service_class, config):
        s_instance = yield from service_class.initialize(config)

        reg_api.setup_service(s_instance)

        self.__services.append(s_instance)

    @asyncio.coroutine
    def init_activity(self, module_name, config):
        act_class = self._init_module(module_name, AActivity)

        a_instance = yield from act_class.initialize(config)
        asyncio.async(a_instance.start())
        self.__activities.append(a_instance)

    def setup_sessions_manager(self, s_manager_obj_path):
        parts = s_manager_obj_path.split('.')
        try:
            module_name = '.'.join(parts[:-1])
            module = importlib.import_module(module_name)
        except ImportError:
            raise RuntimeError('Module "{}" does not found!'.
                               format(module_name))

        class_name = parts[-1]
        if not hasattr(module, class_name):
            raise RuntimeError('Class "{}" does not found in {}'
                               .format(class_name, module_name))

        sessions_manager = getattr(module, class_name)()
        reg_api.setup_sessions_manager(sessions_manager)
        return sessions_manager

    def __make_router(self):
        for method, path, handle, _ in reg_api.get_routes():
            self.__app.router.add_route(method, path, handle)

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
        self.__make_router()
        loop = asyncio.get_event_loop()
        future = loop.create_server(self.__app.make_handler(), host, port)
        return loop.run_until_complete(future)

    def make_unix_server(self, path):
        self.__make_router()
        self.__unixsocket = path
        if os.path.exists(self.__unixsocket):
            os.unlink(self.__unixsocket)
        loop = asyncio.get_event_loop()
        future = loop.create_unix_server(self.__app.make_handler(), path)
        return loop.run_until_complete(future)

    @asyncio.coroutine
    def destroy(self):
        for service in self.__services:
            yield from service.destroy()

        for activity in self.__activities:
            yield from activity.destroy()

        self.__services = []
        self.__activities = []

        if self.__unixsocket:
            os.unlink(self.__unixsocket)
        self.__unixsocket = None
