"""Contains classes to chain different solver methods."""
import time
from enum import Enum

from matplotlib import pyplot as plt
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
        """Returns whether to end this phase."""
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
        """Returns whether to end this phase."""
        return (
            (self.step - self.last_step_with_progress >= self.max_iterations_without_progress) or
            (self.maxtime is not None and time.time() - self.starting_time > self.maxtime)
        )


class SolverIterator(object):
    """An iterator defined by a number of phases.

    Args:
        phases: the phases of this iterator.
    """

    _progressbar = None
    _widgets = None
    _current_phase = 0
    phases = None
    score_history = None

    def __init__(self, phases):

        if not all([isinstance(phase, SolverPhase) for phase in phases]):
            raise ValueError("Phase must be instance of class SolverPhase")

        self.phases = phases
        self._set_offset()
        self.score_history = []
        self.phase_history = []
        self.current_step = None

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
        """Register the current fitness value.

        Args:
            fitness: solution score
        """
        self.score_history.append(fitness)
        self.phases[self._current_phase].register_fitness(fitness.score())

    def widgets(self):
        """Return a list of widgets"""
        if not self._widgets:
            phases_digits = len(str(len(self.phases)))
            phase_widget = progressbar.DynamicMessage('phase', width=1 + 2 * phases_digits)
            score_widget = progressbar.DynamicMessage('score', width=4)
            self._widgets = [
                ' [', phase_widget, '] ',
                progressbar.Bar(),
                ' [', score_widget, '] ', progressbar.Timer()
            ]

        return self._widgets

    def initialize_progressbar(self):
        """Build and return a progress bar."""
        if not self._progressbar:
            self._progressbar = progressbar.ProgressBar(max_value=100.0, widgets=self.widgets())
        return self._progressbar

    def update_progressbar(self, score, final=False):
        """Update the values shown in the progress bar.

        Args:
            score: current solution score
        """
        self._progressbar.update(self.bar_progress(),
                                 score=score,
                                 phase=self.phase_progress())

    def bar_progress(self):
        if self._current_phase >= len(self.phases):
            return 100.0

        phase_score = float(self._current_phase)
        phase = self.phases[self._current_phase]
        if phase.progression_type() == 'generations':
            phase_score += float(phase.step) / phase.iterations
        return 100.0 / len(self.phases) * phase_score

    def phase_progress(self):
        """Returns a string representation of current phase progress"""
        return "{}/{}".format(self._current_phase, len(self.phases))

    def plot(self, maximum_scores, ax=None, savefile=None):
        """Create a plot of the score progression."""
        plt.style.use('ggplot')
        if not ax:
            figure = plt.figure()
            plot_ax = figure.add_subplot(1, 1, 1)
        else:
            plot_ax = ax

        # Extract relevant values
        assignment, scheduling = zip(*[(score.assignment_score(), score.scheduling_score())
                                       for score in self.score_history])
        total = [assignment[i] + scheduling[i] for i in range(len(assignment))]
        steps = list(range(len(self.score_history)))
        zero = [0.0] * len(steps)

        # Draw score progress
        first = plot_ax.fill_between(steps, zero, assignment, label='Assignment score', alpha=0.3)
        plot_ax.fill_between(steps, assignment, total, label='Scheduling score', alpha=0.3)
        plot_ax.plot(total, color='grey', linewidth=3)

        # Set labels
        plot_ax.set_xlabel('generation')
        plot_ax.set_ylabel('raw score')
        plot_ax.set_title('Progression of score over time')

        # Draw maximum scores
        plot_ax.axhline(y=maximum_scores[0], color=first.get_facecolor()[0], linestyle='dashed', alpha=0.5)
        plot_ax.axhline(y=max(assignment) + maximum_scores[1], color='grey', linestyle='dashed', alpha=0.5)

        # Draw phase transitions
        for _, step in enumerate(self.phase_history):
            plot_ax.axvline(x=step, color='grey', linestyle='dashed', alpha=0.5)

        if savefile is not None:
            figure.savefig(savefile)
        elif ax is None:
            plt.legend()
            plt.show()

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
        # If the last phase has finished, raise a StopIteration
        if self._current_phase >= len(self.phases):
            raise StopIteration

        phase = self.phases[self._current_phase]
        try:
            # Store and return the next phase step
            self.current_step = next(phase)
            return self.current_step
        except StopIteration:
            # Move on to the next phase
            self.phase_history.append(self.current_step.i)
            self._current_phase += 1
            return next(self)

