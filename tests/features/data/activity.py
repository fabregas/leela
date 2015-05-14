
import asyncio
from leela.core.activity import AActivity
from leela.utils.logger import logger

class TestActivity(AActivity):
    @classmethod
    @asyncio.coroutine
    def initialize(cls, configuration):
        return TestActivity(configuration.get('act_name', 'TEST_NAME'),
                            configuration.get('user', None))

    def __init__(self, name, user):
        self.name = name
        self.user = user
        self.stopped = False

    @asyncio.coroutine
    def start(self):
        while not self.stopped:
            logger.info('[act-%s] USER=%s iter...'%(self.name, self.user))
            yield from asyncio.sleep(1)


    @asyncio.coroutine
    def destroy(self):
        logger.info('[act-%s] stopping activity...'%self.name)
        self.stopped = True

