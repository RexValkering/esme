import os
import csv
from collections import defaultdict
import numpy as np
from .entities import SchedulingIndividual, SchedulingGroup


def parse_individuals_file(input_file, num_traits):
    """Load the groups from a csv file."""

    if not os.path.isfile(input_file):
        print("File does not exist: {}".format(input_file))
        exit()

    if not input_file.endswith('.csv'):
        print("File is not a .csv: {}".format(input_file))
        exit()

    groups = defaultdict(list)
    individuals_from_file = []
    groups_from_file = []

    with open(input_file) as infile:
        reader = csv.reader(infile)

        # Skip header
        next(reader)

        # Read all individuals from file
        for row in reader:
            name = row[0]
            group = row[1]
            availability = [int(x) for x in row[2 + num_traits:]]
            traits = [float(x) for x in row[2:2+num_traits]]

            groups[group].append(SchedulingIndividual(name, availability, traits=traits))

    # Each trait may be a different distribution. Store a normalized version of each trait.
    averages, stdevs = [], []
    individuals = [individual for individual in groups[group] for group in groups]
    for trait in range(num_traits):
        trait_values = [individual.traits[trait] for individual in individuals]
        averages.append(np.mean(trait_values))
        stdevs.append(np.std(trait_values))
    
    for individual in individuals:
        individual.normalize_traits(averages, stdevs)

    # There are two possible situations:
    # - The group is empty
    # - The group is supplied
    for group_name, members in groups.items():

        if group_name:
            group = SchedulingGroup(name=group_name, members=members)
            groups_from_file.append(group)
        else:
            individuals_from_file.extend(members)

    return individuals_from_file, groups_from_file