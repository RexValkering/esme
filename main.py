from esme.solver import SchedulingSolver
from esme.common import parse_args


def main():
    
    args = parse_args()
    solver = SchedulingSolver(args)
    solver.solve()
    if solver.output_prefix:
        solver.save_results_to_file()
    solver.report()
    solver.plot_progress()


if __name__ == '__main__':
    main()