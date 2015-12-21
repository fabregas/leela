
# Services development

### Required knowledge

Leela services should be written in python3 using asyncio standart library.
You should familiarize yourself with the [asyncio](https://docs.python.org/3/library/asyncio.html) and [aiohttp](http://aiohttp.readthedocs.org/) libraries.


### Service class

Every service is python class inherited from leela.core.service.LeelaService.

If you need some configuration parameters for your service, declare constructor in service with this parameters.
After that you can pass this parameters to service in configuration YAML file (see [Configuration file](/docs/conf-file.md) section).

If you need some async work that must be done when service start, implement `start()` coroutune method.

If you need some work on service stopping, implement `destroy()` coroutune method.

For exmample: 

```python
class MyCoolService(LeelaService):
    def __init__(self, database_uri, reconnect=False):
        self.dbconn = Database(database_uri, reconnect)

    @asyncio.coroutine
    def start(self):
        yield from self.dbconn.connect()

    @asyncio.coroutine
    def destroy(self):
        yield from self.dbconn.disconnect()
```

### Service API

For creating leela service API decorate your service methods with `leela_*` decorators from leela.core.decorators.

For example:

```python
from leela.core.decorators import leela_get

class MyCoolService(LeelaService):
    @leela_get('users')
    def get_users(self, data):
	return ['user #1', 'user #2', 'anonymous']
```

In this example we create method binded on HTTP path /api/users for GET method and returns list of users names (json packed by default)

#### Leela decorators

Leea framework has the several smart decorators:
   * **leela_get** - wrapper for GET HTTP method
   * **leela_post** - wrapper for POST HTTP method
   * **leela_put** - wrapper for PUT HTTP method
   * **leela_delete** - wrapper for DELETE HTTP method
   * **leela_form_post** - wrapper for web form submitting (POST HTTP method with MIME type application/x-www-form-urlencoded)
   * **leela_uploadstream** - wrapper for binary stream uploading
   * **leela_websocket** - wrapper for websocket handling

All this decorators has uniform syntax:

```python
@leela_*(obj_path, *, req_validator=None, resp_validator=None, **mw_params):
def <some_method_name>(self, request):
   ...

```

where:
   * `obj_path` - part of URL that identifies API method (full API method endpoint is /api/<object_path>)
   * `req_validator` - TBD
   * `resp_validator` - TBD
   * `mw_params` - the keyword arguments that should be passed to middlewares (see [Middlewares](/docs/middlewares.md) section for details)
   * `request` - instance of [SmartRequest](#smartrequest)


**leela_get**, **leela_post**, **leela_put**, **leela_delete** are just wrappers for GET, POST, PUT and DELETE HTTP methods.

**leela_form_post** wrapper provide key-value data from HTTP FORM in ``request.data``

**leela_uploadstream** wrapper provide interface for uploading binary stream.
``request.data.stream`` will contain file-like object for reading in this case

For example:

```python
@leela_uploadstream('calc_checksum')
def calc_checksum(self, req):
    checksum = hashlib.sha1()
    while True:
        chunk = yield from req.data.stream.readany()
        if not chunk:
            break
        checksum.update(chunk)
    return checksum.hexdigest()
```

**leela_websoket** wrapper provide interface to server-side WebSocket.
``request.data.websocket`` will contain instance of aiohttp.web.WebSocketResponse.
Wrapped method MUST return this instance after websocket processing.

For example:

```python
@leela_websocket('myws')
def proc_ws(self, req):
   ws = req.data.websocket
   while True:
       msg = yield from ws
       if msg.data == 'close':
            yield from ws.close()
       else:
            ws.send_str('echo: ' + msg.data)
   print('websocket connection closed')
   return ws
```


#### "raw" API method decorator
Leela framework also provides **leela_raw** decorator for some custom HTTP request/response processing.

Wrapped method MUST return instance of aiohttp.web.Response.

Decorator syntax:

```python
@leela_raw(http_method, obj_path)
def <some_method_name>(self, request):
   ...
   return aiohttp.web.Response(...)
```
where:
   * `http_method` - HTTP method name string (GET, POST, DELETE, etc.)
   * `obj_path` - part of URL that identifies API method (full API method endpoint is /api/<object_path>)
   * `request` - aiohttp.web.Request object
Raw leela method MUST return instance of aiohttp.web.Response


#### SmartRequest

SmartRequest instances has following attributes:
   * `query` - key-value structure (parsed from HTTP URL query string)
   * `params` - key-value structure (parsed from variable routes like `/user/{user_id}`)
   * `data` - key-value structure (parsed from HTTP body)
   * `session` - Session instance (or None if session middleware dont included in project)

