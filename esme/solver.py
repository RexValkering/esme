import random
from collections import Counter
import csv
import itertools
import yaml

from tabulate import tabulate
import numpy as np
from deap import creator, base, tools, algorithms

from .common import sorted_teams_from_solution
from .algorithms import evaluate_permutation, mutate_permutation, generate_permutation
from .entities import SchedulingGroup, SchedulingIndividual
from .parsers import InputFileParser
from .profiles import parse_profile


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
    timeslots = None

    solution = None
    solution_generated_groups = None
    solution_groups = None
    solution_schedule = None
    solution_iterator = None
    profile = None

    current_step = None

    def __init__(self, args):
        if not args:
            return

        self.load_scheduling_parameters(args)
        self.solution_iterator = parse_profile(self.profile)
        self.parse_timeslots()

        # Files
        self.input_files = args.input
        self.output_prefix = args.output
        self.groups_save_file = args.savefile

        self.assignable_groups = list()
        self.assignable_individuals = list()
        self.verbose = True

        # Either load groups from file or generate them from parameters
        if self.input_files:
            for input_file in self.input_files:
                self.parse_input_file(input_file)
        else:
            self.generate_groups()

        # Calculate the number of groups we will end up with
        self.total_groups = len(self.assignable_groups)
        for group in self.assignable_individuals:
            number_of_groups = self.get_number_of_groups_by_number_of_individuals(len(group))
            self.total_groups += number_of_groups

        total_options_available = self.num_boats * sum(self.timeslots)
        total_to_assign = self.total_groups * self.courses_per_team

        if self.verbose:
            self._report_initialization()

        if total_to_assign > total_options_available:
            print("The number of slots to assign exceeds the number of options available.")
            print("Please calibrate your parameters and try again.")
            exit()

    def run(self, report=True, plot=True):
        self.solve()
        if self.output_prefix:
            self.save_results_to_file()
        if report:
            self.report()
        if plot:
            self.plot_progress()

    def parse_input_file(self, input_file):
        """Parse an input file. Should know the difference between input and solution files.

        Args:
            input_file: file to read
        """
        parser = InputFileParser(input_file, self.num_traits)
        individuals_from_file, groups_from_file = parser.parse()
        self.assignable_individuals.append(individuals_from_file)
        self.assignable_groups.extend(groups_from_file)

        if self.verbose:
            if individuals_from_file:
                print("Loaded {} individuals".format(len(individuals_from_file)))
            if groups_from_file:
                print("Loaded {} groups".format(len(groups_from_file)))

    def parse_timeslots(self):
        if self.timeslots:
            return
        self.timeslots = [self.num_timeslots] * self.num_days

    def load_scheduling_parameters(self, args):
        """Load scheduling parameters from command line, config file and defaults.

        Args:
            list of command line arguments
        """

        # Default parameter values
        parameters = {
            'generate': 'groups',
            'num_to_generate': 6,
            'num_traits': 0,
            'trait_weights': [],
            'min_members_per_group': 6,
            'max_members_per_group': 7,
            'availability_likelihood': 0.78,
            'num_boats': 1,
            'num_timeslots': 3,
            'num_days': 2,
            'courses_per_team': 1,
            'seats_per_boat': 4,
            'min_available': 5,
            'population': 400,
            'profile': 'default 400',
            'timeslots': None
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

    def generate_individual(self, offset=0):
        """Generate a single individual.

        Args:
            offset: identifier of the individual

        Returns:
            SchedulingIndividual
        """
        individual = SchedulingIndividual('Individual {}'.format(offset))
        individual.randomize_preferences(sum(self.timeslots), self.availability_likelihood)
        return individual

    def generate_group(self, group_size, group_offset, individual_offset):
        """Generate a single group of random individuals.

        Args:
            group_size: number of individuals to generate

        Returns:
            SchedulingGroup
        """
        individuals = [self.generate_individual(i) for i in range(individual_offset,
                                                                  individual_offset + group_size)]
        group = SchedulingGroup('Group {}'.format(group_offset), individuals,
                                num_options=sum(self.timeslots))
        return group

    def save_generated_to_file(self, filename):
        """Save the generated groups and individuals to an availability CSV.

        Args:
            filename: path to CSV file to save to.
        """
        with open(filename, 'w') as outfile:
            writer = csv.writer(outfile)
            writer.writerow(['Name', 'Group'] + self.list_of_timeslots())

            # Write groups
            for i, group in enumerate(self.assignable_groups):
                for individual in group.members:
                    writer.writerow([individual.name, i] + individual.preferences)

            # Write individuals
            for individual in self.assignable_individuals[0]:
                writer.writerow([individual.name, ''] + individual.preferences)

    def generate_groups(self):
        """Generate the groups based on the program parameters"""

        if self.generate == 'groups':
            # Generate groups of random group sizes
            group_sizes = list(range(self.min_members_per_group, self.max_members_per_group + 1))
            offset = 0

            for j in range(self.num_to_generate):
                group_size = random.choice(group_sizes)
                self.assignable_groups.append(self.generate_group(group_size, j, offset))
                offset += group_size

        if self.generate == 'individuals':
            # Generate individuals
            individuals = [self.generate_individual(i) for i in range(self.num_to_generate)]
            self.assignable_individuals.append(individuals)

        # Save to file
        if self.groups_save_file:
            self.save_generated_to_file(self.groups_save_file)

    def generate_schedule_from_solution(self, solution, all_groups):
        """Given a solution, create a [day -> slot -> groups] schedule.

        Args:
            solution: the solution to create the schedule for
        """
        days = {}
        for day, timeslots in enumerate(self.timeslots):
            days[day] = {}
            for slot in range(timeslots):
                days[day][slot] = []

        for i in range(self.courses_per_team * self.total_groups):
            assigned_option = solution[-1][i]
            assigned_entity = all_groups[i // self.courses_per_team]
            assigned_day, assigned_timeslot = self.timeslot_offset_to_pair(assigned_option)

            days[assigned_day][assigned_timeslot].append(assigned_entity)

        return days

    def get_number_of_groups_by_number_of_individuals(self, num_individuals):
        """Returns the target number of groups.

        Args:
            num_individuals: the number of people to generate groups for
        """
        average_group_size = (self.min_members_per_group + self.max_members_per_group) / 2.0

        return int(num_individuals / average_group_size)

    def list_of_timeslots(self):
        """Returns a list of strings for each day and timeslot."""
        return ['Day {} Slot {}'.format(day, slot)
                for day, timeslots in enumerate(self.timeslots)
                for slot in range(timeslots)]

    def timeslot_offset_to_pair(self, offset):
        """Returns the day and slot given a timeslot offset.

        For example, offset 7 may resolve to (0-indexed) day 1, timeslot 3 if all days have 4 slots.

        Args:
            offset: solution offset of timeslot
        """
        for day, timeslots in enumerate(self.timeslots):
            offset -= timeslots
            if offset < 0:
                break
        return day, offset + timeslots

    def maximum_score(self, split=False):
        """Get the maximum possible score.

        Returns:
            int: maximum possible score for solutions
        """
        num_generated_groups = sum(
            self.get_number_of_groups_by_number_of_individuals(len(individuals))
            for individuals in self.assignable_individuals
        ) if self.assignable_individuals else 0

        assignment_score = num_generated_groups
        solution_score = self.courses_per_team * (num_generated_groups + len(self.assignable_groups))
        if split:
            return assignment_score, solution_score
        else:
            return assignment_score + solution_score

    def setup_deap(self):
        """Initialize the deap module."""

        creator.create("FitnessMax", base.Fitness, weights=(1.0,))

        # An individual is a permutation of numbers
        creator.create("Individual", list, fitness=creator.FitnessMax)
        toolbox = base.Toolbox()

        toolbox.register("permutation", generate_permutation, solver=self)
        toolbox.register("individual", tools.initIterate,
                         creator.Individual, toolbox.permutation)
        toolbox.register("population", tools.initRepeat, list, toolbox.individual)

        # Register evaluation function
        toolbox.register("evaluate", evaluate_permutation, solver=self)

        # Reproduction and mutation
        toolbox.register("mate", lambda a, b: (a, b))
        toolbox.register("mutate", mutate_permutation, solver=self)

        # Selection method
        toolbox.register("select", tools.selTournament, tournsize=3)
        return toolbox


    def solve(self):
        """Setup the deap module and find the best permutation."""

        maximum_score = self.maximum_score()

        if maximum_score <= 0.0:
            print("Nothing to solve, aborting.")
            exit()

        toolbox = self.setup_deap()

        # Create population
        population = toolbox.population(n=self.population)

        # Perform evoluationary algorithm
        result = None
        self.solution_iterator.initialize_progressbar()

        maximum_fit = -10*6
        maximum_score_object = None

        for step in self.solution_iterator:
            self.current_step = step
            self.solution_iterator.update_progressbar(100 * maximum_fit / maximum_score)
            offspring = algorithms.varAnd(population, toolbox, cxpb=0.5, mutpb=0.1)

            fits = toolbox.map(toolbox.evaluate, offspring)
            for fit, ind in zip(fits, offspring):
                score = fit[0].score()
                # Update maximum fit
                if score > maximum_fit:
                    maximum_fit = score
                    maximum_score_object = fit[0]

                if int(score) == maximum_score:
                    result = ind
                    break
                ind.fitness.values = score, 

            population = toolbox.select(offspring, k=len(population))
            if maximum_score_object:
                self.solution_iterator.register_fitness(maximum_score_object)

            if result:
                break
        else:
            result = tools.selBest(population, k=1)[0]

        self.solution_iterator.update_progressbar(100 * maximum_fit / maximum_score, final=True)

        self.solution = result

        self.solution_generated_groups = sorted_teams_from_solution(self.solution,
                                                                    self.assignable_individuals)
        self.solution_groups = self.assignable_groups + self.solution_generated_groups
        self.solution_schedule = self.generate_schedule_from_solution(self.solution,
                                                                      self.solution_groups)

        return result

    def plot_progress(self):
        self.solution_iterator.plot(self.maximum_score(split=True))

    def save_results_to_file(self):
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
            for group in self.solution_groups:
                for member in group.members:
                    writer.writerow([member.name, group.name] + member.traits +
                                    member.availability())


        schedule_file = "{}_schedule.csv".format(self.output_prefix)
        with open(schedule_file, 'w') as outfile:
            writer = csv.writer(outfile)
            writer.writerow(['Day'] + list(range(1, max(self.timeslots) + 1)))
            for day, timeslots in enumerate(self.timeslots):
                slots = self.solution_schedule[day]
                writer.writerow([day + 1] + [', '.join([str(x) for x in slots[slot]])
                                             for slot in range(timeslots)])

    def _report_initialization(self):
        total_options_available = self.num_boats * sum(self.timeslots)
        total_individuals_to_assign = sum([len(group) for group in self.assignable_individuals])
        total_to_assign = self.total_groups * self.courses_per_team

        # Print info about current ratio.
        print("Total options available: {} ({} timeslots x {} boats)".format(
            total_options_available, sum(self.timeslots), self.num_boats
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
        print("Ratio: {}/{} ({})".format(total_to_assign, total_options_available,
                                         float(total_to_assign) / total_options_available))
        print("")

    def _print_table(self, table):
        """Output a single table.

        Args:
            table: dict with keys 'data' and 'headers'
        """
        data = table['data']
        rows = [
            [data[k][j] if len(data[k]) > j else '' for k in range(len(data))]
            for j in range(max([len(data[k]) for k in range(len(data))]))
        ]
        print(tabulate(rows, headers=table['headers']))
        print("")

    def _groups_to_tables(self):
        tables = []
        groups_per_row = 3

        for i, group in enumerate(self.solution_groups):
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
        return tables

    def _report_assignment(self):
        """Print info about the clustering solution."""
        print("Generated groups:")
        print("")

        tables = self._groups_to_tables()
        for table in tables:
            self._print_table(table)

        print("")

    def _report_scheduling(self):
        """Print info about the scheduling solution."""
        print("Number of teams: {}".format(self.total_groups))
        print("Available boats per option: {}".format(self.num_boats))
        print("Available options: {}".format(sum(self.timeslots)))
        score = evaluate_permutation(self.solution, self)[0]
        assignment_max, scheduling_max = self.maximum_score(True)
        score.report([assignment_max, scheduling_max])
        print("")

        slot_offset = 0
        for day, timeslots in enumerate(self.timeslots):
            print("Day {}:".format(day + 1))
            for slot in range(timeslots):
                print("\tTimeslot {}: {}".format(slot + 1, ", ".join(
                    [str(x) for x in self.solution_schedule[day][slot]])))
                for x in self.solution_schedule[day][slot]:
                    print("\t\t{} ({}/{})".format(
                        x, x.availability(slot_offset), x.num_members))
                slot_offset += 1
            print("")

    def report(self):

        # Select best and report on results
        if self.assignable_individuals:
            self._report_assignment()

        self._report_scheduling()
