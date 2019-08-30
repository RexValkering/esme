from collections import Counter, defaultdict

from deap import tools

from common import teams_from_solution, SolutionScore
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
        assignments = [solution[-1][g * solver.courses_per_team + i] // solver.num_timeslots for i in range(solver.courses_per_team)]

        count = Counter(assignments)
        if count.most_common(1)[0][1] > 1:
            score.scheduling['penalty']['Same day schedule'] += 2.0



def mutate_permutation(individual, solver):
    method, parameters = solver.current_step.method, solver.current_step.parameters
    
    if method in (SolverMethod.CLUSTERING, SolverMethod.BOTH):
        for item in individual[:-1]:
            tools.mutShuffleIndexes(item, parameters['inpdb'])

    if method in (SolverMethod.SCHEDULING, SolverMethod.BOTH):
        tools.mutShuffleIndexes(individual[-1], parameters['inpdb'])
    return individual, 