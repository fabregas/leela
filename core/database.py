
import hashlib


class UserAlreadyExists(Exception):
    pass


class User(object):
    @classmethod
    def create(cls, username, password, roles, **additional_info):
        pwd_digest = hashlib.sha1(password.encode()).hexdigest()
        return User(username, pwd_digest, roles, **additional_info)

    def __init__(self, username, password_digest, roles, **additional_info):
        self.username = username
        self.password_digest = password_digest
        self.additional_info = additional_info
        self.roles = set(roles) if roles else set()

    def check_password(self, password):
        pwd_digest = hashlib.sha1(password.encode()).hexdigest()
        return pwd_digest == self.password_digest


class AbstractDatabase(object):
    def get_user(self, username):
        pass

    def add_user(self, user):
        pass

    def update_user(self, user):
        pass


class InMemoryDatabase(AbstractDatabase):
    def __init__(self):
        super().__init__()

        self.__users = {}

    def get_user(self, username):
        return self.__users.get(username, None)

    def add_user(self, user):
        if not isinstance(user, User):
            raise RuntimeError('invalid user instance: {}'.format(user))
        if user.username in self.__users:
            raise UserAlreadyExists()

        self.__users[user.username] = user

    def update_user(self, user):
        if not isinstance(user, User):
            raise RuntimeError('invalid user instance: {}'.format(user))
        if user.username in self.__users:
            raise RuntimeError('user "{}" does not found in database'
                               .format(user.username))

        self.__users[user.username] = user
