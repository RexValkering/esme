from collections import Counter

from deap import tools

from common import teams_from_solution
from .iterator import SolverMethod


def evaluate_permutation(solution, solver, split_score=False):
    """Calculate the fitness score of a solution.

    Args:
        solution: the solution to calculate fitness score for
        solver: the SchedulingSolver instance
        split_score: whether to split the score (for debugging purposes)
    """

    assignment_score = 0.0
    scheduling_score = 0.0

    clustering_weight, scheduling_weight = solver.current_step.parameters['weights']

    # Create temporary SchedulingGroup objects for measurements.
    generated_groups = teams_from_solution(solution, solver.assignable_individuals)

    for group in generated_groups:

        # Score of 0 if group is too small.
        if len(group.members) < solver.min_members_per_group:
            continue

        # The penalty is the weighted sum of mean trait differences
        if clustering_weight:
            penalty = 0
            if solver.num_traits:
                penalties = [solver.trait_weights[t] *
                             group.trait_cumulative_penalty(t, 0.0, normalize=True)
                             for t in range(solver.num_traits)]
                penalty = sum(penalties) / sum(solver.trait_weights)

            # Evaluate all traits
            assignment_score += 1 - min(1.0, penalty)

    assignable = solver.assignable_groups + generated_groups

    # Evaluate schedules.
    if scheduling_weight:
        for i in range(solver.courses_per_team * (len(generated_groups) + len(solver.assignable_groups))):
            option = solution[-1][i]
            group = assignable[i // solver.courses_per_team]

            # Ensure enough members are available.
            if group.availability(option) >= solver.min_available:
                scheduling_score += float(group.availability(option)) / group.num_members
            else:
                scheduling_score -= 1

        # Give penalties for one group being twice assigned to the same day.
        for g in range(len(assignable)):
            assignments = [solution[-1][g * solver.courses_per_team + i] // solver.num_timeslots for i in range(solver.courses_per_team)]

            count = Counter(assignments)
            if count.most_common(1)[0][1] > 1:
                scheduling_score -= 2.0

    if split_score:
        return scheduling_score, assignment_score

    combined_score = assignment_score * clustering_weight + scheduling_score * scheduling_weight
    return combined_score,


def mutate_permutation(individual, solver):
    method, parameters = solver.current_step.method, solver.current_step.parameters
    
    if method in (SolverMethod.CLUSTERING, SolverMethod.BOTH):
        for item in individual[:-1]:
            tools.mutShuffleIndexes(item, parameters['inpdb'])

    if method in (SolverMethod.SCHEDULING, SolverMethod.BOTH):
        tools.mutShuffleIndexes(individual[-1], parameters['inpdb'])
    return individual, 