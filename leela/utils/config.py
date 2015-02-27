
import os
import sys

class LeelaConfig(object):
    def __init__(self, project_path):
        self.__project_path = project_path
        self.__config = {}

    def parse(self, config):
        self.__check_param(config, 'leela')

        config = config['leela']
        self.__check_param(config, 'bind_address')
        self.__check_param(config, 'service')

        self.__config['bind_address'] = config['bind_address']
        self.__config['monitor_changes'] = config.get('monitor_changes', False)
        self.__config['leela_proc_count'] = config.get('leela_proc_count', -1)
        self.__config['is_nginx_proxy'] = config.get('nginx_proxy',
                                        self.__config['leela_proc_count'] != 1)
        self.__config['need_daemonize'] = config.get('daemonize', True)
        self.__config['username'] = config.get('username',
                                          os.environ.get('SUDO_USER', 'leela'))
        logger_config = config.get('logger_config', 'logger.yaml')
        self.__config['logger_config_path'] = os.path.join(self.__project_path,
                                                      'config', logger_config)

        service_cfg = config['service']
        self.__check_param(service_cfg, 'endpoint')
        self.__config['srv_endpoint'] = service_cfg['endpoint']
        self.__config['srv_config'] = service_cfg.get('config', {})

        self.__config['python_exec'] = config.get('python_exec',
                                                  sys.executable)

        self.__config['nginx_exec'] = config.get('nginx_exec',
                                                  '/usr/sbin/nginx')

        ssl_config = config.get('ssl', None)
        self.__config['ssl'] = bool(ssl_config)
        self.__config['ssl_cert'] = None
        self.__config['ssl_key'] = None
        self.__config['ssl_only'] = False
        if ssl_config:
            self.__check_param(ssl_config, 'cert')
            self.__check_param(ssl_config, 'key')
            self.__config['ssl_cert'] = os.path.join(self.__project_path,
                                                     'config',
                                                     ssl_config['cert'])
            self.__config['ssl_key'] = os.path.join(self.__project_path,
                                                    'config',
                                                    ssl_config['key'])
            self.__config['ssl_only'] = ssl_config.get('ssl_only', False)

    def __check_param(self, config, param):
        if type(config) != dict or param not in config:
            raise ValueError('<{}> scope is expected in YAML file.'
                             .format(param))

    def __getattr__(self, attr):
        if attr not in self.__config:
            raise RuntimeError('Config parameter {} does not found!'
                               .format(attr))

        return self.__config[attr]
