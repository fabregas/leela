
import time
import string
import random
import pickle
import hashlib

from .orm import Model


DEFAULT_EXPIRE_TIME = 60*60*24*30  # 30 days

SESSION_USER = '_user_'


class User(Model):
    _id = 'username'

    username = None
    password_digest = None
    roles = []
    additional_info = {}

    def get_roles(self):
        return set(self.roles) if self.roles else set()

    def check_password(self, password):
        pwd_digest = hashlib.sha1(password.encode()).hexdigest()
        return pwd_digest == self.password_digest

    @classmethod
    def create(cls, username, password, roles, **additional_info):
        pwd_digest = hashlib.sha1(password.encode()).hexdigest()
        return User(username=username, password_digest=pwd_digest, roles=roles,
                    additional_info=additional_info)


class Session(object):
    def __init__(self, session_id, session_data=None, expire_time=None):
        self.__session_id = session_id
        self.__session_data = session_data if session_data else {}
        self.need_remove = False
        self.modified = False
        self.expire_time = expire_time

    def set(self, key, value):
        self.__session_data[key] = value
        self.modified = True

    def get(self, key, default=None):
        return self.__session_data.get(key, default)

    def get_id(self):
        return self.__session_id

    def set_id(self, session_id):
        self.__session_id = session_id

    def _get_user(self):
        return self.get(SESSION_USER)

    def _set_user(self, user):
        self.set(SESSION_USER, user)

    def dump(self):
        return pickle.dumps(self)

    @classmethod
    def load(self, dump):
        return pickle.loads(dump)

    user = property(_get_user, _set_user)


class AbstractSessionsManager(object):
    def __init__(self, expire_time=DEFAULT_EXPIRE_TIME):
        self.expire_time = expire_time

    def get(self, session_id):
        '''get session dict'''
        pass

    def set(self, session_id, session):
        '''set session dict'''
        pass

    def check_sessions(self):
        '''remove expired sessions'''
        pass


class InMemorySessionsManager(AbstractSessionsManager):
    def __init__(self, expire_time=DEFAULT_EXPIRE_TIME):
        super().__init__(expire_time)
        self.__sessions = {}

    def count(self):
        return len(self.__sessions)

    def check_sessions(self):
        pass

    def get(self, session_id):
        session = self.__sessions.get(session_id, None)
        if session:
            return session

        session = Session(None)
        return session

    def set(self, session):
        session_id = session.get_id()
        if session_id is None:  # new session
            while True:
                session_id = ''.join(random.SystemRandom().choice(
                                     string.ascii_letters + string.digits)
                                     for _ in range(32))
                if session_id not in self.__sessions:
                    break
        exp_time = time.time() + self.expire_time
        session.expire_time = exp_time
        session.set_id(session_id)
        self.__sessions[session_id] = session
        session.modified = False

    def remove(self, session):
        session_id = session.get_id()
        if (session_id is None) or (session_id not in self.__sessions):
            return False
        del self.__sessions[session_id]
        return True
