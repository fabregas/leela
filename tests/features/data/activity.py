
import asyncio
from leela.core.activity import AActivity

class TestActivity(AActivity):
    @classmethod
    @asyncio.coroutine
    def initialize(cls, configuration):
        return TestActivity(configuration.get('name', 'TEST_NAME'))

    def __init__(self, name):
        self.name = name
        self.stopped = False

    @asyncio.coroutine
    def start(self):
        while not self.stopped:
            yield from asyncio.sleep(1)
            print('[act-%s] iter...'%self.name)


    @asyncio.coroutine
    def destroy(self):
        print('[act-%s] stopping activity...'%self.name)
        self.stopped = True

