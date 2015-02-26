
import json
import asyncio
from aiohttp import web

from leela.utils import logger

COOKIE_SESSION_ID = 'session_id'


class UserData(dict):
    def __init__(self):
        super().__init__()
        self.session = None

    def set_session(self, session):
        self.session = session


class authorization(object):
    def __init__(self, *roles):
        self.__roles = roles

    def allowed_roles(self):
        return set(self.__roles)

need_auth = authorization()


class reg_api(object):
    method = None
    __routes = []
    __service = None
    __sessions_manager = None

    def __init__(self, path, auth=None):
        self.path = path
        self.need_auth = bool(auth)
        self.allowed_roles = set() if not auth else auth.allowed_roles()

    @asyncio.coroutine
    def _parse_request(self, request):
        return UserData()

    def _form_response(self, ret_object):
        if isinstance(ret_object, web.Response):
            return ret_object
        return web.Response(body=json.dumps(ret_object).encode(),
                            content_type='application/json')

    def _check_session(self, request):
        session_id = request.cookies.get(COOKIE_SESSION_ID, None)

        session = self.__sessions_manager.get(session_id)

        if self.need_auth:
            user = session.user

            if not user:
                raise web.HTTPUnauthorized()

            if self.allowed_roles:
                allowed = user.get_roles() & self.allowed_roles

                if not allowed:
                    raise web.HTTPUnauthorized(reason='Permission denied')
        return session

    def _postcheck_session(self, response, session):
        if not session:
            return
        if session.modified:
            self.__sessions_manager.set(session)

            # TODO: update user cookies IF NEED
            response.set_cookie(COOKIE_SESSION_ID, session.get_id())
        elif session.need_remove:
            found = self.__sessions_manager.remove(session)
            if not found:
                raise web.HTTPUnauthorized(reason='Session does not found')
            response.del_cookie(COOKIE_SESSION_ID)

    def __call__(self, func):
        def handle(request):
            coro = asyncio.coroutine(func)
            session = self._check_session(request)
            data = yield from self._parse_request(request)
            data.set_session(session)
            ret = yield from coro(self.__service, data, request)
            resp = self._form_response(ret)
            self._postcheck_session(resp, session)
            return resp

        docs = '' if not func.__doc__ else func.__doc__.strip().split('\n')[0]
        self.__routes.append((self.method, '/api/{}'.format(self.path), handle,
                              docs))
        return func

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
        cls.__service = service
        cls.setup_sessions_manager(service.get_sessions_manager())

    @classmethod
    def setup_sessions_manager(cls, sessions_manager):
        from .sessions import AbstractSessionsManager
        if not isinstance(sessions_manager, AbstractSessionsManager):
            raise RuntimeError('Invalid sessions manager instance!')
        cls.__sessions_manager = sessions_manager


class reg_post(reg_api):
    method = 'POST'

    @asyncio.coroutine
    def _parse_request(self, request):
        data = yield from request.content.read()
        if data:
            data = json.loads(data.decode())
        else:
            data = {}

        ret = UserData()
        for key in iter(data):
            ret[key] = data.get(key)
        return ret


class reg_get(reg_api):
    method = 'GET'

    @asyncio.coroutine
    def _parse_request(self, request):
        ret = UserData()
        for key in iter(request.GET):
            ret[key] = request.GET.get(key)
        return ret
