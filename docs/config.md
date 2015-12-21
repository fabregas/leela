
# Configuration

Leela services should be configured using YAML configuration file.
Configuration file should be placed into ``$PROJ_DIR/conf/`` directory.

You can start leela server with some configuration file using **leela** utility:

```bash
leela start <config_file_name>
```

where ``config_file_name`` is the name of configuration file. Can be without ``.yaml`` filename extension (for example, `test_config` or `test_config.yaml`).


## Configuration file format


```yaml

leela:
    bind_address: <bind address>
    bind_port:  <bind port (80 by default)>
    monitor_changes: <true|false (false by default)>
    leela_proc_count: <leela workers count (-1 = cpu_count by default)
    logger_config: <logger config file name (logger.yaml by default)>
    need_daemonize: <true|false (true by default)>
    user: <owner of the application (leela by default)>
    static_path: <path to static files ([project_path]/www by default)>
    nginx_proxy: <true|false (false by default)>
    nginx_exec: <path to nginx exec (/usr/sbin/nginx by default) 
    python_exec: <path to Python exec (python3 by default)

middlewares:
    - endpoint: <middleware endpoint, python module path>
      <mw_conf_key1>: <mw_conf_val1>
      <mw_conf_key2>: <mw_conf_val2>
      ...
    ...

services:
    - endpoint: <service endpoint - python module path>
      config:
         <srv_conf_key1>: <srv_conf_val1>
         <srv_conf_key2>: <srv_conf_val2>
	 ...
      middlewares:
         - endpoint: <middleware endpoint, python module path>
           <mw_conf_key1>: <mw_conf_val1>
           <mw_conf_key2>: <mw_conf_val2>
           ...
         ...
    ...
```

Values of parameters in configuration file can be environment variables. For example:

```yaml
test0: $TEST_ENV_VAR
test1: $TEST_ENV_VAR || 'my test value'
test2: $HOME || '/my/home'
test3: null || helloo
test4: 'my simple string value with "\|\|"'
test5: '\$just string with "$" symbol'
```
