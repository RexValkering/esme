# Introduction

Do you have a training schedule to create? Want to do it with evolutionary computing? Then you're at the right place!

This script was made in an attempt to solve the rower scheduling problem.
Given a list of rowers and the number of available boats and timeslots, can we create a schedule that maximizes the rowers available per course?

# Requirements

- Python3

# Usage

Checkout the code repository and edit the following two files:

*examples/availability-simple.csv*

Make a copy of this file and add your rowers to this file.
The first column denotes the identifier of each rower; you can put a name or a number, it doesn't really matter.
The second column denotes the group of each rower.
If you put a group name, the program tries to schedule each group.
If you leave all groups empty, the program tries to schedule each individual rower.

*examples/config-simple.yaml*

Make a copy of this file and adjust the parameters to your situation.
You can override these parameters using command-line parameters, if you wish.

Once you're done, run the program as follows:

```bash
pip install -r requirements.txt
python main.py -c config.yaml -i examples/availability-simple.csv -v
```

It will them attempt to create a schedule using evolutionary computing. The `-v` flag stands for verbose and tells you what it's doing.

# Examples

Examples are available in the examples folder. Use the following commands to run them:

```bash
python main.py -c examples/config-simple.yaml -i availability-simple.csv -v
python main.py -c examples/config-large.yaml -i availability-large.csv -v 	  # Based on real data
python main.py -c examples/config-random.yaml -v                              # Generates random groups.
```

# How does this work?

This program makes use of Evolutionary Algorithms. Evolutionary Algorithms attempt to solve optimization problems (such as this one) using the traits of evolution: mutation, recombination and survival of the fittest. Each possible schedule is considered an 'individual'. Every generation, the best individuals from that generation are used to form the next generation, which undergo mutation, and the process repeats.

When solving optimization problems, it is important to consider how you model your data: what does an individual look like and how is it mutated? In this algorithm we consider each individual to be a permutation of timeslots. We number the possible timeslots (days x times) and repeat each number for every boat.

