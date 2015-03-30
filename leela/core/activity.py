
import asyncio

class AActivity(object):
    @classmethod
    @asyncio.coroutine
    def initialize(cls, configuration):
        '''key-value configration from YAML'''
        raise RuntimeError('Not implemented!')


    @asyncio.coroutine
    def start(self):
        pass

    @asyncio.coroutine
    def destroy(self):
        pass

