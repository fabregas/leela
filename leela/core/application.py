#!/usr/bin/python

import os
import yaml
import logging
import logging.config
import importlib
import asyncio
import copy
from aiohttp import web

from leela.core.decorators import leela_api
from leela.core.service import LeelaService
from leela.core.middleware import LeelaMiddleware


class Application(object):
    def __init__(self):
        self.__app = web.Application()
        self.__services = []
        self.__unixsocket = None
        self.__server = None
        self.__handler = None

    def set_logger_config(self, logger_config_path):
        try:
            config = yaml.load(open(logger_config_path))

            logging.config.dictConfig(config)
        except Exception as err:
            raise RuntimeError('Invalid logger config file: {}'
                               .format(err))

    def _import_class(self, class_endpoint):
        parts = class_endpoint.split('.')
        class_name = parts.pop(-1)

        try:
            module = importlib.import_module('.'.join(parts))
        except ImportError as err:
            raise RuntimeError(
                'Class "{}" does not found: {}'.format(class_endpoint, err))

        class_o = getattr(module, class_name, None)
        if class_o is None:
            raise RuntimeError(
                'Class "{}" does not found!'.format(class_endpoint))
        return class_o

    def _initialize_class(self, class_obj, config, args_section=None):
        params = {}
        for key, value in config.items():
            if isinstance(value, dict):
                # this is object config
                class_endpoint = value.get('endpoint', None)
                if class_endpoint is None:
                    raise RuntimeError('"endpoint" does not found for '
                                       '"{}" object in config'.format(key))

                if args_section:
                    class_config = value.get(args_section, {})
                else:
                    class_config = copy.copy(value)
                    class_config.pop('endpoint')

                params[key] = self._initialize_class(
                    self._import_class(class_endpoint), class_config)
            else:
                # int, string, list will be passed as is
                params[key] = value

        try:
            return class_obj(**params)
        except TypeError as err:
            raise RuntimeError('{} initialization failed: {}'
                               .format(class_obj, err))

    @asyncio.coroutine
    def init_middleware(self, mw_config):
        def get_mw_instance(mw):
            return mw

        mw_instance = self._initialize_class(
            get_mw_instance, {'mw': mw_config})

        if not isinstance(mw_instance, LeelaMiddleware):
            raise RuntimeError('{} MUST be a subclass of LeelaMiddleware'
                               .format(mw_instance.__class__))

        yield from mw_instance.start()
        return mw_instance

    @asyncio.coroutine
    def init_service(self, service_endpoint, config, middlewares):
        service_class = self._import_class(service_endpoint)
        if not issubclass(service_class, LeelaService):
            raise RuntimeError('{} MUST be a subclass of LeelaService'
                               .format(service_class))

        service_class.set_middlewares(middlewares)

        s_instance = self._initialize_class(service_class, config, 'config')
        yield from s_instance.start()

        leela_api.setup_service(s_instance)
        self.__services.append(s_instance)

    def handle_static(self, static_path):
        self.__app.router.add_static('/static', static_path)

        @asyncio.coroutine
        def root_handler(request):
            idx_path = os.path.join(static_path, 'index.html')
            if not os.path.exists(idx_path):
                raise web.HTTPNotFound()
            data = open(idx_path).read()
            return web.Response(body=data.encode())

        @asyncio.coroutine
        def root_opt_handler(request):
            return web.Response(headers={'Allow': 'GET'})

        self.__app.router.add_route('GET', '/', root_handler)
        self.__app.router.add_route('OPTIONS', '/', root_opt_handler)

    def __make_router(self):
        for method, obj_name, handle, _, opt_handler in leela_api.get_routes():
            path = "/api/{}".format(obj_name)
            self.__app.router.add_route(method, path, handle)
            self.__app.router.add_route('OPTIONS', path, opt_handler)

    def make_tcp_server(self, host, port):
        self.__make_router()
        loop = asyncio.get_event_loop()
        self.__handler = self.__app.make_handler()
        future = loop.create_server(self.__handler, host, port)
        self.__server = loop.run_until_complete(future)

    def make_unix_server(self, path):
        self.__make_router()
        self.__unixsocket = path
        if os.path.exists(self.__unixsocket):
            os.unlink(self.__unixsocket)
        loop = asyncio.get_event_loop()
        self.__handler = self.__app.make_handler()
        future = loop.create_unix_server(self.__handler, path)
        self.__server = loop.run_until_complete(future)

    @asyncio.coroutine
    def destroy(self):
        if self.__handler:
            yield from self.__handler.finish_connections(1.0)

        for service in self.__services:
            yield from service.destroy()

        if self.__server:
            self.__server.close()
            yield from self.__server.wait_closed()

        yield from self.__app.finish()

        self.__services = []
        self.__server = None

        if self.__unixsocket:
            os.unlink(self.__unixsocket)
        self.__unixsocket = None
