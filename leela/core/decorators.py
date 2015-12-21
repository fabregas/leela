
import json
import re
import inspect
import asyncio
import aiohttp
import traceback
from aiohttp import web

from leela.utils.logger import logger


class SmartDict(dict):
    def __init__(self):
        super().__init__()

    def from_dict(self, dict_val):
        for key, value in dict_val.items():
            self[key] = value

    def __getattr__(self, attr):
        return self[attr]

    def __setattr__(self, attr, value):
        raise ValueError('Request should not be modified')


class SmartRequest:
    __slots__ = ('session', 'data', 'query', 'params')

    def __init__(self):
        self.session = None
        self.query = SmartDict()
        self.params = SmartDict()
        self.data = SmartDict()

    def set_session(self, session):
        self.session = session

    def __repr__(self):
        return '<SmartRequest query={}, params={}, data={}>'.format(
            self.query, self.params, self.data)


class leela_api(object):
    http_method = None
    __routes = []
    __routes_map = {}

    def __init__(self, object_name, *,
                 req_validator=None, resp_validator=None, **mw_params):
        """
        object_name - name of API object
        req_validator - request validator (None if no need to validate)
        resp_validator - response validator (None if no need to validate)
        mw_params - parameters for middlewares
        """
        self.object_name = object_name
        self.req_validator = req_validator
        self.resp_validator = resp_validator
        self.mw_params = mw_params

    @classmethod
    @asyncio.coroutine
    def _parse_request(cls, request):
        ret = SmartRequest()

        ret.params.from_dict(request.match_info)
        ret.query.from_dict(request.GET)

        data = yield from request.content.read()
        if data:
            data = json.loads(data.decode())
        else:
            data = {}

        ret.data.from_dict(data)
        return ret

    @classmethod
    def _form_response(cls, ret_object):
        if isinstance(ret_object, web.Response):
            return ret_object

        return web.Response(body=json.dumps(ret_object).encode(),
                            content_type='application/json')

    def __call__(self, func):
        func._l_api = self
        func._l_decorator_class = self.__class__

        return asyncio.coroutine(func)

    @classmethod
    def _decorate_method(cls, service, method):
        def handler(request):
            try:
                dclass = method._l_decorator_class

                data = yield from dclass._parse_request(request)

                #FIXME req validation

                mw_cache = {}
                for middleware in service.middlewares():
                    resp = yield from middleware.on_request(
                        request, data, method._l_api.mw_params, mw_cache)
                    if resp:
                        assert isinstance(resp, web.Response), \
                            'Middleware {} returns invalid response: {}' \
                            .format(middleware, resp)
                        return resp

                ret = yield from method(data)

                #FIXME resp validation

                resp = dclass._form_response(ret)

                for middleware in service.middlewares():
                    resp = yield from middleware.on_response(
                        request, data, resp, method._l_api.mw_params, mw_cache)
            except web.HTTPException as ex:
                resp = ex
            except Exception as ex:
                resp = web.Response(text=traceback.format_exc(), status=500)

            return resp

        def option_handler(request):
            resp = web.Response()
            for middleware in service.middlewares():
                resp = middleware.on_response(
                    request, SmartRequest(), resp,
                    method._l_api.mw_params, {})
            return resp


        docs = '' if not method.__doc__ \
                  else method.__doc__.strip().split('\n')[0]
        cls.__routes.append((method._l_api.http_method,
                             method._l_api.object_name,
                             handler,
                             docs,
                             option_handler))

    @classmethod
    def get_routes(cls):
        for route in cls.__routes:
            yield route

    @classmethod
    def setup_service(cls, service):
        from .service import LeelaService
        if not isinstance(service, LeelaService):
            raise RuntimeError('Service should be instance of AService, '
                               'but {}'.format(service))
        s_methods = dir(service)
        for m_name in s_methods:
            method = getattr(service, m_name)
            if not inspect.ismethod(method):
                continue
            if not getattr(method, '_l_api', False):
                continue
            cls._decorate_method(service, method)


class leela_get(leela_api):
    http_method = 'GET'


class leela_post(leela_api):
    http_method = 'POST'


class leela_put(leela_post):
    http_method = 'PUT'


class leela_delete(leela_post):
    http_method = 'DELETE'


class leela_form_post(leela_api):
    http_method = 'POST'

    @classmethod
    @asyncio.coroutine
    def _parse_request(cls, request):
        ret = SmartRequest()

        ret.params.from_dict(request.match_info)
        ret.query.from_dict(request.GET)

        data = yield from request.post()
        ret.data.from_dict(data)
        return ret


class leela_postfile(leela_form_post):
    @classmethod
    def _form_response(cls, ret_object):
        return web.Response()


class leela_websocket(leela_get):
    http_method = 'GET'

    @classmethod
    @asyncio.coroutine
    def _parse_request(cls, request):
        ret = yield from super()._parse_request(request)
        ws = web.WebSocketResponse()
        ok, protocol = ws.can_start(request)
        if not ok:
            raise web.HTTPExpectationFailed(reason='Invalid WebSocket')
        ws.start(request)
        ret.data['websocket'] = ws
        return ret

    @classmethod
    def _form_response(cls, ret_object):
        if not isinstance(ret_object, web.WebSocketResponse):
            raise RuntimeError('Expected WebSocketResponse object as a result')
        return ret_object


class leela_uploadstream(leela_post):
    @classmethod
    @asyncio.coroutine
    def _parse_request(cls, request):
        ret = SmartRequest()
        ret.params.from_dict(request.match_info)
        ret.query.from_dict(request.GET)
        ret.data['stream'] = request.content
        return ret

    @classmethod
    def _form_response(cls, ret_object):
        return web.Response()
