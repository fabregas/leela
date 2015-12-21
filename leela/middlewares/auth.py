import asyncio
from aiohttp import web

from leela.core.middleware import LeelaMiddleware
from leela.services.auth import SESSION_USER_KEY, authorization


class AuthMiddleware(LeelaMiddleware):
    @asyncio.coroutine
    def on_request(self, request, data, params, cache):
        auth_req = params.get('auth', None)
        if not auth_req:
            return
        assert isinstance(auth_req, authorization), auth_req

        if not data.session:
            raise web.HTTPUnauthorized()

        user = data.session.get(SESSION_USER_KEY)
        if not user:
            raise web.HTTPUnauthorized()

        allowed_roles = auth_req.allowed_roles()
        if allowed_roles:
            allowed = user.get_roles() & allowed_roles
            if not allowed:
                raise web.HTTPUnauthorized(reason='Permission denied')

    @asyncio.coroutine
    def on_response(self, request, data, response, params, cache):
        return response
