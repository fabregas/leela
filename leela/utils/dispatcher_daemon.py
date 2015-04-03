
import os
import sys
import json
import yaml
import time
import signal
import logging
import logging.config
import multiprocessing
import asyncio.subprocess
import tempfile
import copy

import leela
from .logger import logger
from .daemon3x import daemon as Daemon


NGINX_CFG_TMPL = '''
worker_processes 1;
daemon off;
user %(username)s;

events {
    worker_connections 1024;
}

http {
    sendfile on;

    gzip              on;
    gzip_http_version 1.0;
    gzip_proxied      any;
    gzip_min_length   500;
    gzip_disable      "MSIE [1-6]\.";
    gzip_types        text/plain text/xml text/css
                      text/comma-separated-values
                      text/javascript
                      application/x-javascript
                      application/atom+xml;

    upstream app_servers {
        %(app_servers)s
    }

    %(nossl_config)s
    %(ssl_config)s
}
'''

NGINX_NOSSL_CONFIG = '''
    server {
        listen %(running_port)s;

        access_log /dev/null;
        error_log /tmp/error_log;

        location ^~ /  {
            root %(static_path)s;
        }

        location /api {
            proxy_pass         http://app_servers;
            proxy_pass_header Server;
            proxy_redirect     off;
            proxy_set_header   Host $host;
            proxy_set_header   X-Real-IP $remote_addr;
            proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header   X-Forwarded-Host $server_name;
        }
    }
'''

NGINX_SSL_CONFIG = '''
    server {
        listen 443;

        ssl on;
        ssl_certificate         %(ssl_cert)s;
        ssl_certificate_key     %(ssl_key)s;

        access_log /dev/null;
        error_log /tmp/error_log;

        location ^~ /  {
            root %(static_path)s;
        }

        location /api {
            proxy_pass         http://app_servers;
            proxy_redirect     off;
            proxy_set_header   Host $host;
            proxy_set_header   X-Real-IP $remote_addr;
            proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header   X-Forwarded-Host $server_name;
        }
    }
'''

NGINX_SSL_ONLY_CONFIG = '''
    server {
        listen %(running_port)s;
        return 301 https://$host$request_uri;
    }
'''


def _make_nginx_config(username, proj_name, servers, port, static_path,
                       ssl_cert=None, ssl_key=None, ssl_only=False):
    app_servers = ''
    for server in servers:
        app_servers += '\t\tserver unix:{};\n'.format(server)

    ssl_config = nossl_config = ''
    if ssl_cert and ssl_key:
        ssl_config = NGINX_SSL_CONFIG % {'ssl_cert': ssl_cert,
                                         'ssl_key': ssl_key,
                                         'static_path': static_path}
    if ssl_only:
        nossl_config = NGINX_SSL_ONLY_CONFIG % {'running_port': port}
    else:
        nossl_config = NGINX_NOSSL_CONFIG % {'static_path': static_path,
                                             'running_port': port}

    params = {'app_servers': app_servers, 'username': username,
              'ssl_config': ssl_config, 'nossl_config': nossl_config}
    config = NGINX_CFG_TMPL % params
    conf_path = os.path.join(tempfile.gettempdir(),
                             'leela-{}-nginx.conf'.format(proj_name))
    open(conf_path, 'w').write(config)
    return conf_path


def _check_root(config):
    if os.geteuid() != 0:
        msg = 'You need to have root privileges to run this script.\n' \
              'Please try again, this time using \'sudo\'. Exiting.'
        raise RuntimeError(msg)

    if not os.path.exists(config.nginx_exec):
        raise RuntimeError('Nginx exec does not found at {}. Fix your config'
                           .format(config.nginx_exec))


class ServiceMgmt:
    def __init__(self, username=None, outstream=None):
        self.__proc = None
        self.__out = None
        self.__stopped = True
        self.__args = None
        self.__env = None
        self.__input_s = None
        self.__username = username

    def __repr__(self):
        return str(self.__args)

    @asyncio.coroutine
    def start(self, *args, env=None, input_s=None, need_stdout=False):
        if env is None:
            env = {}
        self.__args = args
        self.__env = env
        self.__input_s = input_s
        if self.__username:
            args = ['su', self.__username, '-s'] + list(args)
            stderr = asyncio.subprocess.PIPE
        else:
            stderr = self.__out

        if need_stdout:
            self.__out = None
            stderr = self.__out

        self.__proc = yield from \
            asyncio.create_subprocess_exec(*args,
                                           stdout=self.__out,
                                           stderr=stderr,
                                           stdin=asyncio.subprocess.PIPE,
                                           env=env)
        self.__stopped = False
        if input_s:
            self.__proc.stdin.write(input_s.encode() + b'\n')
        self.__proc.stdin.close()

    @asyncio.coroutine
    def check_run(self):
        while True:
            ret = yield from self.__proc.wait()
            yield from asyncio.sleep(1)
            if not self.__stopped:
                try:
                    err_msg = yield from self.__proc.stderr.read()
                    logger.error('child stderr: {}'.format(err_msg[-1000:]))
                except Exception as err:
                    logger.error('check_run() -> stderr.read() failed: {}'
                                 .format(err))

                logger.error('Unexpected process "{}" termination.'
                             ' Try to reload...'.format(' '.join(self.__args)))

                yield from self.start(*self.__args, env=self.__env,
                                      input_s=self.__input_s)
            else:
                return

    @asyncio.coroutine
    def stop(self):
        self.__stopped = True
        if self.__proc is None:
            return

        self.__proc.send_signal(signal.SIGINT)
        ret = yield from self.__proc.wait()

        self.__proc = None


def _run_leela_processes(loop, bin_dir, home_path, proj_name, config):
    leela_processes = []
    bind_sockets = []
    env = copy.copy(os.environ)
    env['PYTHONPATH']= os.path.abspath(os.path.dirname(leela.__file__))\
        .rstrip('leela')
            

    for i in range(config.leela_proc_count):
        s_mgmt = ServiceMgmt(config.username)
        is_unixsocket = config.is_nginx_proxy
        lp_is_ssl = config.ssl and not is_unixsocket
        if not config.is_nginx_proxy:
            lp_bind_addr = config.bind_address
        else:
            tmpdir = tempfile.gettempdir()
            tmp_file = os.path.join(tmpdir,
                                    '{}-{}.unixsocket'.format(proj_name, i))
            lp_bind_addr = tmp_file

        bind_sockets.append(lp_bind_addr)

        params_str = json.dumps(['services', home_path,
                                 config.logger_config_path,
                                 config.services,
                                 config.sessions_manager, lp_is_ssl,
                                 lp_bind_addr, is_unixsocket])

        cor = s_mgmt.start(config.python_exec,
                           os.path.join(bin_dir, 'leela-worker'),
                           '{}-{}'.format(proj_name, i),
                           env=env, input_s=params_str,
                           need_stdout = not config.need_daemonize)

        loop.run_until_complete(cor)
        leela_processes.append(s_mgmt)


    for act in config.activities:
        s_mgmt = ServiceMgmt(config.username)
        params_str = json.dumps(['activity', home_path,
                                 config.logger_config_path,
                                 act['act_endpoint'], act['act_config']])
        cor = s_mgmt.start(config.python_exec,
                           os.path.join(bin_dir, 'leela-worker'),
                           '{}-act-{}'.format(proj_name, act['act_endpoint']),
                           env=env, input_s=params_str,
                           need_stdout = not config.need_daemonize)

        loop.run_until_complete(cor)
        leela_processes.append(s_mgmt)

    return leela_processes, bind_sockets


def _run_nginx(loop, home_path, proj_name, config,
               leela_processes,  bind_sockets):
    if config.is_nginx_proxy:
        parts = config.bind_address.split(':')
        if len(parts) == 2:
            port = parts[1]
        else:
            port = 80
        static_path = os.path.abspath(os.path.join(home_path, 'www'))

        cnf_file = _make_nginx_config(config.username, proj_name,
                                      bind_sockets, port,
                                      static_path, config.ssl_cert,
                                      config.ssl_key,
                                      config.ssl_only)
        nginx_mgmt = ServiceMgmt()
        cor = nginx_mgmt.start(config.nginx_exec, '-c', cnf_file)
        loop.run_until_complete(cor)
        leela_processes.append(nginx_mgmt)


def _stop_processes(loop, leela_processes):
    cors = []
    for proc in leela_processes:
        try:
            cors.append(proc.stop())
        except ProcessLookupError as err:
            logger.error('ProcessLookupError: {}'.format(err))
        except Exception as err:
            logger.error('proc.stop() faied: {}'.format(err))

    for cor in cors:
        try:
            loop.run_until_complete(cor)
        except ProcessLookupError as err:
            logger.error('ProcessLookupError: {}'.format(err))
        except Exception as err:
            logger.error('proc.stop() faied: {}'.format(err))

    # loop.close()


@asyncio.coroutine
def _check_changes(path):
    cur_time = time.time()
    print('cur time: ', cur_time)
    while True:
        for cur_path, _, files in os.walk(path):
            for file_name in files:
                f_path = os.path.join(cur_path, file_name)
                if not f_path.endswith('.py'):
                    continue
                if os.path.getmtime(f_path) > cur_time:
                    print('detected changed file at {}...'.format(f_path))
                    return f_path
        yield from asyncio.sleep(1)


def start(bin_dir, home_path, config):
    if os.path.exists(config.logger_config_path):
        logging.config.dictConfig(yaml.load(open(config.logger_config_path)))
    else:
        print('WARNING! Logger config does not found at {}'
              .format(config.logger_config_path))
        config.logger_config_path = '--noconf'

    if config.leela_proc_count <= 0:
        config.leela_proc_count = multiprocessing.cpu_count()
    if config.leela_proc_count > 1:
        config.is_nginx_proxy = True

    if config.is_nginx_proxy:
        _check_root(config)
    else:
        config.username = None

    proj_name = os.path.basename(home_path.rstrip('/'))
    if config.need_daemonize:
        daemon = Daemon('/tmp/leela-{}.pid'.format(proj_name))
        daemon.start()

    # with daemon context
    leela_processes = []
    bind_sockets = []
    try:
        loop = asyncio.get_event_loop()
        leela_processes, bind_sockets = _run_leela_processes(loop, bin_dir,
                                                             home_path,
                                                             proj_name,
                                                             config)

        _run_nginx(loop, home_path, proj_name, config,
                   leela_processes,  bind_sockets)

    except BaseException as err:
        logger.error('leela daemon failed: {}'.format(err))
        _stop_processes(loop, leela_processes)
        return

    retcode = 1
    try:
        if config.monitor_changes:
            cor = _check_changes(os.path.join(home_path, 'services'))
            loop.run_until_complete(cor)
        else:
            tasks = []
            for proc in leela_processes:
                tasks.append(asyncio.async(proc.check_run()))


            for task in tasks:
                loop.run_until_complete(task)
    except KeyboardInterrupt:
        retcode = 0

    _stop_processes(loop, leela_processes)

    print('Done.')
    return retcode


def stop(home_path):
    proj_name = os.path.basename(home_path.rstrip('/'))
    daemon = Daemon('/tmp/leela-{}.pid'.format(proj_name))
    daemon.stop()
