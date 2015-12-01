
import os
import sys
import yaml


class LeelaConfig(object):
    def __init__(self, project_path):
        self.__project_path = project_path
        self.__config = {}

    def parse(self, config):
        self.__check_param(config, 'leela')
        self.__check_param(config, 'services')
        services_cfg = config['services']

        srv_mws = config.get('middlewares', [])
        if type(srv_mws) != list:
            raise ValueError('Middlewares must be declared in list')
        expanded_srv_mws = []
        for mw in srv_mws:
            expanded_mw = self.__parse_cf_params(mw)
            expanded_srv_mws.append(expanded_mw)
        self.__config['middlewares'] = expanded_srv_mws

        config = config['leela']

        self.__check_param(config, 'bind_address', 'leela')

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
        static_path = self.__gv(config, 'static_path', 'www')
        self.__config['static_path'] = os.path.join(self.__project_path,
                                                    static_path)

        services = []
        if not services_cfg:
            raise ValueError('No one service found in config file')
        for s_config in services_cfg:
            self.__check_param(s_config, 'endpoint', 'services')
            raw_srv_config = s_config.get('config', {})
            srv_config = self.__parse_cf_params(raw_srv_config)

            srv_mws = s_config.get('middlewares', [])
            if type(srv_mws) != list:
                raise ValueError('Middlewares must be declared in list')
            expanded_srv_mws = []
            for mw in srv_mws:
                expanded_mw = self.__parse_cf_params(mw)
                expanded_srv_mws.append(expanded_mw)

            services.append({'srv_endpoint': s_config['endpoint'],
                             'srv_config': srv_config,
                             'srv_middlewares': expanded_srv_mws})
        self.__config['services'] = services

        self.__config['python_exec'] = self.__gv(config, 'python_exec',
                                                  sys.executable or 'python3')

        self.__config['nginx_exec'] = self.__gv(config, 'nginx_exec',
                                                 '/usr/sbin/nginx')

        ssl_config = config.get('ssl', None)
        self.__config['ssl'] = bool(ssl_config)
        self.__config['ssl_cert'] = None
        self.__config['ssl_key'] = None
        self.__config['ssl_only'] = False
        if ssl_config:
            self.__check_param(ssl_config, 'cert', 'leela')
            self.__check_param(ssl_config, 'key', 'leela')
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


    def __check_param(self, config, param, parent=None):
        if not parent:
            parent = ''
        else:
            parent += '.'

        if type(config) != dict or param not in config:
            raise ValueError('<{}{}> does not found in YAML file'
                             .format(parent, param))

    def __check_type(self, param, val, rtype):
        if type(val) != rtype:
            try:
                val = rtype(val)
            except ValueError as err:
                raise ValueError('<{}> value should be an instance of "{}" '
                             '(but "{}" found)'
                             .format(param, rtype.__name__, val))
        return val

    def __parse_cf_params(self, config):
        parsed_dict = {}
        for key, value in config.items():
            if type(value) == str:
                parsed_dict[key] = self.__gv(config, key)
            elif type(value) == list:
                r_list = []
                for item in value:
                    if type(item) == str:
                        r_list.append(self.__gv({'key': item}, 'key'))
                    elif type(item) == dict:
                        r_list.append(self.__parse_cf_params(item))
                    else:
                        r_list.append(item)
                parsed_dict[key] = r_list
            elif type(value) == dict:
                parsed_dict[key] = self.__parse_cf_params(value)
            else:
                parsed_dict[key] = value

        return parsed_dict

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
