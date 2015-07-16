
import json
import re
import inspect
import asyncio
import aiohttp
import traceback
from aiohttp import web
from .sessions import InMemorySessionsManager

from leela.utils.logger import logger

COOKIE_SESSION_ID = 'session_id'


class CORS(object):
    def __init__(self, rule):
        if 'url_regex' not in rule:
            raise RuntimeError('url_regex is expected for CORS config')

        self.url_regex = re.compile(rule['url_regex'])
        self.allow_origin = rule.get('allow_origin', [])
        self.allow_credentials = rule.get('allow_credentials', False)
        self.allow_methods = rule.get('allow_methods',
                                      ['GET', 'POST', 'PUT', 'PATCH',
                                       'DELETE', 'OPTIONS'])
        self.allow_headers = rule.get('allow_headers',
                                      ['x-requested-with', 'content-type',
                                       'accept', 'origin', 'authorization',
                                       'x-csrftoken'])

    def check(self, request):
        if request.method not in self.allow_methods:
            raise web.HTTPMethodNotAllowed(request.method, self.allow_methods,
                                           headers=self.http_headers())

    def matched(self, url):
        return bool(self.url_regex.match(url))

    def http_headers(self):
        return {'Access-Control-Allow-Origin':  ' '.join(self.allow_origin),
                'Access-Control-Allow-Credentials':
                                        str(self.allow_credentials).lower(),
                'Access-Control-Allow-Methods': ', '.join(self.allow_methods),
                'Access-Control-Allow-Headers': ', '.join(self.allow_headers)}


class UserData(dict):
    def __init__(self):
        super().__init__()
        self.session = None

    def set_session(self, session):
        self.session = session

    def __getattr__(self, attr):
        return self[attr]


class authorization(object):
    def __init__(self, *roles):
        self.__roles = roles

    def allowed_roles(self):
        return set(self.__roles)

need_auth = authorization()


class reg_api(object):
    method = None
    __routes = []
    __cors_rules = []
    __routes_map = {}
    __sessions_manager = InMemorySessionsManager()
    _default_headers = aiohttp.MultiDict({})
    __headers = {}

    def __init__(self, path, auth=None):
        '''
        path - object path
        auth - instance of @authorization class or None
        '''
        self.path = path
        self.need_auth = bool(auth)
        self.allowed_roles = set() if not auth else auth.allowed_roles()


    @classmethod
    def __get_headers(cls, path):
        if path in cls.__headers:
            return cls.__headers[path]

        f_rule = None
        for cors_rule in cls.__cors_rules:
            if cors_rule.matched(path):
                f_rule = cors_rule

        resp_headers = cls._default_headers
        if f_rule is not None:
            resp_headers.update(f_rule.http_headers())
        cls.__headers[path] = (resp_headers, f_rule)
        return cls.__headers[path]


    @classmethod
    @asyncio.coroutine
    def _parse_request(cls, request):
        return UserData()

    @classmethod
    def _form_response(cls, ret_object, headers={}):
        if isinstance(ret_object, web.Response):
            ret_object.headers.update(headers)
            return ret_object

        return web.Response(body=json.dumps(ret_object).encode(),
                            content_type='application/json',
                            headers=headers)

    @classmethod
    @asyncio.coroutine
    def _check_session(cls, request, need_auth, allowed_roles):
        session_id = request.cookies.get(COOKIE_SESSION_ID, None)

        session = yield from cls.__sessions_manager.get(session_id)

        if need_auth:
            user = session.user

            if not user:
                raise web.HTTPUnauthorized()

            if allowed_roles:
                allowed = user.get_roles() & allowed_roles

                if not allowed:
                    raise web.HTTPUnauthorized(reason='Permission denied')
        return session

    @classmethod
    @asyncio.coroutine
    def _postcheck_session(cls, response, session):
        if not session:
            return

        if session.need_remove:
            found = yield from cls.__sessions_manager.remove(session)
            if not found:
                raise web.HTTPUnauthorized(reason='Session does not found')
            response.del_cookie(COOKIE_SESSION_ID)
        elif session.modified:
            yield from cls.__sessions_manager.set(session)

            # TODO: update user cookies IF NEED
            response.set_cookie(COOKIE_SESSION_ID, session.get_id())

    def __call__(self, func):
        func.path = '/api/{}'.format(self.path)
        func.method = self.method
        func.need_auth = self.need_auth
        func.allowed_roles = self.allowed_roles
        func.is_leela_api = True 
        func.decorator_class = self.__class__
        
        return asyncio.coroutine(func)

    @classmethod
    def _decorate_method(cls, method):
        def handler(request):
            session = None
            try:
                dclass = method.decorator_class
                session = yield from dclass._check_session(request,
                                                           method.need_auth,
                                                           method.allowed_roles)
                data = yield from dclass._parse_request(request)

                headers, cors_rule = dclass.__get_headers(request.path)
                if cors_rule:
                    cors_rule.check(request)

                data.set_session(session)

                ret = yield from method(data, request)

                resp = dclass._form_response(ret, headers)
            except web.HTTPException as ex:
                resp = ex
            except Exception as ex:
                resp = web.Response(text=traceback.format_exc(), status=500)
            finally:
                yield from dclass._postcheck_session(resp, session)

            return resp

        def option_handler(request):
            dclass = method.decorator_class
            headers, cors_rule = dclass.__get_headers(request.path)
            if cors_rule:
                cors_rule.check(request)
                headers['Allow'] = ','.join(cors_rule.allow_methods)
            else:
                headers['Allow'] = 'HEAD,GET,PUT,POST,PATCH,DELETE,OPTIONS'

            return web.Response(headers=headers)


        docs = '' if not method.__doc__ \
                  else method.__doc__.strip().split('\n')[0]
        cls.__routes.append((method.method, method.path, handler, docs,
                             option_handler))


    @classmethod
    def set_default_headers(cls, headers):
        cls._default_headers = aiohttp.MultiDict(headers)

    @classmethod
    def set_cors_rules(cls, cors_rules):
        cls.__cors_rules = cors_rules

    @classmethod
    def get_routes(cls):
        for route in cls.__routes:
            yield route

    @classmethod
    def setup_service(cls, service):
        from .service import AService
        if not isinstance(service, AService):
            raise RuntimeError('Service should be instance of AService, '
                               'but {}'.format(service))
        s_methods = dir(service)
        for m_name in s_methods:    
            method = getattr(service, m_name)
            if not inspect.ismethod(method):
                continue
            if not getattr(method, 'is_leela_api', False): 
                continue
            cls._decorate_method(method)

    @classmethod
    def setup_sessions_manager(cls, sessions_manager):
        from .sessions import AbstractSessionsManager
        if not isinstance(sessions_manager, AbstractSessionsManager):
            raise RuntimeError('Invalid sessions manager instance!')
        cls.__sessions_manager = sessions_manager


class reg_post(reg_api):
    method = 'POST'

    @classmethod
    @asyncio.coroutine
    def _parse_request(cls, request):
        data = yield from request.content.read()
        if data:
            data = json.loads(data.decode())
        else:
            data = {}

        ret = UserData()
        for key in iter(data):
            ret[key] = data.get(key)
        return ret

class reg_put(reg_post):
    method = 'PUT'

class reg_delete(reg_post):
    method = 'DELETE'

class reg_form_post(reg_api):
    method = 'POST'

    @classmethod
    @asyncio.coroutine
    def _parse_request(cls, request):
        data = yield from request.post()

        ret = UserData()
        for key in iter(data):
            ret[key] = data.get(key)
        return ret


class reg_get(reg_api):
    method = 'GET'

    @classmethod
    @asyncio.coroutine
    def _parse_request(cls, request):
        ret = UserData()
        for key in iter(request.GET):
            ret[key] = request.GET.get(key)
        return ret

class reg_websocket(reg_get):
    method = 'GET'

    @classmethod
    @asyncio.coroutine
    def _parse_request(cls, request):
        ret = yield from super()._parse_request(request)
        ws = web.WebSocketResponse()
        ok, protocol = ws.can_start(request)
        if not ok:
            raise web.HTTPExpectationFailed(reason='Invalid WebSocket')
        ws.start(request)
        ret.websocket = ws
        return ret

    @classmethod
    def _form_response(cls, ret_object, headers):
        if not isinstance(ret_object, web.WebSocketResponse):
            raise RuntimeError('Expected WebSocketResponse object as a result')
        ret_object.headers.update(headers)
        return ret_object

class reg_postfile(reg_form_post):
    @classmethod
    def _form_response(cls, ret_object, headers):
        return web.Response(headers = headers)

class reg_uploadstream(reg_post):
    @classmethod
    @asyncio.coroutine
    def _parse_request(cls, request):
        ret = UserData()
        for key in iter(request.GET):
            ret[key] = request.GET.get(key)
        ret['stream'] = request.content
        return ret

    @classmethod
    def _form_response(cls, ret_object, headers):
        return web.Response(headers = headers)
