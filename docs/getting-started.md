
# Getting Started

### About
Leela is yet another framework for web development in Python3

We are using `asyncio` library for building extreme scalable web applications with extreme concurrency

### Install Leela package

```sh
$ pip3 install leela
```

### Leela management tool

You can create, start and stop your applications using **leela** tool.

    Usage:

    leela new-project <project name> [<base path>]
    or
    leela build [<project path>]
    or
    leela start <configuration name> [<project path>]
    or
    leela stop [<project path>]


#### create new project

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

#### build/rebuild frontend

    # cd first_leela_project
    # leela build

#### start test server

    # leela start test
    
Service should be started at http://127.0.0.1:8080/

Ok.. now you can implement your service using python3 and create veiw layer in HTML+CSS+AngularJS (if you need it)


