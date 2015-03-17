
import asyncio
from aiohttp import web
from .core import reg_get, reg_post, reg_api
from .sessions import User
from .orm import Model
from .orm import AbstractDatabase

from leela.db_support.inmemory import InMemoryDatabase


class AService(object):
    @classmethod
    def initialize(cls, configuration):
        '''key-value configration from YAML'''
        raise RuntimeError('Not implemented!')

    def __init__(self, database):
        if database is None:
            database = InMemoryDatabase()

        if not isinstance(database, AbstractDatabase):
            raise RuntimeError('Invalid database instance!')

        self.database = database
        self.db = database  # alias
        Model.init(database)

    @asyncio.coroutine
    def destroy(self):
        '''you should implement your 'destructor' in this method'''
        yield from self.database.disconnect()

    def mandatory_check(self, data, *keys):
        for key in keys:
            if key not in data:
                raise web.HTTPBadRequest(reason='Mandatory parameter "{}" '
                                         'does not found'.format(key))

    @reg_get('__introspect__')
    def util_introspect_methods(self, data, http_req):
        li_list = ''
        for method, path, _, docs in reg_api.get_routes():
            if path.startswith('/api/__'):
                continue

            docs = '' if not docs else '-- {}'.format(docs)
            li_list += '<li><b>{}</b>&nbsp;&nbsp;{}&nbsp;&nbsp;{}</li>'\
                       .format(method.upper(), path, docs)
        if not li_list:
            li_list = 'No one API method found...'

        html = '''<html><body>
                    <h1>Available methods:</h1>
                    <ul>
                        {}
                    </ul>
                  </body></html>'''.format(li_list)
        return web.Response(body=html.encode())

    @reg_post('__auth__')
    def util_auth(self, data, http_req):
        self.mandatory_check(data, 'username', 'password')

        user = yield from User.get(data['username'])
        if not user:
            raise web.HTTPUnauthorized(reason='User does not found')

        if not user.check_password(data['password']):
            raise web.HTTPUnauthorized(reason='Invalid password')

        data.session.user = user

        return web.Response()

    @reg_post('__logout__')
    def util_terminate(self, data, http_req):
        data.session.need_remove = True
        return web.Response()
