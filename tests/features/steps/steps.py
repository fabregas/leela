#!/usr/bin/python3

import os
import sys
import http.client as httplib
import tempfile
import time
import multiprocessing
from subprocess import Popen, PIPE
from behave import *

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__),
                           '../../../'))
leela_bin = os.path.join(base_dir, 'bin/leela')
test_data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                '../data'))

def call_leela(*args):
    s_args = ['python3', leela_bin]
    proc = Popen(s_args + list(args), stdout=PIPE, stderr=PIPE,
                  env={'PYTHONPATH': base_dir})
    return proc

def sudo_call_leela(*args):
    cmd = 'sudo PYTHONPATH="%s" python3 %s %s' % (base_dir, leela_bin, ' '.join(args))
    #proc = Popen(cmd, stdout=PIPE, stderr=PIPE)
    #return proc
    ret = os.system(cmd)

def call_cmd(cmd):
    proc = Popen(cmd, shell=True, stdout=PIPE)
    return proc.communicate()[0]

@given(u'I create leela project "{proj_name}"')
def step_impl(context, proj_name):
    work_dir = os.path.join(context.work_dir, proj_name)
    print('Creating leela project at {}'.format(work_dir))

    proc = call_leela('new-project', proj_name, context.work_dir)
    out, err = proc.communicate()
    if proc.returncode != 0:
        print('RETCODE =', proc.returncode)
        print(out.decode())
        print(err.decode())
        raise RuntimeError('leela new-project failed!')

    ret = os.system('cp %s %s/'%(os.path.join(test_data_dir, 'test-act.yaml'),
                          os.path.join(work_dir, 'config')))

    os.system('mkdir %s/activities'%work_dir)
    os.system('cp %s %s/activities'%(os.path.join(test_data_dir, 'activity.py'),
                                     work_dir))

    context.work_dir = work_dir 

@when(u'I start leela with "{config_name}" config as "{user}"')
def step_impl(context, config_name, user):
    if user == 'superuser':
        sudo_call_leela('start', config_name, context.work_dir)
        context.for_clean.append(lambda: sudo_call_leela('stop', context.work_dir))
    else:
        context.proc = call_leela('start', config_name, context.work_dir)
        context.processes.append(context.proc)


@then(u'I see leela failed with message "{f_message}"')
def step_impl(context, f_message):
    out = context.proc.communicate()[0]
    assert f_message in out.decode(), 'Unexpected output: %s'%out


@then(u'I see leela nodaemon')
def step_impl(context):
    time.sleep(1)
    rcode = context.proc.poll()
    if rcode is not None:
        print('OUT: ', context.proc.communicate())
        raise RuntimeError('leela process does not found!')

@then(u'I see leela daemon')
def step_impl(context):
    time.sleep(.5)

    ps_out = call_cmd('ps aux | grep "leela start"') 
    count = len(ps_out.decode().split('\n')) - 3
    #print('=========', ps_out, count)
    assert count == 1, 'processes found - {}'.format(count)

@then(u'I see "{workers_count}" leela worker binded on "{socket_type}" socket')
def step_impl(context, workers_count, socket_type):
    if workers_count == 'cpu_count':
        workers_count = 2*multiprocessing.cpu_count()
    ps_out = call_cmd('ps aux | grep leela-worker') 
    count = len(ps_out.decode().split('\n')) - 3
    #print('=========', ps_out, count)
    assert count == int(workers_count), 'processes found - {}'.format(count)

    conn = httplib.HTTPConnection("127.0.0.1:8080")
    conn.request("GET", "/")
    conn.getresponse()
    conn.close()

@then(u'get "{path}" with code "{code}"')
def step_impl(context, path, code):
    conn = httplib.HTTPConnection("127.0.0.1:8080")
    conn.request("GET", path)
    r = conn.getresponse()
    assert r.status == int(code), r.reason
    conn.close()


@then(u'contain "{text}" in "{path}" body')
def step_impl(context, text, path):
    conn = httplib.HTTPConnection("127.0.0.1:8080")
    conn.request("GET", path)
    r = conn.getresponse()
    data = r.read().decode()
    assert (text in data) == True, data
    conn.close()

@then(u'contain header "{header}" in "{path}"')
def step_impl(context, header, path):
    conn = httplib.HTTPConnection("127.0.0.1:8080")
    conn.request("GET", path)
    r = conn.getresponse()
    for cheader, value in r.getheaders():
        if header.lower() == cheader.lower():
            break
    else:
        raise Exception('header "%s" does not found! Received headers: %s'%
                (header, str(r.getheaders())))
    conn.close()


@then(u'not contain header "{header}" in "{path}"')
def step_impl(context, header, path):
    conn = httplib.HTTPConnection("127.0.0.1:8080")
    conn.request("GET", path)
    r = conn.getresponse()
    for cheader, value in r.getheaders():
        if header.lower() == cheader.lower():
            raise Exception('header "%s" not expected!! Received headers: %s'%
                (header, str(r.getheaders())))

    conn.close()
