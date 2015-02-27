
import os
import sys
import json
import yaml
import signal
import logging
import logging.config
import multiprocessing
import asyncio.subprocess
import tempfile

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

	access_log /tmp/access_log;
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

	access_log /tmp/access_log;
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
        nossl_config = NGINX_SSL_ONLY_CONFIG % { 'running_port': port }
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
    def start(self, *args, env=None, input_s=None):
        if env is None:
            env = {}
        self.__args = args
        self.__env = env
        self.__input_s = input_s
        if self.__username:
            args = ['su', self.__username, '-s'] + list(args)

        self.__proc = yield from \
            asyncio.create_subprocess_exec(*args,
                                           stdout=self.__out,
                                           stderr=asyncio.subprocess.PIPE,
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


def start(bin_dir, home_path, config):
    logger_config_path = config.logger_config_path
    leela_proc_count = config.leela_proc_count
    is_nginx_proxy = config.is_nginx_proxy
    username = config.username

    if os.path.exists(logger_config_path):
        logging.config.dictConfig(yaml.load(open(logger_config_path)))
    else:
        print('WARNING! Logger config does not found at {}'
              .format(logger_config_path))
        logger_config_path = '--noconf'

    if leela_proc_count > 1:
        is_nginx_proxy = True

    if is_nginx_proxy:
        _check_root(config)
    else:
        username = None

    proj_name = os.path.basename(home_path.rstrip('/'))
    if config.need_daemonize:
        daemon = Daemon('/tmp/leela-{}.pid'.format(proj_name))
        daemon.start()

    # with daemon context
    if leela_proc_count <= 0:
        leela_proc_count = multiprocessing.cpu_count()

    loop = asyncio.get_event_loop()
    leela_processes = []
    bind_sockets = []

    for i in range(leela_proc_count):
        s_mgmt = ServiceMgmt(username)
        is_unixsocket = is_nginx_proxy
        lp_is_ssl = config.ssl and not is_unixsocket
        if not is_nginx_proxy:
            lp_bind_addr = config.bind_address
        else:
            tmpdir = tempfile.gettempdir()
            tmp_file = os.path.join(tmpdir,
                                    '{}-{}.unixsocket'.format(proj_name, i))
            if os.path.exists(tmp_file):
                os.unlink(tmp_file)
            lp_bind_addr = tmp_file

        bind_sockets.append(lp_bind_addr)
        env = { 'PYTHONPATH': os.path.abspath(os.path.dirname(leela.__file__))
                             .rstrip('leela') }

        params_str = json.dumps([home_path, logger_config_path,
                                 config.srv_endpoint,
                                 config.srv_config, lp_is_ssl,
                                 lp_bind_addr, is_unixsocket])

        cor = s_mgmt.start(config.python_exec,
                           os.path.join(bin_dir, 'leela-worker'),
                           '{}-{}'.format(proj_name, i),
                           env=env, input_s=params_str)

        loop.run_until_complete(cor)
        leela_processes.append(s_mgmt)


    try:
        if is_nginx_proxy:
            parts = config.bind_address.split(':')
            if len(parts) == 2:
                port = parts[1]
            else:
                port = 80
            static_path = os.path.abspath(os.path.join(home_path, 'www'))

            cnf_file = _make_nginx_config(username, proj_name, bind_sockets, port,
                            static_path, config.ssl_cert, config.ssl_key,
                            config.ssl_only)
            nginx_mgmt = ServiceMgmt()
            cor = nginx_mgmt.start(config.nginx_exec, '-c', cnf_file)
            loop.run_until_complete(cor)
            leela_processes.append(nginx_mgmt)
    except BaseException as err:
        logger.error('leela daemon failed: {}'.format(err))
        # FIXME : stop already started services...


    tasks = []
    for proc in leela_processes:
        tasks.append(asyncio.async(proc.check_run()))

    for task in tasks:
        try:
            loop.run_until_complete(task)
        except KeyboardInterrupt:
            break

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

    loop.close()
    print('Done.')


def stop(home_path):
    proj_name = os.path.basename(home_path.rstrip('/'))
    daemon = Daemon('/tmp/leela-{}.pid'.format(proj_name))
    daemon.stop()
