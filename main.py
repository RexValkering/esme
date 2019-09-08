from esme.solver import SchedulingSolver
from esme.common import parse_args


def main():
    
    args = parse_args()
    solver = SchedulingSolver(args)
    solver.run(report=True)

if __name__ == '__main__':
    main()