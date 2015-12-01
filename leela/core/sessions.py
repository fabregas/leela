
import time
import string
import random
import pickle
import hashlib
import asyncio


DEFAULT_EXPIRE_TIME = 60*60*24*30  # 30 days


class Session(object):
    def __init__(self, session_id, session_data=None, expire_time=None):
        self.__session_id = session_id
        self.__session_data = session_data if session_data else {}
        self.need_remove = False
        self.modified = False
        self.expire_time = expire_time

    def __setitem__(self, key, value):
        self.set(key, value)

    def set(self, key, value):
        self.__session_data[key] = value
        self.modified = True

    def get(self, key, default=None):
        return self.__session_data.get(key, default)

    def pop(self, key, default=None):
        return self.__session_data.pop(key, default)

    def get_id(self):
        return self.__session_id

    def set_id(self, session_id):
        self.__session_id = session_id

    def remove(self):
        self.need_remove = True

    def dump(self):
        return pickle.dumps(self)

    @classmethod
    def load(self, dump):
        return pickle.loads(dump)


class BaseSessionManager(object):
    def __init__(self, expire_time=DEFAULT_EXPIRE_TIME):
        self.expire_time = expire_time

    def generate_session_id(self):
        return ''.join(random.SystemRandom().choice(
                    string.ascii_letters + string.digits) for _ in range(32))

    def update_session_time(self, session):
        exp_time = time.time() + self.expire_time
        session.expire_time = exp_time

    @asyncio.coroutine
    def start(self):
        """start session manager
        Can be inherited
        """
        pass

    @asyncio.coroutine
    def stop(self):
        """stop session manager
        Can be inherited
        """
        pass

    @asyncio.coroutine
    def get(self, session_id):
        '''get session dict'''
        pass

    @asyncio.coroutine
    def set(self, session):
        '''set session dict'''
        pass

    @asyncio.coroutine
    def remove(self, session):
        '''remove session'''
        pass


class InMemorySessionsManager(BaseSessionManager):
    def __init__(self, expire_time=DEFAULT_EXPIRE_TIME):
        super().__init__(expire_time)
        self.__sessions = {}

    def count(self):
        return len(self.__sessions)

    @asyncio.coroutine
    def get(self, session_id):
        session = self.__sessions.get(session_id, None)
        if session:
            return session

        session = Session(None)
        return session

    @asyncio.coroutine
    def set(self, session):
        session_id = session.get_id()
        if session_id is None:  # new session
            while True:
                session_id = self.generate_session_id()
                if session_id not in self.__sessions:
                    break
        exp_time = time.time() + self.expire_time
        session.expire_time = exp_time
        session.set_id(session_id)
        self.__sessions[session_id] = session
        session.modified = False

    @asyncio.coroutine
    def remove(self, session):
        session_id = session.get_id()
        if (session_id is None) or (session_id not in self.__sessions):
            return False
        del self.__sessions[session_id]
        return True
