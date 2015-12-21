
import os
import signal
import tempfile


def before_scenario(context, scenario):
    context.processes = []
    context.for_clean = []

def after_scenario(context, scenario):
    for process in context.processes:
        if process.returncode is None:
            process.send_signal(signal.SIGINT)
            process.wait()

    for routine in context.for_clean:
        print('cleaning %s ...'%routine)
        routine()

def before_all(context):
    context.work_dir = tempfile.mkdtemp(prefix='leela_proj-')

    #context.config.setup_logging()

def after_all(context):
    if 'work_dir' in context:
        print('removing test dir {}'.format(context.work_dir))
        os.system('rm -rf {}'.format(context.work_dir))

