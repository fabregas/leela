
import asyncio
from aiohttp import web

from .decorators import leela_get, leela_api


class LeelaService(object):
    __middlewares = []

    @classmethod
    def set_middlewares(cls, middlewares):
        cls.__middlewares = middlewares

    @classmethod
    def middlewares(cls):
        for mw in cls.__middlewares:
            yield mw

    @asyncio.coroutine
    def start(self):
        """you should implement your 'async constructor' in this method"""
        pass

    @asyncio.coroutine
    def destroy(self):
        """you should implement your 'destructor' in this method"""
        pass

    def mandatory_check(self, data, *keys):
        for key in keys:
            if key not in data:
                raise web.HTTPBadRequest(
                    reason='Mandatory parameter "{}" does not found'
                    .format(key))

    @leela_get('__introspect__')
    def util_introspect_methods(self, data):
        li_list = ''
        for method, path, _, docs, _ in leela_api.get_routes():
            if path.startswith('/api/__'):
                continue

            docs = '' if not docs else '-- {}'.format(docs)
            li_list += '<li><b>{}</b>&nbsp;&nbsp;{}&nbsp;&nbsp;{}</li>'\
                       .format(method.upper(), '/api/{}'.format(path), docs)

        if not li_list:
            li_list = 'No one API method found...'

        html = '''<html><body>
                    <h1>Available methods:</h1>
                    <ul>
                        {}
                    </ul>
                  </body></html>'''.format(li_list)
        return web.Response(text=html)
