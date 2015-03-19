Leela
=====

### Yet another framework for web development in Python3
#### We are using `asyncio` library for building extreme scalable web applications with extreme concurrency


Installation
------------

You can install `leela` package using pip3:

    pip3 install git+https://github.com/fabregas/leela.git

Dependencies:

    PyYAML (check the name for your linux distro)
    nginx (don't need for development)


Start your project
------------------

You can create template for new project using following command:

    # leela new-project first_leela_project
    
        - downloading leela.js ...
        - downloading angular.min.js ...
        ================================================================================
        New Leela project is started at /home/fabregas/first_leela_project
        ================================================================================
        -> write your home HTML in www/index.html file
        -> save your HTML templates (for angularjs) in www/templates directory
        -> save your javascript scripts in www/js directory
        -> save your css files in www/css directory
        -> save your static images into www/img directory
        ================================================================================

Now you can start test server:

    # cd first_leela_project
    # leela start test
    
Service should be started at http://127.0.0.1:8080/

Ok.. now you can implement your service using python3 and create veiw layer in HTML+CSS+AngularJS (if you need it)


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
