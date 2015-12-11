import asyncio

from leela.core.middleware import LeelaMiddleware
from leela.core.sessions import BaseSessionManager, InMemorySessionsManager


COOKIE_SESSION_ID = 'l_session_id'


class SessionMiddleware(LeelaMiddleware):
    def __init__(self, session_manager=None):
        if not session_manager:
            session_manager = InMemorySessionsManager()

        assert isinstance(session_manager, BaseSessionManager)
        self.session_manager = session_manager

    @asyncio.coroutine
    def start(self):
        yield from self.session_manager.start()

    @asyncio.coroutine
    def destroy(self):
        yield from self.session_manager.destroy()

    @asyncio.coroutine
    def on_request(self, request, data, params, cache):
        session_id = request.cookies.get(COOKIE_SESSION_ID, None)
        session = yield from self.session_manager.get(session_id)
        data.set_session(session)

    @asyncio.coroutine
    def on_response(self, request, data, response, params, cache):
        if not data.session:
            return response

        if data.session.need_remove:
            yield from self.session_manager.remove(data.session)
            response.del_cookie(COOKIE_SESSION_ID)
        elif data.session.modified:
            yield from self.session_manager.set(data.session)
            response.set_cookie(COOKIE_SESSION_ID, data.session.get_id())

        return response
