import unittest
from schedulingsolver.common import SolverMethod
from schedulingsolver.iterator import SolverPhase, SolverIterator


class TestStringMethods(unittest.TestCase):

    def test_empty(self):
        iteration = SolverIterator([])
        with self.assertRaises(StopIteration):
            next(iteration)

    def helper_iterator(self, iterator, expected):
        for method in expected:
            step = next(iterator)
            self.assertEqual(step.method, method)

        with self.assertRaises(StopIteration):
            next(iterator)

    def helper_single(self, method):
        iteration = SolverIterator([SolverPhase(method, 3)])
        for _ in range(3):
            step = next(iteration)
            self.assertEqual(step.method, method)

        with self.assertRaises(StopIteration):
            next(iteration)

    def test_clustering(self):
        self.helper_single(SolverMethod.CLUSTERING)

    def test_scheduling(self):
        self.helper_single(SolverMethod.SCHEDULING)

    def test_combined(self):
        self.helper_single(SolverMethod.BOTH)

    def test_alternate(self):
        iteration = SolverIterator([SolverPhase(SolverMethod.ALTERNATING, 3)])
        expected = [SolverMethod.CLUSTERING, SolverMethod.SCHEDULING, SolverMethod.CLUSTERING]
        self.helper_iterator(iteration, expected)

    def test_complex(self):
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

        self.helper_iterator(iteration, expected)

if __name__ == '__main__':
    unittest.main()