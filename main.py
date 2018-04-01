import random
from deap import creator, base, tools, algorithms
from collections import Counter
import pickle
import os

# A group consists of a group of members.
class Group:

    def __init__(self, members = 6, options = 20):
        self.num_members = members
        self.num_options = options
        self.preferences = [0] * options

    def randomize(self, likelihood = 0.85):
        print likelihood
        for i in range(self.num_options):
            availabilities = [random.random() < likelihood
                              for j in range(self.num_members)]
            self.preferences[i] = sum(availabilities)

    def __repr__(self):
        return repr(self.preferences)

# Number of groups to generate
num_groups = 50

# Number of members per group
num_members = 7

# Number of days
num_days = 5

# Number of distinct timeslots
num_timeslots = 4

num_options = num_days * num_timeslots

# Number of matches required per group
num_matches = 2

# Minimum number of members that should be available per match
min_available = 5

# Number of available boats to assign
num_boats = 5

# Likelihood of a member being available for an option
likelihood = 0.5 # From site

# Number of generations to test.
num_generations = 400

# Population to test
num_population = 400

indpb = 0.05

# File that contains groups:
groups_file = 'groups_05.pickle'

# Print info about current ratio.
total_options_available = num_boats * num_options
total_to_assign = num_groups * num_matches
print("Total options available: {}".format(total_options_available))
print("Total to assign: {}".format(total_to_assign))
print("Ratio: {}/{} ({})".format(total_to_assign, total_options_available,
    float(total_to_assign) / total_options_available))
print("")

# Generate the groups
groups = []

if groups_file != '' and os.path.isfile(groups_file):
    with open(groups_file) as infile:
        groups = pickle.load(infile)
else:
    for i in range(num_groups):
        group = Group(num_members, num_options)
        group.randomize(likelihood)
        groups.append(group)
    with open(groups_file, 'w') as outfile:
        pickle.dump(groups, outfile)

for group in groups:
    print group

# Evaluation function
def evaluatePermutation(individual, debug=False):
    total = 0.0

    for i in range(num_matches * num_groups):
        option = individual[i]
        group = groups[i // num_matches]

        # Ensure enough members are available.
        if group.preferences[option] >= min_available:
            total += float(group.preferences[option]) / group.num_members
        elif debug:
            print "Not enough people"

    # Give penalties for one group being twice assigned to the same day.
    for g in range(num_groups):
        assignments = [individual[g * num_matches + i] // num_timeslots for i in range(num_matches)]

        count = Counter(assignments)
        if count.most_common(1)[0][1] > 1:
            if debug:
                print "Booo you suck"
            total -= 8.0

    return total,

# Create list of options.
def generatePermutation():
    options = []
    for o in range(num_options):
        options.extend([o] * num_boats)
    random.shuffle(options)
    return options

creator.create("FitnessMax", base.Fitness, weights=(1.0,))

# An individual is a permutation of numbers
creator.create("Individual", list, fitness=creator.FitnessMax)

toolbox = base.Toolbox()

toolbox.register("permutation", generatePermutation)
toolbox.register("individual", tools.initIterate, creator.Individual, toolbox.permutation)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)

# Register evaluation function
toolbox.register("evaluate", evaluatePermutation)

# Reproduction and mutation
#toolbox.register("mate", tools.cxOrdered, indpb=0.05)
toolbox.register("mate", lambda a, b: (a, b))
toolbox.register("mutate", tools.mutShuffleIndexes, indpb=indpb)

# Selection method
toolbox.register("select", tools.selTournament, tournsize=3)

# Create population of 20 individuals.
population = toolbox.population(n=num_population)

# Perform evoluationary algorithm
for gen in range(num_generations):
    offspring = algorithms.varAnd(population, toolbox, cxpb=0.5, mutpb=0.1)
    fits = toolbox.map(toolbox.evaluate, offspring)
    for fit, ind in zip(fits, offspring):
        ind.fitness.values = fit
    population = toolbox.select(offspring, k=len(population))

# Select best and report on results
result = tools.selBest(population, k=1)[0]
print(result)

days = {}
for day in range(num_days):
    days[day] = {}
    for slot in range(num_timeslots):
        days[day][slot] = []

for i in range(num_matches * num_groups):
    assigned_option = result[i]
    assigned_group = i // num_matches
    assigned_day = assigned_option // num_timeslots
    assigned_timeslot = assigned_option % num_timeslots
    #print assigned_day, assigned_timeslot, assigned_group

    days[assigned_day][assigned_timeslot].append(assigned_group)

print("Aantal ploegen: {}".format(num_groups))
print("Aantal boten: {}".format(num_boats))
print("Aantal unieke tijdstippen: {}".format(num_options))
print("Oplossingsscore: {}".format(evaluatePermutation(result, True)[0]))
print("Maximale score: {}".format(num_matches * num_groups))
print("")

for day in range(num_days):
    print("Dag {}:".format(day + 1))
    for slot in range(num_timeslots):
        print("\tTijdstip {}: {}".format(slot + 1, ", ".join([str(x) for x in days[day][slot]])))
        for x in days[day][slot]:
            print("\t\t{} {}".format(x, groups[x].preferences[day * num_timeslots + slot]))
    print("")