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

    def __init__(self, input_file, num_traits):
        self.input_file = input_file
        self.num_traits = num_traits
        self.groups = defaultdict(list)

    def _validate(self):
        """Make sure file is valid."""
        if not os.path.isfile(self.input_file):
            raise ValueError("File does not exist: {}".format(self.input_file))

        if not self.input_file.endswith('.csv'):
            raise ValueError("File is not a .csv: {}".format(self.input_file))

    def _parse_file(self):
        """Reads individuals from the submitted input file."""
        with open(self.input_file) as infile:
            reader = csv.reader(infile)

            # Skip header
            next(reader)

            # Read all individuals from file
            for row in reader:
                name = row[0]
                group = row[1]
                availability = [int(x) for x in row[2 + self.num_traits:]]
                traits = [float(x) for x in row[2:2+self.num_traits]]

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
        self._validate()
        self._parse_file()
        self._normalize_traits()
        return self._generate_lists()
