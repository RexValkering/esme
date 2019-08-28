from .iterator import SolverIterator, SolverPhase, SolverMethod

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
