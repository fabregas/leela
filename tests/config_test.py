
import aiohttp
import asyncio
import unittest
import yaml
import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from leela.utils.config import LeelaConfig

loop = asyncio.get_event_loop()

def async_test(f):
    def wrapper(*args, **kwargs):
        coro = asyncio.coroutine(f)
        future = coro(*args, **kwargs)
        loop.run_until_complete(future)
    return wrapper


class TestConfig(unittest.TestCase):
    @async_test
    def test_config_parser(self):
        config = LeelaConfig('/tmp/testproject')

        with self.assertRaisesRegex(
            ValueError, '<leela> does not found in YAML file'):
            config.parse({})

        with self.assertRaisesRegex(
            ValueError, '<services> does not found in YAML file'):
            config.parse({'leela': {}})

        with self.assertRaisesRegex(
            ValueError, '<leela.bind_address> does not found in YAML file'):
            config.parse({'leela': 'test',
                          'services': []})

        with self.assertRaisesRegex(
            ValueError, 'No one service found in config file'):
            config.parse({'leela': {'bind_address': 'localhost'},
                          'services': []})

        with self.assertRaisesRegex(
            ValueError,
            '<services.endpoint> does not found in YAML file'):
            config.parse({'leela': {'bind_address': 'localhost'},
                          'services': [{'invalid': 33}]})

        with self.assertRaisesRegex(
            ValueError,
            'Middlewares must be declared in list'):
            config.parse({'leela': {'bind_address': 'localhost'},
                          'middlewares': {'test': 4},
                          'services': []})

        # minimal config and check defaults ...
        config.parse({'leela': {'bind_address': 'localhost'},
                      'services': [
                          {'endpoint': 'test.com.TestService'}
                      ]})
        self.assertEqual(config.middlewares, [])
        self.assertEqual(config.bind_address, 'localhost')
        self.assertEqual(config.bind_port, 80)
        self.assertEqual(config.monitor_changes, False)
        self.assertEqual(config.leela_proc_count, -1)
        self.assertEqual(config.is_nginx_proxy, True)
        self.assertEqual(config.need_daemonize, True)
        self.assertEqual(config.username, 'leela')
        self.assertEqual(config.logger_config_path,
                         '/tmp/testproject/config/logger.yaml')
        self.assertEqual(config.static_path, '/tmp/testproject/www')
        self.assertEqual(config.services,
                         [{'srv_config': {},
                           'srv_endpoint': 'test.com.TestService',
                           'srv_middlewares': []}])

        # parse large valid config and check
        config = LeelaConfig('/tmp/testproject')
        with open('tests/valid_config.yaml') as conff:
            config.parse(yaml.load(conff))

        self.assertEqual(config.middlewares,
                         [{'endpoint': 'test.path.SomeMWClass',
                           'test_list': [4, 2, 2]},
                          {'endpoint': 'test.other.OtherMWClass',
                           'test_env': 'test value if not found'}])
        self.assertEqual(config.bind_address, '0.0.0.0')
        self.assertEqual(config.bind_port, 8080)
        self.assertEqual(config.monitor_changes, True)
        self.assertEqual(config.leela_proc_count, 2)
        self.assertEqual(config.is_nginx_proxy, True)
        self.assertEqual(config.need_daemonize, True)
        self.assertEqual(config.username, 'leela')
        self.assertEqual(config.logger_config_path, '/test/my_logger.yaml')
        self.assertEqual(config.static_path, '/my/custom/path')
        self.assertEqual(config.services,
                         [{'srv_endpoint': 'test.com.service.TestService',
                           'srv_config': {'test_dict':
                                          {'a': os.environ.get(
                                              'HOME', '/root'),
                                           'b': 'ok, thats all...'},
                                          'test_list':
                                          [33, 'test message', {'test': 90}],
                                          'test_int': 23,
                                          'test_str': 'this is string'},
                           'srv_middlewares': [
                               {'endpoint': 'some.middleware.path.MWClass',
                                'other_param': 42344.42,
                                'some_param': {'key': 'value',
                                               'env_k': None}}]},
                          {'srv_endpoint': 'test.other.service.TestService',
                           'srv_config': {'test': 'test value'},
                           'srv_middlewares': []}])

if __name__ == '__main__':
    unittest.main()
