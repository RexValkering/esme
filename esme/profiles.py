from .iterator import SolverIterator, SolverPhase, SolverMethod, SolverProgressionPhase



class SchedulingIterationProfile(SolverIterator):

    def __init__(self, iterations=400, maxtime=None, clustering_weight=1.0, scheduling_weight=1.0):

        weights = [clustering_weight, scheduling_weight]

        phase_iterations = [iterations // 2] * 2
        phase_times = [None] * 2
        if maxtime:
            phase_times = [maxtime * iterations // 2] * 2

        phases = [
            SolverPhase(SolverMethod.SCHEDULING, phase_iterations[0], maxtime=phase_times[0],
                        inpdb=0.05, weights=weights),
            SolverPhase(SolverMethod.SCHEDULING, phase_iterations[1], maxtime=phase_times[1],
                        inpdb=0.01, weights=weights)
        ]

        super().__init__(phases)


class DefaultIterationProfile(SolverIterator):

    def __init__(self, iterations=400, maxtime=None, clustering_weight=1.0, scheduling_weight=1.0):

        weights = [clustering_weight, scheduling_weight]

        phase_iterations = [i * iterations // 10 for i in [1, 2, 4, 3]]
        phase_times = [None] * 4
        if maxtime:
            phase_times = [i * maxtime // 10 for i in [1, 2, 4, 3]]

        phases = [
            SolverPhase(SolverMethod.CLUSTERING, phase_iterations[0], maxtime=phase_times[0],
                        inpdb=0.05, weights=[clustering_weight, 0.0]),
            SolverPhase(SolverMethod.ALTERNATING, phase_iterations[1], maxtime=phase_times[1],
                        inpdb=0.05, weights=weights),
            SolverPhase(SolverMethod.BOTH, phase_iterations[2], maxtime=phase_times[2],
                        inpdb=0.01, weights=weights),
            SolverPhase(SolverMethod.SCHEDULING, phase_iterations[3], maxtime=phase_times[3],
                        inpdb=0.01, weights=weights)
        ]

        super().__init__(phases)


class ProgressionIterationProfile(SolverIterator):

    def __init__(self, iterations=10, maxtime=None, clustering_weight=1.0, scheduling_weight=1.0):

        weights = [clustering_weight, scheduling_weight]

        phase_iterations = [iterations] * 4
        phase_times = [None] * 4
        if maxtime:
            phase_times = [i * maxtime // 10 for i in [1, 2, 4, 3]]

        phases = [
            SolverProgressionPhase(SolverMethod.CLUSTERING, phase_iterations[0], maxtime=phase_times[0],
                                   inpdb=0.05, weights=[clustering_weight, 0.0]),
            SolverProgressionPhase(SolverMethod.ALTERNATING, phase_iterations[1], maxtime=phase_times[1],
                                   inpdb=0.05, weights=weights),
            SolverProgressionPhase(SolverMethod.BOTH, phase_iterations[2], maxtime=phase_times[2],
                                   inpdb=0.01, weights=weights),
            SolverProgressionPhase(SolverMethod.SCHEDULING, phase_iterations[3], maxtime=phase_times[3],
                                   inpdb=0.01, weights=weights)
        ]

        super().__init__(phases)


PROFILES = {
    'default': DefaultIterationProfile,
    'progression': ProgressionIterationProfile,
    'scheduling': SchedulingIterationProfile
}


def parse_profile(profile_string):
    """Parse the provided solution profile"""

    # Set default number of generations if not provided.
    if profile_string == 'default':
        profile_string == 'default 400'

    profile, iterations, maxtime = None, None, None
    parts = profile_string.split()
    if not 1 < len(parts) < 4:
        raise ValueError('Cannot parse profile parameter: {}'.format(profile_string))

    profile, iterations = parts[0], int(parts[1])
    if len(parts) == 3:
        maxtime = float(parts[2])

    if profile not in PROFILES:
        raise ValueError('Profile does not exist: {}'.format(profile))

    return PROFILES[profile](iterations, maxtime)