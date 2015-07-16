
import os
import sys
import yaml


class LeelaConfig(object):
    def __init__(self, project_path):
        self.__project_path = project_path
        self.__config = {}

    def parse(self, config):
        self.__check_param(config, 'leela')

        self.__config['CORS'] = config.get('CORS', {})
        config = config['leela']

        self.__check_param(config, 'bind_address')
        self.__check_param(config, 'services')

        self.__config['bind_address'] = self.__gv(config, 'bind_address')
        self.__config['bind_port'] = self.__gv(config, 'bind_port', 80, int)
        self.__config['monitor_changes'] = self.__gv(config,
                                                     'monitor_changes',
                                                     False, bool)
        self.__config['leela_proc_count'] = self.__gv(config, 
                                                      'leela_proc_count',
                                                      -1, int)
        def_proxy = self.__config['leela_proc_count'] != 1
        self.__config['is_nginx_proxy'] = self.__gv(config, 'nginx_proxy',
                                                    def_proxy)
        self.__config['need_daemonize'] = self.__gv(config, 'daemonize',
                                                    True, bool)
        def_user = os.environ.get('SUDO_USER', 'leela')
        self.__config['username'] = self.__gv(config, 'username', def_user)
        logger_config = self.__gv(config, 'logger_config', 'logger.yaml')
        self.__config['logger_config_path'] = os.path.join(self.__project_path,
                                                           'config',
                                                           logger_config)
        self.__config['static_path'] = self.__gv(config, 'static_path')

        services_cfg = config['services']
        services = []
        for s_config in services_cfg:
            self.__check_param(s_config, 'endpoint')
            raw_srv_config = s_config.get('config', {})
            srv_config = {}
            for param in raw_srv_config:
                srv_config[param] = self.__gv(raw_srv_config, param)
            services.append({'srv_endpoint': s_config['endpoint'],
                             'srv_config': srv_config })
        self.__config['services'] = services

        activities_cfg = config.get('activities', [])
        activities = []
        for a_config in activities_cfg:
            self.__check_param(a_config, 'endpoint')
            raw_act_config = a_config.get('config', {})
            act_config = {}
            for param in raw_act_config:
                act_config[param] = self.__gv(raw_act_config, param)
            activities.append({'act_endpoint': a_config['endpoint'],
                               'act_config': act_config})
        self.__config['activities'] = activities

        self.__config['python_exec'] = self.__gv(config, 'python_exec',
                                                  sys.executable or 'python3')

        self.__config['nginx_exec'] = self.__gv(config, 'nginx_exec',
                                                 '/usr/sbin/nginx')

        s_mgr = config.get('sessions_manager', {})
        self.__config['sessions_manager'] = s_mgr.get('endpoint', None)

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
                                                     self.__gv(ssl_config,
                                                               'cert'))
            self.__config['ssl_key'] = os.path.join(self.__project_path,
                                                    'config',
                                                    self.__gv(ssl_config,
                                                              'key'))
            self.__config['ssl_only'] = self.__gv(ssl_config, 'ssl_only',
                                                  False, bool)


    def __check_param(self, config, param):
        if type(config) != dict or param not in config:
            raise ValueError('<{}> scope is expected in YAML file.'
                             .format(param))

    def __check_type(self, param, val, rtype):
        if type(val) != rtype:
            try:
                val = rtype(val)
            except ValueError as err:
                raise ValueError('<{}> value should be an instance of "{}" '
                             '(but "{}" found)'
                             .format(param, rtype.__name__, val))
        return val

    def __gv(self, config, param, default=None, ret_type=None):
        '''get value of config param

        Examples of config params:
            test1: $TEST_ENV_VAR || 'my test value'
            test2: $HOME || '/my/home'
            test3: null || helloo
            test4: 'my simple string value with "\|\|"'
            test5: '\$just string with "$" symbol'
        '''

        if param not in config:
            return default

        val = config[param]

        if type(val) not in (str, bytes):
            if ret_type:
                self.__check_type(param, val, ret_type)
            return val

        if '||' in val:
            parts = val.split('||')
        else:
            parts = [val]

        for item in parts:
            item = item.strip()
            if item.startswith('$'):
                val = os.environ.get(item[1:], None)
            else:
                val = yaml.load(item)
            if val:
                break

        if type(val) == str:
            val = val.replace('\\|\\|', '||').replace('\$', '$')

        if ret_type:
            val = self.__check_type(param, val, ret_type)

        return val

    def __getattr__(self, attr):
        if attr not in self.__config:
            raise RuntimeError('Config parameter {} does not found!'
                               .format(attr))

        return self.__config[attr]
