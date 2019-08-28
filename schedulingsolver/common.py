import argparse
from collections import defaultdict
from entities import SchedulingGroup


def teams_from_solution(solution, assignable_individuals):
    """Generate teams from the individuals that were scheduled.

    Args:
        solution: the solution permutation
        assignable_individuals: the individuals to assign to temporary groups

    Returns:
        list of SchedulingGroup instances
    """
    generated_teams = defaultdict(list)

    # Add all individuals to a group list, then create the group based on its members
    for i, category in enumerate(assignable_individuals):
        part = solution[i]
        for individual, group in enumerate(part):
            if individual >= len(category):
                break
            generated_teams[group].append(category[individual])

    return [SchedulingGroup('Generated group {}'.format(g+1), members)
            for g, members in generated_teams.items()]


def sorted_teams_from_solution(solution, assignable_individuals):
    """Generate teams and sort them by id.

    Args:
        solution: the solution permutation
        assignable_individuals: the individuals to assign to temporary groups

    Returns:
        list of SchedulingGroup instances
    """
    return sorted(
        teams_from_solution(solution, assignable_individuals),
        key=lambda x: x.id
    )


def parse_args():
    """Define the command line arguments to be passed."""
    parser = argparse.ArgumentParser()

    group = parser.add_argument_group('files')
    group.add_argument('-i', '--input', nargs='*', help='input csv file(s)')
    group.add_argument('-o', '--output', help='csv file to output schedule to')
    group.add_argument('-s', '--savefile', help='csv file to save generated individuals to (if no input specified)')
    group.add_argument('-c', '--config', help='config .yaml file')

    group = parser.add_argument_group('general')
    group.add_argument('--score', help='Score the provided solution files instead.', action='store_true')
    group.add_argument('--generate',
                        help='Set to `individuals` to generate individuals without groups ' + 
                             'or to `groups` to generate individuals with groups. Ignored if one ' +
                             'or more input files are supplied.',
                        choices=['individuals', 'groups'])
    group.add_argument('-g', '--num_to_generate', help='number of individuals/groups to generate', type=int)
    
    group.add_argument('--num_traits', help='number of traits in input csv files')
    group.add_argument('-w', '--trait_weights', nargs='*', help='trait weights')
    group.add_argument('-m', '--solution_mode',
                       help="1: clustering only; 2: scheduling only; 3; both clustering and scheduling; 4: alternating",
                       type=int, default=3)

    group = parser.add_argument_group('parameters')
    group.add_argument('-min', '--min_members_per_group', help='minimum number of members per group', type=int)
    group.add_argument('-max', '--max_members_per_group', help='maximum number of members per group', type=int)
    group.add_argument('-b', '--num_boats', help='number of boats per time slot', type=int)
    group.add_argument('-t', '--num_timeslots', help='number of timeslots per day', type=int)
    group.add_argument('-d', '--num_days', help='number of days to schedule', type=int)
    group.add_argument('-n', '--courses_per_team', help='number of courses to schedule per group per week', type=int)
    group.add_argument('-a', '--min_available', help='minimum number of members available per course', type=int)
    group.add_argument('-l', '--availability_likelihood', help='likelihood of a member being available for an option', type=float)
    group.add_argument('-x', '--generations', help='number of generations to test', type=int)
    group.add_argument('-y', '--population', help='population size per generation', type=int)
    group.add_argument('-z', '--indpb', help='evolution algorithm parameter', type=float)
    args = parser.parse_args()
    return args