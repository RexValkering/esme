[![Sonarcloud Status](https://sonarcloud.io/api/project_badges/measure?project=RexValkering_team-scheduling&metric=alert_status)](https://sonarcloud.io/dashboard?id=RexValkering_team-scheduling)
[![BCH compliance](https://bettercodehub.com/edge/badge/RexValkering/team-scheduling?branch=master)](https://bettercodehub.com/)

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
The CSV requires the following structure:

* The first column denotes the identifier of each rower; you can put a name or a number, it doesn't really matter.
* The second column denotes the group of each rower. If you put a group name, the program tries to schedule each group. If you leave all groups empty, the program tries to schedule each individual rower.
* Third, add a column for each trait, such as length, weight, or years of experience. Skip if you don't do assignment or don't care about the group composition. Make sure the number of traits is correct in the config file.
* Fourth, add a column for each day and timeslot combination.

*config.yaml*

Make a copy of this file and adjust the parameters to your situation.
You can override these parameters using command-line parameters, if you wish.

Once you're done, run the program as follows:

```bash
pip install .
python3 main.py -c my-config.yaml -i my-availability.csv
```

It will then attempt to create a schedule using evolutionary computing.

# Examples

Examples are available in the examples folder. Use the following commands to run them:

```bash
# Generate 12 random groups and do scheduling only.
examples/example-simple.sh

# Generate 78 random individuals without traits and do both group assignment and scheduling.
examples/example-assignment.sh

# Load users from input files and do both group assignment and scheduling. Groups are based on an anonimized dataset.
examples/example-with-input-data.sh
```

For reference: the example datasets are two sets with 315 rowers in total. The average availability is 77.4%. Using this scheduler, I've seen solutions with up to 99,1% availability.

# How does this work?

This program makes use of Evolutionary Algorithms. Evolutionary Algorithms attempt to solve optimization problems (such as this one) using the traits of evolution: mutation, recombination and survival of the fittest. Each possible schedule is considered an 'individual'. Every generation, the best individuals from that generation are used to form the next generation, which undergo mutation, and the process repeats.

When solving optimization problems, it is important to consider how you model your data: what does an individual look like and how is it mutated? In this algorithm we consider each individual/solution to be a permutation of numbers. For scheduling the groups, we number the possible timeslots (days x times) and repeat each number for every boat. For example, given 2 days, 3 timeslots per day and 2 boats per timeslot, each possible solution would be a permutation of the list `[1 1 2 2 3 3 4 4 5 5 6 6]`. Of a solution, the first number is the first course of team 1, the second number is the second course of team 1, the third number is the first course of team 2, and so on.

The advantage of using this notation is that every solution is inherently correct. Every solution is guaranteed to 'fit', you only have to find the optimal one.

## How is scoring done?

For each solution, the program calculates two distinct scores: assignment and scheduling score. Assignment score determines how well the individuals fit into their respective groups. The lesser the difference between traits in a group, the higher the score.

Scheduling score is calculated as the percentage of individuals that can be present at their scheduled time. Some penalties are applied to avoid groups being scheduled twice on the same day and too low availability.

The score of a solution is the sum of both scores, divided by the maximum possible score.
