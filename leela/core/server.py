
import os
import asyncio
from aiohttp import web
from .sessions import AbstractSessionsManager
from .core import reg_api


def run_server(service, host, port, static_path='.',
               sessions_manager=None):
    app = web.Application()

    for method, path, handle, _ in reg_api.get_routes():
        app.router.add_route(method, path, handle)
    app.router.add_static('/static', static_path)

    @asyncio.coroutine
    def root_handler(request):
        idx_path = os.path.join(static_path, 'index.html')
        if not os.path.exists(idx_path):
            raise web.HTTPNotFound()
        data = open(idx_path).read()
        return web.Response(body=data.encode())

    app.router.add_route('GET', '/', root_handler)

    reg_api.setup_service(service)
    if not sessions_manager:
        sessions_manager = AbstractSessionsManager()
    reg_api.setup_sessions_manager(sessions_manager)
    loop = asyncio.get_event_loop()
    future = loop.create_server(app.make_handler(), host, port)
    return loop.run_until_complete(future)
