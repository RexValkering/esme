from collections import Counter, defaultdict
import random

from deap import tools

from .common import teams_from_solution, sorted_teams_from_solution, SolutionScore
from .iterator import SolverMethod


def evaluate_permutation(solution, solver):
    """Calculate the fitness score of a solution.

    Args:
        solution: the solution to calculate fitness score for
        solver: the SchedulingSolver instance
        split_score: whether to split the score (for debugging purposes)
    """

    # create score object
    clustering_weight, scheduling_weight = solver.current_step.parameters['weights']
    score = SolutionScore(clustering_weight, scheduling_weight)
    trait_weight_sum = sum(solver.trait_weights)

    # Create temporary SchedulingGroup objects for measurements.
    generated_groups = teams_from_solution(solution, solver.assignable_individuals)

    for group in generated_groups:

        # Score of 0 if group is too small.
        if len(group.members) < solver.min_members_per_group:
            continue

        score.assignment['score'] += 1.0

        # The penalty is the weighted sum of mean trait differences
        if clustering_weight and solver.num_traits:
            penalties = [solver.trait_weights[t] *
                         group.trait_cumulative_penalty(t, 0.0, normalize=True)
                         for t in range(solver.num_traits)]

            # Store penalties in SolutionScore object.
            for t, penalty in enumerate(penalties):
                trait_key = 'Trait {} differences'.format(t+1)
                score.assignment['penalty'][trait_key] += penalty / trait_weight_sum

    assignable = solver.assignable_groups + generated_groups

    # Evaluate schedules.
    if scheduling_weight:
        evaluate_schedule(solution, score, solver, assignable)
    return score,


def evaluate_schedule(solution, score, solver, assignable):
    for g in range(solver.courses_per_team * len(assignable)):
        option = solution[-1][g]
        group = assignable[g // solver.courses_per_team]

        # Ensure enough members are available.
        if group.availability(option) >= solver.min_available:
            score.scheduling['score'] += float(group.availability(option)) / group.num_members
        else:
            score.scheduling['penalty']['Not enough members'] += 1.0

    # Give penalties for one group being twice assigned to the same day.
    for g in range(len(assignable)):
        assignments = [solver.timeslot_offset_to_pair(solution[-1][g * solver.courses_per_team + i])[0]
                       for i in range(solver.courses_per_team)]

        count = Counter(assignments)
        if count.most_common(1)[0][1] > 1:
            score.scheduling['penalty']['Same day schedule'] += 2.0


def generate_permutation(solver):
    """Generate a fully random starting permutation

    Args:
        solver: SchedulingSolver object
    """
    permutation = []

    # Create lists of individual-to-group assignments.
    groups_offset = len(solver.assignable_groups)
    for _, individuals_group in enumerate(solver.assignable_individuals):

        # Get the number of groups
        num_groups = solver.get_number_of_groups_by_number_of_individuals(
            len(individuals_group))

        options = []
        if solver.num_traits:
            # Create groups sorted by the first trait
            average_group_size = len(individuals_group) / num_groups
            if False and solver.num_traits == 2:
                order = sorted([(individual.normalized_traits[0] + individual.normalized_traits[1], i)
                                for i, individual in enumerate(individuals_group)])
            else:
                order = sorted([(individual.traits[0], i)
                                for i, individual in enumerate(individuals_group)])
            options = [-1] * len(individuals_group)

            for i, (_, individual_id) in enumerate(order):
                group = groups_offset + int(i // average_group_size)
                options[individual_id] = group

            count = Counter(options)
            for key, value in count.items():
                options += [key] * (solver.max_members_per_group - value)
        else:
            for i in range(groups_offset, num_groups + groups_offset):
                options.extend([i] * solver.max_members_per_group)
            random.shuffle(options)

        groups_offset += num_groups
        permutation.append(options)

    # Create a final list of group schedules.
    options = []
    for k in range(sum(solver.timeslots)):
        options.extend([k] * solver.num_boats)
    random.shuffle(options)
    permutation.append(options)

    return permutation

def mutate_permutation(individual, solver):
    method, parameters = solver.current_step.method, solver.current_step.parameters
    # print("Before: {}".format(individual))
    
    if method in (SolverMethod.CLUSTERING, SolverMethod.BOTH):
        # mutate_assignment(individual, solver, parameters['inpdb'])
        for item in individual[:-1]:
            tools.mutShuffleIndexes(item, parameters['inpdb'])

    if method in (SolverMethod.SCHEDULING, SolverMethod.BOTH):
        tools.mutShuffleIndexes(individual[-1], parameters['inpdb'])

    # print("After: {}".format(individual))
    return individual,


def mutate_assignment(individual, solver, probability):
    """Adjusted version of mutShuffleIndexes.

    This function is an adjusted in the way that the probability for exchange is not independent,
    but dependent on the proposed value of the switch.

    Args:
        individual: the solution candidate
        solver: the SolutionSolver instance
        probability: base probability for exchange
    """
    generated_groups = sorted_teams_from_solution(individual, solver.assignable_individuals)
    num_groups_per_collection = [
        solver.get_number_of_groups_by_number_of_individuals(len(collection))
        for collection in individual[:-1]
    ]

    def group_offset(c, g):
        return sum(num_groups_per_collection[:c]) + g

    multiplier = 1.0
    for c, collection in enumerate(individual[:-1]):

        size = len(collection)
        for i in range(size):
            drawn = random.random()
            if drawn > probability * multiplier:
                continue

            swap_indx = random.randint(0, size - 2)
            if swap_indx >= i:
                swap_indx += 1

            swap_group = collection[swap_indx]

            print(solver.num_traits, solver.assignable_individuals[c][i].normalized_traits)
            print(group_offset(c, swap_group))
            print(len(generated_groups))
            difference = sum([abs(solver.assignable_individuals[c][i].normalized_traits[x] -
                              generated_groups[group_offset(c, swap_group)].trait_average(x))
                          for x in range(solver.num_traits)])

            chance = probability * (1.0 / max(1.0, difference)) 
            if drawn < chance:
                collection[i], collection[swap_indx] = collection[swap_indx], collection[i]

    return individual,


def finalize_solution(solution, solver):

    generated_groups = teams_from_solution(solution, solver.assignable_individuals)
    assignable = solver.assignable_groups + generated_groups

    while True:
        score = SolutionScore()
        evaluate_schedule(solution, score, solver, assignable)
        schedule = solution[-1]

        continue_loop = False
        for i in range(solver.courses_per_team * len(assignable)):
            for j in range(i+1, len(schedule)):
                new_schedule = list(schedule)
                new_schedule[i] = schedule[j]
                new_schedule[j] = schedule[i]

                new_score = SolutionScore()
                evaluate_schedule(solution[:-1] + [new_schedule], new_score, solver, assignable)
                if new_score.scheduling_score() > score.scheduling_score():
                    solution = solution[:-1] + [new_schedule]
                    continue_loop = True

            if continue_loop:
                break

        if not continue_loop:
            break

    return solution