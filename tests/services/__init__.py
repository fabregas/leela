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
    def test(self, req):
        print('test func ...', req)
        ret = ['test sting', 1, self.__a]
        if req.query:
            ret.append(req.query)
        return ret

    @leela_post('incoming')
    def test2(self, req):
        print('POST test func ...', dict(req.data))
        self.__incoming.update(dict(req.data))
        return True

    @leela_get('incoming')
    def test3(self, req):
        return self.__incoming

    @leela_put('incoming')
    def test2_put(self, req):
        print('PUT test func ...', req.data)
        self.__incoming[req.data.key] = req.data.value
        return True

    @leela_delete('incoming')
    def test2_delete(self, req):
        print('DELETE test func ...', req.data)
        del self.__incoming[req.data.key]
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
    def test22(self, req):
        ret = yield from self.test(req)
        print('test22 func ...', req.data, ret)
        return ['test sting', 22, self.__b]

    @leela_get('secret', auth=need_auth)
    def test_secret(self, req):
        return 'SECRET'

    @leela_get('top_secret', auth=authorization('testrole', 'superrole'))
    def test_topsecret(self, req):
        return 'TOP SECRET'

    @leela_get('super_secret', auth=authorization('superrole'))
    def test_supersecret(self, req):
        return 'SUPER SECRET'

    @leela_postfile('some_file')
    def test_upload(self, req):
        t0 = datetime.now()

        self.__class__.FNAME = req.data.file.filename
        self.__class__.FCONT = req.data.file.file.read()
        req.data.file.file.close()

        print('some_file proc time: %s'%(datetime.now()-t0))

    @leela_get('some_file')
    def test_file_info(self, req):
        rec = [self.FNAME, self.FCONT.decode(),
               getattr(self, 'STREAM_SHA1', None)]
        return rec

    @leela_uploadstream('some_str_file')
    def test_uploadstr(self, req):
        t0 = datetime.now()

        h = hashlib.sha1()
        while True:
            chunk = yield from req.data.stream.readany()
            if not chunk:
                break
            h.update(chunk)
        self.__class__.STREAM_SHA1 = h.hexdigest()

        print('some_str_file proc time: %s'%(datetime.now()-t0))
