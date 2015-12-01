import asyncio
import hashlib
from aiohttp import web

from leela.core.service import LeelaService
from leela.core.decorators import leela_post


SESSION_USER_KEY = '_leela_user'


class authorization(object):
    def __init__(self, *roles):
        self.__roles = set(roles)

    def allowed_roles(self):
        return self.__roles

need_auth = authorization()


class BaseUser(object):
    def __init__(self, username, password_digest, roles, **additional_info):
        self.username = username
        self.password_digest = password_digest
        self.roles = roles
        self.additional_info = additional_info

    def check_password(self, password):
        pwd_digest = hashlib.sha1(password.encode()).hexdigest()
        return pwd_digest == self.password_digest

    @classmethod
    def create(cls, username, password, roles, **additional_info):
        pwd_digest = hashlib.sha1(password.encode()).hexdigest()
        return cls(username=username, password_digest=pwd_digest,
                   roles=roles, additional_info=additional_info)

    def get_roles(self):
        return set(self.roles)

class AuthBasedService(LeelaService):

    @asyncio.coroutine
    def get_user(self, username):
        """MUST be implemented in inherited class"""
        raise RuntimeError('not implemented')

    @leela_post('__auth__')
    def util_auth(self, data):
        self.mandatory_check(data, 'username', 'password')

        user = yield from self.get_user(data.username)

        if not user:
            raise web.HTTPUnauthorized(reason='User does not found')

        if not user.check_password(data.password):
            raise web.HTTPUnauthorized(reason='Invalid password')

        data.session.set(SESSION_USER_KEY, user)

        return {'username': user.username,
                'roles': user.roles,
                'additional': user.additional_info}

    @leela_post('__logout__', auth=need_auth)
    def util_logout(self, data):
        if data.get('clear_session', True):
            data.session.remove()
        else:
            data.session.set(SESSION_USER_KEY, None)
        return web.Response()
