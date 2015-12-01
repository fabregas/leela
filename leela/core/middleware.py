
import asyncio

class LeelaMiddleware(object):
    @asyncio.coroutine
    def start(self):
        """you should implement your 'async constructor' in this method"""
        pass

    @asyncio.coroutine
    def destroy(self):
        """you should implement your 'destructor' in this method"""
        pass

    @asyncio.coroutine
    def on_request(self, request, data, params):
        return None

    @asyncio.coroutine
    def on_response(self, request, data, response, params):
        return response
