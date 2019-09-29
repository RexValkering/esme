import os
import yaml
from collections import namedtuple

from .common import SolutionScore
from .algorithms import evaluate_schedule
from .parsers import InputFileParser, GroupScheduleParser


class Solution(object):

    config = None
    individuals = None
    groups = None
    schedule = None
    score = None

    def __init__(self, solution_name):
        self.solution_name = solution_name
        self._validate_name()
        self._load_config()
        self._load_individuals()
        self._load_schedule()
        self._load_progress()
        self._calculate_score()

    def _resolve_input(self, extension):
        """Retrieve the path to the file for a given extension."""
        return '{}_{}.csv'.format(self.solution_name, extension)

    def _resolve_config(self):
        return '{}_config.yaml'.format(self.solution_name)

    def _validate_name(self):
        """Ensure all required files exist."""
        extensions = ['groups', 'schedule', 'progress']

        for extension in extensions:
            filename = self._resolve_input(extension)
            if not os.path.isfile(filename):
                raise ValueError('File `{}` does not exist.'.format(filename))

        if not os.path.isfile(self._resolve_config()):
            raise ValueError('File `{}` does not exist.'.format(filename))

    def _load_config(self):
        """Load configuration file"""
        parameters = [
            'num_traits',
            'num_info',
            'trait_weights',
            'min_members_per_group',
            'max_members_per_group',
            'num_boats',
            'courses_per_team',
            'min_available',
            'population',
            'profile',
            'timeslots'
        ]

        # Parse config file. These override default values.
        with open(self._resolve_config()) as infile:
            self.config = yaml.safe_load(infile)

        for key in self.config:
            if key not in parameters:
                raise ValueError("Unknown config parameter: {}".format(key))

    def _load_individuals(self):
        """Load the file with individuals and groups."""
        parser = InputFileParser(self._resolve_input('groups'),
                                 self.config['num_info'],
                                 self.config['num_traits'],
                                 sum(self.config['timeslots']))
        self.individuals, self.groups = parser.parse()
        self.groups.sort()

    def _load_schedule(self):
        """Load the file with the group schedule."""
        parser = GroupScheduleParser(self._resolve_input('schedule'), self.groups)
        self.schedule = parser.parse()

    def _load_progress(self):
        pass

    def _calculate_score(self):
        score, maximum = 0, 0
        for day in self.schedule:
            for timeslot in day:
                for team in timeslot:
                    for individual in team.members:
                        score += sum(individual.scheduled_timeslots_availability)
                        maximum += len(individual.scheduled_timeslots_availability)

        self.score = round(100.0 * score / maximum, 1)