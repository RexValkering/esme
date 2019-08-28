"""Contains classes to chain different solver methods."""
import time
from enum import Enum


class SolverMethod(Enum):

    CLUSTERING = 1
    SCHEDULING = 2
    BOTH = 3
    ALTERNATING = 4


class SolverStep(object):
    """Solver parameters for a single step.

    Args:
        i_: step number/name
        method: the method to use (clustering/scheduling/both/alternating)
        kwargs: named parameters to pass
    """

    def __init__(self, i_, method, **kwargs):
        self.method = method
        self.i = i_
        self.parameters = kwargs

    def step(self):
        return self.i


class SolverPhase(object):
    """Solver parameters for a full phase.

    Either iterations or maxtime needs to be defined. If only iterations is defined, the phase runs
    a predefined number of steps. If only maxtime is defined, the iteration runs for a predetermined
    amount of time. If both are defined, it runs until whichever comes first.

    Args:
        method: the method to use (clustering/scheduling/both/alternating)
        iterations: the number of steps to run
        maxtime: the maximum time to run
        kwargs: named parameters to pass
    """

    def __init__(self, method, iterations=None, maxtime=None, **kwargs):
        if iterations is None and maxtime is None:
            raise ValueError("Either iterations or maxtime needs to be defined.")

        self.method = method
        self.iterations = iterations
        self.maxtime = maxtime
        self.parameters = kwargs

        self.starting_time = None
        self.step = 0
        self.global_offset = 0

    def set_offset(self, offset):
        """Set the global offset value.

        Args:
            offset: number of steps preceded.
        """
        self.global_offset = offset

    def _generate_step(self):
        """Generate a SolverStep item for this phase.

        Returns:
            SolverStep
        """
        if self.method == SolverMethod.ALTERNATING:
            return SolverStep(
                self.global_offset + self.step,
                SolverMethod.SCHEDULING if (self.step % 2) else SolverMethod.CLUSTERING,
                **self.parameters
            )
        return SolverStep(self.global_offset + self.step, self.method, **self.parameters)

    def __iter__(self):
        self.step = 0
        return self

    def __next__(self):
        if self.starting_time is None:
            self.starting_time = time.time()

        if ((self.iterations is not None and self.step >= self.iterations) or
                (self.maxtime is not None and time.time() - self.starting_time > self.maxtime)):
            raise StopIteration

        result = self._generate_step()
        self.step += 1
        return result


class SolverIterator(object):
    """An iterator defined by a number of phases.

    Args:
        phases: the phases of this iterator.
    """

    def __init__(self, phases):

        if not all([isinstance(phase, SolverPhase) for phase in phases]):
            raise ValueError("Phase must be instance of class SolverPhase")

        self.phases = phases
        self._set_offset()
        self._current_phase = 0

    def add_phase(self, phase):
        """Append a single phase to the SolverIterator.

        Args:
            phase: phase to append
        """
        if not isinstance(phase, SolverPhase):
            raise ValueError("Phase must be instance of class SolverPhase")

        self.phases.append(phase)
        self._set_offset()

    def _set_offset(self):
        """set the offset for all underlying phases."""
        global_offset = 0
        for phase in self.phases:
            phase.set_offset(global_offset)
            global_offset += phase.iterations

    def __iter__(self):
        self._current_phase = 0
        return self

    def __next__(self):
        if self._current_phase >= len(self.phases):
            raise StopIteration

        phase = self.phases[self._current_phase]
        try:
            return next(phase)
        except StopIteration:
            self._current_phase += 1
            return next(self)
