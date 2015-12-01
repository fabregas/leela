Leela
=====

### Yet another framework for web development in Python3
#### We are using `asyncio` library for building extreme scalable web applications with extreme concurrency




  * [Installation](#installation)
  * [Leela management tool](#leela-management-tool)
  * [Leela configuration](#leela-configuration)
    * [Configuration file format](#configuration-file-format)
  * [Development](#development)
    * [Service methods](#service-methods)
    * [Authentication](#authentication)


Installation
============

You can install `leela` package using pip3:

    pip3 install git+https://github.com/fabregas/leela.git

Dependencies:

    PyYAML
    aiohttp
    nginx (don't need for development)


Leela management tool
=====================

You can create, start and stop your applications using **leela** tool.

    Usage:

    leela new-project <project name> [<base path>]
    or
    leela build [<project path>]
    or
    leela start <configuration name> [<project path>]
    or
    leela stop [<project path>]



You can create template for new project using following command:

    # leela new-project first_leela_project
    
        - downloading init project structure ...
        ================================================================================
        New Leela project is started at /home/fabregas/first_leela_project
        ================================================================================
        -> write your home HTML in www/index.html file
        -> save your HTML templates (for angularjs) in www/templates directory
        -> save your javascript scripts in www/js directory
        -> save your css files in www/css directory
        -> save your static images into www/img directory

        Build/rebuild your front-end dependencies using commands:
            # leela build

        Run your project in test mode using command:
            # leela start test
        ================================================================================

Now you can start test server:

    # cd first_leela_project
    # leela start test
    
Service should be started at http://127.0.0.1:8080/

Ok.. now you can implement your service using python3 and create veiw layer in HTML+CSS+AngularJS (if you need it)


Leela configuration
===================

You should specify your configuration files in `project_path/config` directory. By default,
leela has test.yaml and production.yaml configuration files.


Configuration file format
-------------------------

    leela:
        bind_address: <bind IP address>
        *bind_port: <bind port (80 by default)>
        *monitor_changes: <true|false (false by default)>
        *leela_proc_count: <leela workers count (-1 = cpu_count by default)
        *logger_config: <logger config file name (logger.yaml by default)>
        *need_daemonize: <true|false (true by default)>
        *user: <owner of the application (leela by default)>
        *static_path: <path to static files (project_path/www by default)>
        *nginx_proxy: <true|false (false by default)>
        *nginx_exec: <path to nginx exec (/usr/sbin/nginx by default)
        *python_exec: <path to Python exec (python3 by default)

        *ssl:
            *ssl_cert: <path to SSL certificate>
            *ssl_key: <path to SSL key>
            *ssl_only: <true|false (false by default)> 

        services:
            - endpoint: <service endpoint - python module path>
              *config: <configuration dictionary ({} by default)
	      *middlewares: <list of service middlewares>
            ...

    *middlewares:
	- endpoint: <middleware class endpoint>
	  *config: <configuration dictionary ({} by default)>

    *CORS:
        - *url_regex: <URL regexp for CORS apply>
          *allow_origin: <list of allowed origin ([] by default)>
          *allow_credentials: <true|false (false by default)>
          *allow_methods: <list of allowed HTTP methods ([GET, POST, PUT, PATCH, DELETE, OPTIONS] by default)>
          *allow_headers: <list of allowed HTTP headers (['x-requested-with', 'content-type', 'accept',
                                                        'origin', 'authorization', 'x-csrftoken'] by default)>
        ...

Parameters that marked as '\*' are optional.


Values of parameters in configuration file can be environment variables.
For example:

    test0: $TEST_ENV_VAR
    test1: $TEST_ENV_VAR || 'my test value'
    test2: $HOME || '/my/home'
    test3: null || helloo
    test4: 'my simple string value with "\|\|"'
    test5: '\$just string with "$" symbol'







Development
===========

Service methods
---------------

By default, you have service template in PROJECT_DIR/services/service.py :


    from leela.core import *
    from leela.db_support.mongo import MongoDB                                         
                                                                                    
    class MyService(AService):                                                         
        @classmethod                                                                   
        def initialize(cls, config):                                                   
            if 'db_name' not in config:                                                
                raise RuntimeError('db_name does not found in YAML config')            
            db = MongoDB(config.get('db_name', None))                                  
            yield from db.connect(config.get('db_hostname', '127.0.0.1'),              
                                  config.get('db_port', 27017))                        
                                                                                    
            Model.init(db)                                                             
                                                                                    
            return cls(db)
   
   
You can implement method with fillowing decorators:

> reg\_get   
> reg\_post   
> reg\_put   
> reg\_delete   

for GET, POST, PUT and DELETE HTTP methods.
Also you can specify WebSocket processor using following decorator:
> reg\_websocket

This decorators should accept some object path as first argument.
Decorated method should accept two arguments: data (parsed from request) and http_req (aiohttp.HTTPRequest object)
For example:

    @reg_get('str_len')
    def get_slen(self, data, http_req):
        return len(data.string)

You can perform GET request in your browser http://127.0.0.1:8080/api/str_len?string=testme and see '6' (length of string 'testme')

For uploading files you can use following decorators:
> reg\_postfile

for receiving file from multipart POST request
> reg\_uploadstream

for receiving file as a raw binary stream (good choice for large files for better async process)


### Authentication

You can request authentication (and authorization) for every API method. For example:

    @reg_post('personal_info', need_auth)
    def post_info(self, data, http_req):
        self.mandatory_check(data, 'city', 'age', 'sex')
        
        new_info = {'city': data.city, 'age': data.age, 'sex': data.sex}
        
        data.session.user.additional_info.update(new_info)
        yield from data.session.user.save()
        
    @reg_delete('personal_info', authorization('testrole'))
    def del_info(self, data, http_req):
        data.session.user.additional_info = {}
        yield from data.session.user.save()


You can implement username/password authentication just adding new user into database:
>user = User.create('newuser', 'userpwd', ['testrole'])   
>yield from user.save()

After that you can authenticate user using in-box API method /api/\_\_auth\_\_ . If authentication will be success, session_id will be stored in cookies.
You can logout using in-box API method /api/\_\_logout\_\_

#### ... to be continued ...
