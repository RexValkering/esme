import random
from itertools import count
import numpy as np


class SchedulingIndividual(object):
    """Represents an individual, either as part of a group or individually.

    Args:
        name: identifier of individual
        preferences: list of booleans which represent the availability per timeslot
        traits: list of quantitative traits, such as length, which are used for making groups
    """

    _ids = count(0)

    num_members = 1

    def __init__(self, name, preferences=None, traits=None):
        self.id = next(self._ids)
        self.name = name
        self.preferences = preferences
        self.traits = traits if traits is not None else []
        self.normalized_traits = []

    def normalize_traits(self, averages, stdevs):
        """Store a version of each trait normalized to its distribution.

        Args:
            averages: list of averages
            stdevs: list of standard deviations
        """
        for i, (average, stdev) in enumerate(zip(averages, stdevs)):
            self.normalized_traits.append((self.traits[i] - average) / stdev)

    def randomize_preferences(self, num_options, likelihood):
        """Randomize whether an individual is available at an option or not.

        Args:
            num_options: number of options to evaluate
            likelihood: likelihood of individual being available
        """
        self.preferences = [int(random.random() < likelihood) for _ in range(num_options)]

    def availability(self, option=None):
        """Return availability at a certain option, or all options if no option is supplied.
        
        Args:
            option: option to get availability for. If none is given, it returns all availability
        """

        if option is not None:
            return int(self.preferences[option])
        return self.preferences

    def __repr__(self):
        return self.name


class SchedulingGroup(object):
    """Represents a group of members with varying availability.

    Args:
        name: name or identifier of group
        members: list of members to add to group
        num_options: the number of timeslots available
    """

    _ids = count(0)

    def __init__(self, name, members, num_options=None):
        self.id = next(self._ids)
        self.name = name
        self.members = members
        self.averages = {}
        for member in members:
            member.group = self

        # If num_options is not supplied, infer from preferences.
        if num_options:
            self.num_options = num_options
        elif members[0].preferences:
            self.num_options = len(members[0].preferences)
        else:
            print('Cannot infer number of options (SchedulingGroup)')
            exit()

        self.num_members = len(self.members)

    def trait_average(self, trait):
        """Calculate the average value of a trait in a group."""
        if trait not in self.averages:
            self.averages[trait] = np.mean([member.normalized_traits[trait]
                                            for member in self.members])
        return self.averages[trait]

    def trait_cumulative_penalty(self, trait, margin=0.0, normalize=False):
        """Calculate the cumulative penalty of a trait in a group.

        Args:
            trait: index of trait to consider
            margin: margin of error from mean for which no penalty will be applied
            normalize: whether to divide the sum by the number of members
        """
        if not self.members:
            return 0.0

        values = [member.normalized_traits[trait] for member in self.members]
        average = np.mean(values)
        return (sum([max(0, abs(value - average) - margin) for value in values])
                / (len(self.members) if normalize else 1.0))

    def randomize_preferences(self, likelihood):
        """Randomize the availability of all members

        Args:
        1    likelihood: likelihood of a member being available
        """
        for member in self.members:
            member.randomize_preferences(self.num_options, likelihood)

    def availability(self, option=None):
        """Return availability at a certain option, or all options if no option is supplied."""
        if option is not None:
            return sum([member.preferences[option] for member in self.members])
        return [sum([member.preferences[option] for member in self.members])
                for option in range(self.num_options)]

    def __repr__(self):
        return self.name
