import os
import csv
from collections import defaultdict
import numpy as np
from .entities import SchedulingIndividual, SchedulingGroup


class InputFileParser(object):
    """Converts a single input file into individuals and groups.

    Args:
        input_file: CSV file with individuals
        num_traits: the number of traits in the file
    """

    def __init__(self, input_file, num_traits, num_timeslots=None):
        self.input_file = input_file
        self.num_traits = num_traits
        self.groups = defaultdict(list)
        self.detected_slots = num_timeslots

    def _validate_file(self):
        """Make sure file is valid."""
        if not os.path.isfile(self.input_file):
            raise ValueError("File does not exist: {}".format(self.input_file))

        if not self.input_file.endswith('.csv'):
            raise ValueError("File is not a .csv: {}".format(self.input_file))

    def _validate_row(self, row):
        if not self.detected_slots:
            self.detected_slots = len(row) - 2 - self.num_traits

        valid_row_length = 2 + self.num_traits + self.detected_slots
        if len(row) != valid_row_length:
            raise ValueError("Row does not have valid number of columns: {}".format(str(row)))

        if any([int(availability) not in [0, 1] for availability in self._extract_availability(row)]):
            raise ValueError("Incorrect value in availability: {}".format(self._extract_availability(row)))

    def _extract_traits(self, row):
        return row[2:2 + self.num_traits]

    def _extract_availability(self, row):
        return row[2 + self.num_traits:]

    def _parse_file(self):
        """Reads individuals from the submitted input file."""
        with open(self.input_file, encoding="latin-1") as infile:
            reader = csv.reader(infile)

            # Skip header
            next(reader)

            # Read all individuals from file
            for row in reader:
                self._validate_row(row)
                name = row[0]
                group = row[1]
                availability = [int(x) for x in self._extract_availability(row)]
                traits = [float(x) for x in self._extract_traits(row)]

                self.groups[group].append(SchedulingIndividual(name, availability, traits=traits))

    def _normalize_traits(self):
        """Each trait may have a different distribution. Normalize the traits."""
        averages, stdevs = [], []
        individuals = [individual for group in self.groups for individual in self.groups[group]]
        for trait in range(self.num_traits):
            trait_values = [individual.traits[trait] for individual in individuals]
            averages.append(np.mean(trait_values))
            stdevs.append(np.std(trait_values))

        for individual in individuals:
            individual.normalize_traits(averages, stdevs)

    def _generate_lists(self):
        """Generate two lists from input data and return them.

        Returns:
            individuals: list of unassigned individuals
            groups: list of groups with assigned individuals
        """
        individuals_from_file = []
        groups_from_file = []

        for group_name, members in self.groups.items():

            if group_name:
                group = SchedulingGroup(name=group_name, members=members)
                groups_from_file.append(group)
            else:
                individuals_from_file.extend(members)

        return individuals_from_file, groups_from_file

    def parse(self):
        """Parses input file and returns results.

        Returns:
            individuals: list of unassigned individuals
            groups: list of groups with assigned individuals
        """
        self._validate_file()
        self._parse_file()
        self._normalize_traits()
        return self._generate_lists()


class GroupScheduleParser(object):
    """Converts a single input file into a schedule

    Args:
        input_file: CSV file with the schedule
        groups: all groups that should be present in the schedule
    """

    schedule = None
    lookup = None

    def __init__(self, input_file, groups):
        self.input_file = input_file
        self.groups = groups
        self.lookup = {group.name: group for group in self.groups}

    def _validate_file(self):
        pass

    def _parse_file(self):
        with open(self.input_file) as infile:
            reader = csv.reader(infile)
            next(reader)
            self.schedule = [
                [self._lookup_list(column.split(', ')) if column else [] for column in row[1:]]
                for row in reader
            ]

    def _lookup_list(self, groups):
        return [self.lookup[group] for group in groups]

    def _enrich_groups(self):
        index = 0
        for day, timeslots in enumerate(self.schedule):
            for timeslot, groups in enumerate(timeslots):
                for group in groups:
                    group.add_scheduled_timeslot((day, timeslot))
                    for individual in group.members:
                        individual.scheduled_timeslots_availability.append(
                            individual.preferences[index])
                index += 1

    def _validate_groups(self):
        frequency = [len(group.scheduled_timeslots) for group in self.groups]
        if min(frequency) < max(frequency):
            raise ValueError('The number of scheduled timeslots is not equal for all groups.')

    def _generate_lists(self):
        return self.schedule

    def parse(self):
        """Parses input file and returns results.

        Returns:
            individuals: list of unassigned individuals
            groups: list of groups with assigned individuals
        """
        self._validate_file()
        self._parse_file()
        self._enrich_groups()
        self._validate_groups()
        return self._generate_lists()
