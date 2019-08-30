from .iterator import SolverIterator, SolverPhase, SolverMethod, SolverProgressionPhase

class DefaultIterationProfile(SolverIterator):

    def __init__(self, generations=400, clustering_weight=1.0, scheduling_weight=1.0):

        weights = [clustering_weight, scheduling_weight]

        steps_per_phase = generations // 4
        phases = [
            SolverPhase(SolverMethod.CLUSTERING, steps_per_phase, inpdb=0.05,
                        weights=[clustering_weight, 0.0]),
            SolverPhase(SolverMethod.ALTERNATING, steps_per_phase, inpdb=0.05, weights=weights),
            SolverPhase(SolverMethod.BOTH, steps_per_phase, inpdb=0.01, weights=weights),
            SolverPhase(SolverMethod.SCHEDULING, steps_per_phase, inpdb=0.01, weights=weights)
        ]

        super().__init__(phases)


class ProgressionIterationProfile(SolverIterator):

    def __init__(self, max_iterations_without_progress=10, clustering_weight=1.0, scheduling_weight=1.0):

        weights = [clustering_weight, scheduling_weight]

        phases = [
            SolverProgressionPhase(SolverMethod.CLUSTERING, max_iterations_without_progress, inpdb=0.05,
                        weights=[clustering_weight, 0.0]),
            SolverProgressionPhase(SolverMethod.ALTERNATING, max_iterations_without_progress, inpdb=0.05, weights=weights),
            SolverProgressionPhase(SolverMethod.BOTH, max_iterations_without_progress, inpdb=0.01, weights=weights),
            SolverProgressionPhase(SolverMethod.SCHEDULING, max_iterations_without_progress, inpdb=0.01, weights=weights)
        ]

        super().__init__(phases)
