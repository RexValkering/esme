import random
from deap import creator, base, tools, algorithms
from collections import Counter, defaultdict
import pickle
import os
import csv
import itertools
import yaml


class SchedulingSolver():

    num_groups = None
    members_per_group = None
    availability_likelihood = None
    num_boats = None
    num_timeslots = None
    num_days = None
    courses_per_team = None
    seats_per_boat = None
    min_available = None
    generations = None
    population = None
    indpb = None

    def __init__(self, args):
        if not args:
            return

        # Default parameter values
        parameters = {
            'num_groups': 24,
            'members_per_group': 7,
            'availability_likelihood': 0.78,
            'num_boats': 1,
            'num_timeslots': 3,
            'num_days': 2,
            'courses_per_team': 1,
            'seats_per_boat': 4,
            'min_available': 5,
            'generations': 400,
            'population': 400,
            'indpb': 0.05
        }

        # Parse config file. These override default values.
        if args.config:
            with open(args.config) as infile:
                config = yaml.safe_load(infile)
            for key, value in config.items():
                if key not in parameters:
                    print("Unknown config parameter: {}".format(key))
                    exit()
                parameters[key] = value

        # Parse passed parameters. These override default and config values.
        for key, value in vars(args).items():
            if key in parameters and value is not None:
                parameters[key] = value

        # Set passed parameters
        for key, value in parameters.items():
            setattr(self, key, value)

        # Files
        self.input_file = args.input
        self.output_file = args.output
        self.groups_save_file = args.savefile

        self.solve_mode = 'groups'
        self.assignable = []

        self.num_options = self.num_timeslots * self.num_days
        self.verbose = args.verbose

        # Either load groups from file or generate them from parameters
        if self.input_file:
            self.parse_input_file()
        else:
            self.generate_groups()

        total_options_available = self.num_boats * self.num_options
        if self.solve_mode == 'individuals':
            total_options_available *= self.seats_per_boat

        total_to_assign = self.num_groups * self.courses_per_team
        if self.solve_mode == 'individuals':
            total_to_assign = len(self.assignable) * self.courses_per_team

        if self.verbose:
            # Print info about current ratio.
            print("Total options available: {} ({} days x {} timeslots x {} boats)".format(
                total_options_available, self.num_days, self.num_timeslots, self.num_boats
            ))
            print("Total to assign: {} ({} groups x {} courses)".format(total_to_assign,
                self.num_groups, self.courses_per_team))
            print("Ratio: {}/{} ({})".format(total_to_assign, total_options_available,
                float(total_to_assign) / total_options_available))
            print("")

        if total_to_assign > total_options_available:
            print("The number of slots to assign exceeds the number of options available.")
            print("Please calibrate your parameters and try again.")
            exit()

    def parse_input_file(self):
        """Load the groups from a csv file."""

        if not os.path.isfile(self.input_file):
            print("File does not exist: {}".format(self.input_file))
            exit()

        if not self.input_file.endswith('.csv'):
            print("File is not a .csv: {}".format(self.input_file))
            exit()

        groups = defaultdict(list)
        with open(self.input_file) as infile:
            reader = csv.reader(infile)

            # Skip header
            next(reader)

            # Read all individuals from file
            for row in reader:
                name = row[0]
                group = row[1]
                availability = [bool(int(x)) for x in row[2:]]

                groups[group].append(SchedulingIndividual(name, availability))

        # There are two possible situations:
        # - The group is empty
        # - The group is supplied
        if len(groups) == 1 and list(groups.keys())[0] == '':
            self.solve_mode = 'individuals'
            for member in groups['']:
                self.assignable.append(member)

            if self.verbose:
                print("Loaded {} individuals".format(len(self.assignable)))

        else:
            self.solve_mode = 'groups'
            for group_name, members in groups.items():
                if not group_name:
                    print('Mixture of individuals with and without group is not yet supported')
                    exit()

                group = SchedulingGroup(members=members)
                self.assignable.append(group)

            if self.verbose:
                print("Loaded {} groups".format(len(self.assignable)))


    def generate_groups(self):
        """Generate the groups based on the program parameters"""
        offset = 0
        for _ in range(self.num_groups):

            # Create a standard group
            individuals = [SchedulingIndividual('Individual {}'.format(i))
                           for i in range(offset, offset + self.members_per_group)]
            group = SchedulingGroup(individuals, num_options=self.num_options)

            # Randomize the availability of a groups members
            group.randomize_preferences(self.availability_likelihood)

            self.assignable.append(group)
            offset += self.members_per_group

        if self.verbose:
            print("Generated {} groups", self.num_groups)

        # Save to file
        if self.groups_save_file:
            with open(self.groups_save_file, 'w') as outfile:
                writer = csv.writer(outfile)
                writer.writerow(['Name', 'Group'] +
                                ['Day {} Slot {}'.format(day, slot) for day, slot in
                                 itertools.product(range(self.num_days),
                                                   range(self.num_timeslots))
                                ])
                for i, group in enumerate(self.assignable):
                    for individual in group.members:
                        writer.writerow([individual.name, i] + individual.preferences)


    def solve(self):
        """Setup the deap module and find the best permutation."""
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))

        # An individual is a permutation of numbers
        creator.create("Individual", list, fitness=creator.FitnessMax)

        toolbox = base.Toolbox()

        def generate_permutation():
            """Generate a fully random starting permutation"""
            options = []
            for o in range(self.num_options):
                if self.solve_mode == 'groups':
                    options.extend([o] * self.num_boats)
                elif self.solve_mode == 'individuals':
                    options.extend([o] * (self.num_boats * self.seats_per_boat))
            random.shuffle(options)
            return options

        toolbox.register("permutation", generate_permutation)
        toolbox.register("individual", tools.initIterate, creator.Individual, toolbox.permutation)
        toolbox.register("population", tools.initRepeat, list, toolbox.individual)

        # Register evaluation function
        toolbox.register("evaluate", evaluate_permutation,
                         assignable=self.assignable,
                         num_courses=self.courses_per_team,
                         num_timeslots=self.num_timeslots,
                         min_available=self.min_available)

        # Reproduction and mutation
        #toolbox.register("mate", tools.cxOrdered, indpb=0.05)
        toolbox.register("mate", lambda a, b: (a, b))
        toolbox.register("mutate", tools.mutShuffleIndexes, indpb=self.indpb)

        # Selection method
        toolbox.register("select", tools.selTournament, tournsize=3)

        # Create population
        population = toolbox.population(n=self.population)
        maximum_score = self.courses_per_team * len(self.assignable)

        # Perform evoluationary algorithm
        result = None
        for gen in range(self.generations):
            offspring = algorithms.varAnd(population, toolbox, cxpb=0.5, mutpb=0.1)
            fits = toolbox.map(toolbox.evaluate, offspring)
            for fit, ind in zip(fits, offspring):
                if int(fit[0]) == maximum_score:
                    result = ind
                    break
                ind.fitness.values = fit
            population = toolbox.select(offspring, k=len(population))

            if result:
                break
        else:
            result = tools.selBest(population, k=1)[0]

        # Select best and report on results
        if self.verbose:
            print("Best result:")
            print(result)

        days = {}
        for day in range(self.num_days):
            days[day] = {}
            for slot in range(self.num_timeslots):
                days[day][slot] = []

        for i in range(self.courses_per_team * self.num_groups):
            assigned_option = result[i]
            assigned_group = i // self.courses_per_team
            assigned_day = assigned_option // self.num_timeslots
            assigned_timeslot = assigned_option % self.num_timeslots
            #print assigned_day, assigned_timeslot, assigned_group

            days[assigned_day][assigned_timeslot].append(assigned_group)

        if self.verbose:
            print("Aantal ploegen: {}".format(self.num_groups))
            print("Aantal boten: {}".format(self.num_boats))
            print("Aantal unieke tijdstippen: {}".format(self.num_options))
            print("Oplossingsscore: {}".format(evaluate_permutation(result, self.assignable, self.courses_per_team, self.num_timeslots, self.min_available)[0]))
            print("Maximale score: {}".format(maximum_score))
            print("")

            for day in range(self.num_days):
                print("Dag {}:".format(day + 1))
                for slot in range(self.num_timeslots):
                    print("\tTijdstip {}: {}".format(slot + 1, ", ".join([str(x) for x in days[day][slot]])))
                    for x in days[day][slot]:
                        print("\t\t{} {}".format(x, self.assignable[x].preferences[day * self.num_timeslots + slot]))
                print("")


def evaluate_permutation(individual, assignable, num_courses, num_timeslots, min_available):
    """Evaluate a potential solution."""
    total = 0.0

    if isinstance(assignable[0], SchedulingIndividual):
        min_available = 1

    for i in range(num_courses * len(assignable)):
        option = individual[i]
        group = assignable[i // num_courses]

        # Ensure enough members are available.
        if group.availability(option) >= min_available:
            total += float(group.preferences[option]) / group.num_members

    # Give penalties for one group being twice assigned to the same day.
    for g in range(len(assignable)):
        assignments = [individual[g * num_courses + i] // num_timeslots for i in range(num_courses)]

        count = Counter(assignments)
        if count.most_common(1)[0][1] > 1:
            total -= 8.0

    return total,


class SchedulingIndividual():
    """Represents an individual, either as part of a group or individually.

    Args:
        name: identifier of individual
        preferences: """

    num_members = 1

    def __init__(self, name, preferences=None, group=None):
        self.name = name
        self.preferences = preferences
        self.group = group

    def randomize_preferences(self, num_options, likelihood):
        """Randomize whether an individual is available at an option or not.

        Args:
            num_options: number of options to evaluate
            likelihood: likelihood of individual being available
        """
        self.preferences = [random.random() < likelihood for _ in range(num_options)]

    def availability(self, option=None):
        if option is not None:
            return int(self.preferences[option])
        return self.preferences

    def __repr__(self):
        return repr(self.availability())


class SchedulingGroup():
    """Represents a group of members with varying availability."""

    def __init__(self, members, num_options=None):
        
        self.members = members
        for member in members:
            member.group = self

        if num_options:
            self.num_options = num_options
        elif members[0].preferences:
            self.num_options = len(members[0].preferences)
        else:
            print('Cannot infer number of options (SchedulingGroup)')
            exit()

    def randomize_preferences(self, likelihood):
        for member in self.members:
            member.randomize_preferences(self.num_options, likelihood)

    def availability(self, option=None):
        """Return availability at a certain option, or all options if no option is supplied."""
        if option is not None:
            return sum([member.preferences[option] for member in self.members])
        return [sum([member.preferences[option] for member in self.members])
                for option in range(self.num_options)]

    def __repr__(self):
        return repr(self.availability())


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', help='input csv file')
    parser.add_argument('-o', '--output', help='output csv file')
    parser.add_argument('-s', '--savefile', help='save randomly generated groups')
    parser.add_argument('-c', '--config', help='config .yaml file')

    parser.add_argument('-m', '--members_per_group', help='number of members per group', type=int)
    parser.add_argument('-g', '--num_groups', help='number of groups to generate', type=int)
    parser.add_argument('-b', '--num_boats', help='number of boats per timeslot', type=int)
    parser.add_argument('-t', '--num_timeslots', help='number of timeslots per day', type=int)
    parser.add_argument('-d', '--num_days', help='number of days to schedule', type=int)
    parser.add_argument('-n', '--courses_per_team', help='number of courses to schedule per group per week', type=int)
    parser.add_argument('-a', '--min_available', help='minimum number of members available per match', type=int)
    parser.add_argument('-l', '--availability_likelihood', help='likelihood of a member being available for an option', type=float)
    parser.add_argument('-x', '--generations', help='number of generations to test', type=int)
    parser.add_argument('-y', '--population', help='population size per generation', type=int)
    parser.add_argument('-z', '--indpb', help='evolution algorithm parameter', type=float)
    parser.add_argument('-v', '--verbose', help='enable verbosity', action="store_true")
    args = parser.parse_args()

    solver = SchedulingSolver(args)
    solver.solve()


if __name__ == '__main__':
    main()