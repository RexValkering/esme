from esme.common import SolverMethod
from esme.iterator import SolverPhase, SolverIterator

iteration = SolverIterator([
    SolverPhase(SolverMethod.CLUSTERING, 2),
    SolverPhase(SolverMethod.SCHEDULING, 3),
    SolverPhase(SolverMethod.ALTERNATING, 4),
    SolverPhase(SolverMethod.BOTH, 5)
])

expected = ([SolverMethod.CLUSTERING] * 2 + 
            [SolverMethod.SCHEDULING] * 3 +
            [SolverMethod.CLUSTERING, SolverMethod.SCHEDULING,
             SolverMethod.CLUSTERING, SolverMethod.SCHEDULING] +
            [SolverMethod.BOTH] * 5)

for x in iteration:
    print(x.method, x.i)

print(expected)