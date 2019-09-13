"""This file is used by Python Celery to launch the Celery application and register tasks."""
# from __future__ import absolute_import, unicode_literals
import json

from celery import Celery
from .solver import SchedulingSolver
from .common import parse_args


app = Celery('tasks', broker='pyamqp://guest@localhost//')


def is_number(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


@app.task(ignore_result=True)
def create_schedule(data, input_files, config_file, output):
    def report_progress(data):
        with open('{}_progress.json'.format(output), 'w') as outfile:
            json.dump(data, outfile)

    solver_args = {
        'config': config_file,
        'input': input_files,
        'output': output,
        'min_members_per_group': data['min_team_size'],
        'max_members_per_group': data['max_team_size'],
        'num_boats': data['num_boats'],
        'courses_per_team': data['courses_per_team'],
        'min_available': '1'
    }

    args = []
    for key, value in solver_args.items():
        args += ['--{}'.format(key), str(value)]
    parsed_args = parse_args(args)
    for key, value in vars(parsed_args).items():
        if isinstance(value, str) and is_number(value):
            setattr(parsed_args, key, int(value))

    solver = SchedulingSolver(parsed_args)
    solver.set_progress_callback(report_progress)
    solver.run(report=False)
