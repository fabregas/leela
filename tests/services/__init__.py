import asyncio
from datetime import datetime

from leela.core import *
from leela.services.auth import (need_auth, authorization,
                                 AuthBasedService, BaseUser)

class A(LeelaService):
    def __init__(self, a):
        super().__init__()
        self.__a = a
        self.__incoming = {}

    @leela_get('test_path')
    def test(self, data):
        print('test func ...', data)
        ret = ['test sting', 1, self.__a]
        if data:
            ret.append(data)
        return ret

    @leela_post('incoming')
    def test2(self, data):
        print('POST test func ...', dict(data))
        self.__incoming.update(dict(data))
        return True

    @leela_get('incoming')
    def test3(self, data):
        return self.__incoming

    @leela_put('incoming')
    def test2_put(self, data):
        print('PUT test func ...', data)
        self.__incoming[data.key] = data.value
        return True

    @leela_delete('incoming')
    def test2_delete(self, data):
        print('DELETE test func ...', data)
        del self.__incoming[data.key]
        return True


class B(A, AuthBasedService):
    FNAME = None
    FCONT = None

    def __init__(self, a, b):
        super().__init__(a)
        self.__b = b

    @asyncio.coroutine
    def get_user(self, username):
        if username == 'kst':
            return BaseUser.create(username, '123', ['testrole'])
        return None

    @leela_get('test_path2')
    def test22(self, data):
        ret = yield from self.test(data)
        print('test22 func ...', data, ret)
        return ['test sting', 22, self.__b]

    @leela_get('secret', auth=need_auth)
    def test_secret(self, data):
        return 'SECRET'

    @leela_get('top_secret', auth=authorization('testrole', 'superrole'))
    def test_topsecret(self, data):
        return 'TOP SECRET'

    @leela_get('super_secret', auth=authorization('superrole'))
    def test_supersecret(self, data):
        return 'SUPER SECRET'

    @leela_postfile('some_file')
    def test_upload(self, data):
        t0 = datetime.now()

        self.__class__.FNAME = data.file.filename
        self.__class__.FCONT = data.file.file.read()
        data.file.file.close()

        print('some_file proc time: %s'%(datetime.now()-t0))

    @leela_get('some_file')
    def test_file_info(self, data):
        rec = [self.FNAME, self.FCONT.decode(),
               getattr(self, 'STREAM_SHA1', None)]
        return rec

    @leela_uploadstream('some_str_file')
    def test_uploadstr(self, data):
        t0 = datetime.now()

        h = hashlib.sha1()
        while True:
            chunk = yield from data.stream.readany()
            if not chunk:
                break
            h.update(chunk)
        self.__class__.STREAM_SHA1 = h.hexdigest()

        print('some_str_file proc time: %s'%(datetime.now()-t0))
