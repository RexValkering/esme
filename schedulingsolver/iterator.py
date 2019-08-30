"""Contains classes to chain different solver methods."""
import time
from enum import Enum
import progressbar


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
        # if iterations is None and maxtime is None:
            # raise ValueError("Either iterations or maxtime needs to be defined.")

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

    def register_fitness(self, fitness):
        pass

    def progression_type(self):
        return 'time' if self.maxtime is not None else 'generations'

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

    def stop_iteration(self):
        return (
            (self.iterations is not None and self.step >= self.iterations) or
            (self.maxtime is not None and time.time() - self.starting_time > self.maxtime)
        )

    def __iter__(self):
        self.step = 0
        return self

    def __next__(self):
        if self.starting_time is None:
            self.starting_time = time.time()

        if self.stop_iteration():
            raise StopIteration

        result = self._generate_step()
        self.step += 1
        return result


class SolverProgressionPhase(SolverPhase):

    def __init__(self, method, max_iterations_without_progress, **parameters):
        self.max_iterations_without_progress = max_iterations_without_progress
        self.last_step_with_progress = 0
        self.last_fitness_value = -10**6
        super().__init__(method, **parameters)

    def progression_type(self):
        return 'progression'

    def register_fitness(self, fitness):
        """Register the latest fitness value."""
        if fitness <= self.last_fitness_value:
            return

        self.last_fitness_value = fitness
        self.last_step_with_progress = self.step

    def stop_iteration(self):
        return self.step - self.last_step_with_progress >= self.max_iterations_without_progress


class SolverIterator(object):
    """An iterator defined by a number of phases.

    Args:
        phases: the phases of this iterator.
    """

    _progressbar = None
    _widgets = None
    _current_phase = 0
    phases = None

    def __init__(self, phases):

        if not all([isinstance(phase, SolverPhase) for phase in phases]):
            raise ValueError("Phase must be instance of class SolverPhase")

        self.phases = phases
        self._set_offset()

    def add_phase(self, phase):
        """Append a single phase to the SolverIterator.

        Args:
            phase: phase to append
        """
        if not isinstance(phase, SolverPhase):
            raise ValueError("Phase must be instance of class SolverPhase")

        self.phases.append(phase)
        self._set_offset()

    def register_fitness(self, fitness):
        self.phases[self._current_phase].register_fitness(fitness)

    def widgets(self):
        """Return a list of widgets"""
        if not self._widgets:
            score_widget = progressbar.DynamicMessage('score', width=4)
            self._widgets = [
                progressbar.Percentage(), ' (', progressbar.SimpleProgress(), ') ',
                progressbar.Bar(),
                ' [', score_widget, '] ', progressbar.Timer()
            ]

        return self._widgets

    def progressbar(self, max_value):
        """Build and return a progress bar."""
        if not self._progressbar:
            # phase_types = {phase.progression_type() for phase in self.phases}
            self._progressbar = progressbar.ProgressBar(max_value=max_value, widgets=self.widgets())
        return self._progressbar

    def _set_offset(self):
        """set the offset for all underlying phases."""
        global_offset = 0
        for phase in self.phases:
            phase.set_offset(global_offset)
            global_offset += (phase.iterations if phase.iterations else 0)

    def __iter__(self):
        self._current_phase = 0
        return self

    def __next__(self):
        print("Phase: {}".format(self._current_phase))
        if self._current_phase >= len(self.phases):
            raise StopIteration

        phase = self.phases[self._current_phase]
        try:
            return next(phase)
        except StopIteration:
            print("Received StopIteration")
            self._current_phase += 1
            return next(self)

