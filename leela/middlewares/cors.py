import re
import asyncio

from leela.core.middleware import LeelaMiddleware
from leela.core.sessions import BaseSessionManager, InMemorySessionsManager


class CORS(object):
    def __init__(self, rule):
        if 'url_regex' not in rule:
            raise RuntimeError('url_regex is expected for CORS config')

        self.url_regex = re.compile(rule['url_regex'])
        self.allow_origin = rule.get('allow_origin', [])
        self.allow_credentials = rule.get('allow_credentials', False)
        self.allow_methods = rule.get('allow_methods',
                                      ['GET', 'POST', 'PUT', 'PATCH',
                                       'DELETE', 'OPTIONS'])
        self.allow_headers = rule.get('allow_headers',
                                      ['x-requested-with', 'content-type',
                                       'accept', 'origin', 'authorization',
                                       'x-csrftoken'])

        self.http_headers = {
            'Access-Control-Allow-Origin':  ' '.join(self.allow_origin),
            'Access-Control-Allow-Credentials':
                str(self.allow_credentials).lower(),
            'Access-Control-Allow-Methods': ', '.join(self.allow_methods),
            'Access-Control-Allow-Headers': ', '.join(self.allow_headers)}

    def __repr__(self):
        return 'CORS({})'.format(self.url_regex)

    def check(self, request):
        if request.method not in self.allow_methods:
            raise web.HTTPMethodNotAllowed(request.method, self.allow_methods,
                                           headers=self.http_headers())

    def matched(self, url):
        return bool(self.url_regex.match(url))


class CorsMiddleware(LeelaMiddleware):
    def __init__(self, rules):
        self.__cors_rules = [CORS(rule) for rule in rules]

    def _find_cors_rule(self, path):
        for cors_rule in self.__cors_rules:
            if cors_rule.matched(path):
                return cors_rule
        return None

    @asyncio.coroutine
    def on_request(self, request, data, params, cache):
        cors_rule = self._find_cors_rule(request.path)

        if cors_rule:
            cors_rule.check(request)

        cache['cors_rule'] = cors_rule

    @asyncio.coroutine
    def on_response(self, request, data, response, params, cache):
        cors_rule = cache.get('cors_rule')

        if request.method == 'OPTIONS':
            cors_rule = self._find_cors_rule(request.path)
            if cors_rule:
                response.headers['Allow'] = ','.join(cors_rule.allow_methods)
            else:
                response.headers['Allow'] = \
                    'HEAD,GET,PUT,POST,PATCH,DELETE,OPTIONS'

        if cors_rule:
            response.headers.update(cors_rule.http_headers)

        return response
