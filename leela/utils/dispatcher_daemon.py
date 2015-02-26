
import os
import sys
import json
import yaml
import logging.config
import asyncio.subprocess


class ServiceMgmt:
    def __init__(self, outstream=None):
        self.__proc = None
        self.__out = None
        self.__stopped = True
        self.__args = None

    @asyncio.coroutine
    def start(self, *args):
        self.__args = args
        self.__proc = yield from \
            asyncio.create_subprocess_exec(*args,
                                           stdout=self.__out,
                                           stderr=self.__out,
                                           stdin=asyncio.subprocess.PIPE)
        self.__stopped = False

    @asyncio.coroutine
    def send_to_stdin(self, string):
        self.__proc.stdin.write(string.encode() + b'\n')

    @asyncio.coroutine
    def check_run(self):
        while True:
            yield from self.__proc.wait()
            if not self.__stopped:
                print('Unexpected process "{}" termination. Try to reload...'.
                      format(' '.join(self.__args)))
                yield from self.start(*self.__args)
                yield from asyncio.sleep(1)

    @asyncio.coroutine
    def stop(self):
        self.__stopped = True
        if self.__proc is None:
            return
        self.__proc.terminate()
        yield from self.__proc.wait()
        self.__proc = True


def start(bin_dir, home_path, bind_addr, monitor_changes, leela_proc_count,
          is_nginx_proxy, is_ssl, logger_config_path,
          srv_endpoint, srv_config):

    if os.path.exists(logger_config_path):
        logging.config.dictConfig(yaml.load(open(logger_config_path)))
    else:
        print('WARNING! Logger config does not found at {}'
              .format(logger_config_path))
        logger_config_path = '--noconf'

    # with daemon context
    s_mgmt = ServiceMgmt()
    is_unixsocket = False
    loop = asyncio.get_event_loop()
    cor = s_mgmt.start('python3', os.path.join(bin_dir, 'leela-worker'),
                       'test-node01')
    loop.run_until_complete(cor)

    params_str = json.dumps([home_path, logger_config_path, srv_endpoint,
                             srv_config, is_ssl, bind_addr, is_unixsocket])
    cor = s_mgmt.send_to_stdin(params_str)
    loop.run_until_complete(cor)

    try:
        cor = s_mgmt.check_run()
        loop.run_until_complete(cor)
    finally:
        s_mgmt.stop()


def stop(home_path):
    pass
