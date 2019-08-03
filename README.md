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

*config.yaml*

Adjust the parameters to your situation.
You can override these parameters using command-line parameters, if you wish.

Once you're done, run the program as follows:

```bash
python3 main.py -c config.yaml -i examples/availability-simple.csv
```

It will them attempt to create a schedule using evolutionary computing.

# Examples

Examples are available in the examples folder. Use the following commands to run them:

```bash
# Generate 40 random groups and do scheduling only.
python3 main.py -c examples/config-scheduling-only.yaml

# Use groups from input file and do scheduling only. Groups are based on real data.
python3 main.py -c examples/config-scheduling-only.yaml -i examples/availability-large.csv

# Generate a group of random individuals and schedule them into groups
python3 main.py -c examples/config-clustering-and-scheduling.yaml

python3 main.py -c examples/config-large.yaml -i availability-large.csv     # Based on real data
python3 main.py -c examples/config-random.yaml                              # Generates random groups.
```


