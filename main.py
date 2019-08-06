import numpy as np
import random
from deap import creator, base, tools, algorithms
from collections import Counter, defaultdict
import os
import csv
import itertools
import yaml
import progressbar
from tabulate import tabulate

from common import generate_teams_from_solution, evaluate_permutation, parse_args, \
    mutate_permutation
from entities import SchedulingGroup, SchedulingIndividual
from parsers import parse_individuals_file


class SchedulingSolver():
    """ Main class for the scheduling problem solver."""
    generate = None

    num_traits = None
    trait_weights = None
    num_to_generate = None
    min_members_per_group = None
    max_members_per_group = None
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

        self.load_scheduling_parameters(args)

        # Files
        self.input_files = args.input
        self.output_prefix = args.output
        self.groups_save_file = args.savefile

        self.assignable_groups = list()
        self.assignable_individuals = list()

        self.num_options = self.num_timeslots * self.num_days
        self.verbose = True

        # Either load groups from file or generate them from parameters
        if self.input_files:
            for input_file in self.input_files:
                self.parse_input_file(input_file)
            print(self.assignable_individuals)
        else:
            self.generate_groups()

        # Calculate the number of groups we will end up with
        self.total_groups = len(self.assignable_groups)
        for group in self.assignable_individuals:
            number_of_groups = self.get_number_of_groups_by_number_of_individuals(len(group))
            self.total_groups += number_of_groups

        total_options_available = self.num_boats * self.num_options
        total_individuals_to_assign = sum([len(group) for group in self.assignable_individuals])
        total_to_assign = self.total_groups * self.courses_per_team

        if self.verbose:
            # Print info about current ratio.
            print("Total options available: {} ({} days x {} timeslots x {} boats)".format(
                total_options_available, self.num_days, self.num_timeslots, self.num_boats
            ))
            if self.assignable_individuals:
                print("")
                print("CLUSTERING")
                print("----------")
                print("Number of individuals to assign to groups: {}".format(
                    total_individuals_to_assign))
                print("Number of groups to form: {}".format(
                    self.total_groups - len(self.assignable_groups)))
            print("")
            print("SCHEDULING")
            print("----------")
            print("Total number of groups: {}".format(self.total_groups))
            print("Number of slots to assign: {} ({} groups x {} courses)".format(
                total_to_assign, self.total_groups, self.courses_per_team))
            print("Ratio: {}/{} ({})".format(
                total_to_assign, total_options_available,
                float(total_to_assign) / total_options_available))
            print("")

        if total_to_assign > total_options_available:
            print("The number of slots to assign exceeds the number of options available.")
            print("Please calibrate your parameters and try again.")
            exit()

    def parse_input_file(self, input_file):
        """Parse an input file. Should know the difference between input and solution files.

        Args:
            input_file: file to read
        """
        individuals_from_file, groups_from_file = parse_individuals_file(
            input_file, self.num_traits)
        self.assignable_individuals.append(individuals_from_file)
        self.assignable_groups.extend(groups_from_file)

        if self.verbose:
            if individuals_from_file:
                print("Loaded {} individuals".format(len(individuals_from_file)))
            if groups_from_file:
                print("Loaded {} groups".format(len(groups_from_file)))

    def load_scheduling_parameters(self, args):
        """Load scheduling parameters from command line, config file and defaults.

        Args:
            list of command line arguments
        """

        # Default parameter values
        parameters = {
            'generate': 'groups',
            'num_to_generate': 24,
            'num_traits': 0,
            'trait_weights': [],
            'min_members_per_group': 5,
            'max_members_per_group': 8,
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

    def generate_groups(self):
        """Generate the groups based on the program parameters"""
        offset = 0

        group_sizes = list(range(self.min_members_per_group, self.max_members_per_group + 1))

        if self.generate == 'groups':
            for j in range(self.num_to_generate):

                group_size = random.choice(group_sizes)

                # Create a standard group
                individuals = [SchedulingIndividual('Individual {}'.format(i))
                               for i in range(offset, offset + group_size)]
                group = SchedulingGroup('Group {}'.format(j), individuals,
                                        num_options=self.num_options)

                # Randomize the availability of a groups members
                group.randomize_preferences(self.availability_likelihood)

                self.assignable_groups.append(group)
                offset += group_size

            if self.verbose:
                print("Generated {} groups".format(self.num_to_generate))

        if self.generate == 'individuals':
            individuals = [SchedulingIndividual('Individual {}'.format(i))
                           for i in range(self.num_to_generate)]

            for individual in individuals:
                individual.randomize_preferences(self.num_options, self.availability_likelihood)

            self.assignable_individuals.append(individuals)

        # Save to file
        if self.groups_save_file:
            with open(self.groups_save_file, 'w') as outfile:
                writer = csv.writer(outfile)
                writer.writerow(['Name', 'Group'] + self.list_of_timeslots())
                # Write groups
                for i, group in enumerate(self.assignable_groups):
                    for individual in group.members:
                        writer.writerow([individual.name, i] + individual.preferences)

                # Write individuals
                for individual in self.assignable_individuals[0]:
                    writer.writerow([individual.name, ''] + individual.preferences)

    def generate_schedule_from_solution(self, scheduling_solution, all_groups):
        """Given a solution, create a [day -> slot -> groups] schedule.

        Args:
            solution: the solution to create the schedule for
        """
        days = {}
        for day in range(self.num_days):
            days[day] = {}
            for slot in range(self.num_timeslots):
                days[day][slot] = []

        for i in range(self.courses_per_team * self.total_groups):
            assigned_option = scheduling_solution[i]
            assigned_entity = all_groups[i // self.courses_per_team]
            assigned_day = assigned_option // self.num_timeslots
            assigned_timeslot = assigned_option % self.num_timeslots

            days[assigned_day][assigned_timeslot].append(assigned_entity)

        return days

    def get_number_of_groups_by_number_of_individuals(self, num_individuals):
        """Returns the target number of groups.

        Args:
            num_individuals: the number of people to generate groups for
        """
        average_group_size = (self.min_members_per_group + self.max_members_per_group) / 2.0
        return int(num_individuals / average_group_size + 0.5)

    def list_of_timeslots(self):
        """Returns a list of strings for each day and timeslot."""
        return ['Day {} Slot {}'.format(day, slot) for day, slot in
                itertools.product(range(self.num_days), range(self.num_timeslots))]

    def maximum_score(self):
        """Get the maximum possible score."""
        num_generated_groups = sum(
            self.get_number_of_groups_by_number_of_individuals(len(individuals))
            for individuals in self.assignable_individuals
        ) if self.assignable_individuals else 0

        return num_generated_groups + self.courses_per_team * (num_generated_groups +
                                                               len(self.assignable_groups))

    def solve(self):
        """Setup the deap module and find the best permutation."""

        maximum_score = self.maximum_score()

        if maximum_score <= 0.0:
            print("Nothing to solve, aborting.")
            exit()

        creator.create("FitnessMax", base.Fitness, weights=(1.0,))

        # An individual is a permutation of numbers
        creator.create("Individual", list, fitness=creator.FitnessMax)
        toolbox = base.Toolbox()


        def generate_permutation():
            """Generate a fully random starting permutation"""
            permutation = []

            # Create lists of individual-to-group assignments.
            groups_offset = len(self.assignable_groups)
            for i, individuals_group in enumerate(self.assignable_individuals):
                num_groups = self.get_number_of_groups_by_number_of_individuals(len(individuals_group))
                options = []
                for j in range(groups_offset, num_groups + groups_offset):
                    options.extend([j] * self.max_members_per_group)
                groups_offset += num_groups
                random.shuffle(options)
                permutation.append(options)

            # Create a final list of group schedules.
            options = []
            for o in range(self.num_options):
                options.extend([o] * self.num_boats)
            random.shuffle(options)
            permutation.append(options)

            return permutation

        toolbox.register("permutation", generate_permutation)
        toolbox.register("individual", tools.initIterate,
                         creator.Individual, toolbox.permutation)
        toolbox.register("population", tools.initRepeat, list, toolbox.individual)

        # Register evaluation function
        toolbox.register("evaluate", evaluate_permutation, solver=self)

        # Reproduction and mutation
        #toolbox.register("mate", tools.cxOrdered, indpb=0.05)
        toolbox.register("mate", lambda a, b: (a, b))
        toolbox.register("mutate", mutate_permutation, indpb=self.indpb)

        # Selection method
        toolbox.register("select", tools.selTournament, tournsize=3)

        # Create population
        population = toolbox.population(n=self.population)

        # Perform evoluationary algorithm
        result = None
        score_widget = progressbar.DynamicMessage('score', width=4)
        widgets = [
            progressbar.Percentage(), ' (', progressbar.SimpleProgress(), ') ',
            progressbar.Bar(),
            ' [', score_widget, '] ', progressbar.Timer()
        ]

        with progressbar.ProgressBar(max_value=self.generations, widgets=widgets) as bar:
            maximum_fit = 0.0

            for gen in range(self.generations):
                bar.update(gen, score=100 * maximum_fit / maximum_score)
                offspring = algorithms.varAnd(population, toolbox, cxpb=0.5, mutpb=0.1)

                fits = toolbox.map(toolbox.evaluate, offspring)
                for fit, ind in zip(fits, offspring):
                    maximum_fit = max(maximum_fit, fit[0])
                    if int(fit[0]) == maximum_score:
                        result = ind
                        break
                    ind.fitness.values = fit

                population = toolbox.select(offspring, k=len(population))

                if result:
                    break
            else:
                result = tools.selBest(population, k=1)[0]

            bar.update(self.generations)
        return result

    def save_results_to_file(self, all_groups, schedule):
        """Save the solution schedule to file.

        Args:
            all_groups: list of SchedulingGroup instances
            schedule: day -> timeslot -> [groups] dictionary
        """
        groups_file = "{}_groups.csv".format(self.output_prefix)
        with open(groups_file, 'w') as outfile:
            writer = csv.writer(outfile)
            writer.writerow(['Name', 'Group'] +
                            ['Trait {}'.format(i+1) for i in range(self.num_traits)] +
                            self.list_of_timeslots())
            for group in all_groups:
                for member in group.members:
                    writer.writerow([member.name, group.name] + member.traits +
                                    member.availability())


        schedule_file = "{}_schedule.csv".format(self.output_prefix)
        with open(schedule_file, 'w') as outfile:
            writer = csv.writer(outfile)
            writer.writerow(['Day'] + list(range(1, self.num_timeslots + 1)))
            for day in range(self.num_days):
                slots = schedule[day]
                writer.writerow([day + 1] + [', '.join([str(x) for x in slots[slot]])
                                             for slot in range(self.num_timeslots)])

    def report(self, solution):

        generated_groups = sorted(
            generate_teams_from_solution(solution, self.assignable_individuals),
            key=lambda x: x.id
        )

        maximum_score = self.maximum_score()

        # Select best and report on results
        if self.verbose:
            print("Best result:")
            print(solution)
            print("")

            if (self.assignable_individuals):
                print("Generated groups:")
                print("")

                tables = []
                groups_per_row = 3

                for i, group in enumerate(generated_groups):
                    if i % groups_per_row == 0:
                        tables.append({'headers': [], 'data': []})

                    tables[-1]['headers'].append(group.name)
                    if self.num_traits:
                        tables[-1]['data'].append(["{} ({})".format(
                            member.name, ', '.join([str(x) for x in member.traits])
                        ) for member in group.members])
                    else:
                        tables[-1]['data'].append(["{}".format(member.name)
                                                   for member in group.members])

                for table in tables:
                    data = table['data']
                    rows = [
                        [data[k][j] if len(data[k]) > j else '' for k in range(len(data))]
                        for j in range(max([len(data[k]) for k in range(len(data))]))
                    ]
                    print(tabulate(rows, headers=table['headers']))
                    print("")
                print("")

        all_groups = self.assignable_groups + generated_groups

        # Retrieve the schedule
        schedule = self.generate_schedule_from_solution(solution[-1], all_groups)

        if self.output_prefix:
            self.save_results_to_file(all_groups, schedule)

        if self.verbose:    
            print("Number of teams: {}".format(self.total_groups))
            print("Available boats per option: {}".format(self.num_boats))
            print("Available options: {}".format(self.num_options))
            print("Solution score: {}".format(evaluate_permutation(solution, self)))
            print("Maximum score: {}".format(maximum_score))
            print("")

            for day in range(self.num_days):
                print("Day {}:".format(day + 1))
                for slot in range(self.num_timeslots):
                    print("\tTimeslot {}: {}".format(slot + 1, ", ".join(
                        [str(x) for x in schedule[day][slot]])))
                    for x in schedule[day][slot]:
                        print("\t\t{} ({}/{})".format(
                            x, x.availability(day * self.num_timeslots + slot), x.num_members))
                print("")


def main():
    
    args = parse_args()
    solver = SchedulingSolver(args)
    solution = solver.solve()
    solver.report(solution)


if __name__ == '__main__':
    main()