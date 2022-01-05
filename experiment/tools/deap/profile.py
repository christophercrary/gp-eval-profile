
from inspect import isclass
import math
import os
import pickle
import random
import timeit

from deap import gp
import numpy as np
from sklearn.metrics import r2_score


# Useful directory path.
root_dir = (f'{os.path.dirname(os.path.abspath(__file__))}/../../results/'
            f'programs')

# Seed the relevant random number generator, for reproducibility.
random.seed(37)

########################################################################
# Some helper functions.
########################################################################

def get_max_size(m, d):
  """Return the maximum possible size for a `m`-ary program of depth `d`."""

  if (m==1):
    return d+1
  else:
    return int((1-m**(d+1))/(1-m))

def generate_primitive_set(
    function_set, num_variables, num_constants, erc_name):
    """Return tuple containing (i) the primitive set based on 
    the given function set (`function_set`), number of terminal 
    variables (`num_variables`), and number of terminal constants
    (`num_constants`), and (ii) the fixed ephemeral constant
    list utilized by the primitive set."""

    primitive_set = gp.PrimitiveSet("main", num_variables, prefix="v")

    # Add functions to primitive set.
    for op, arity in function_set:
        primitive_set.addPrimitive(op, arity)

    # Create a list of fixed ephemeral random constants.
    ephemeral_constants = []
    for i in range(num_constants):
        ephemeral_constants.append(random.uniform(-1,1))
    
    # Add an ephemeral constant to the DEAP primitive set that
    # returns a random value from the `ephemeral_constants` list 
    # of random constants. This is done so that there can only
    # exist a particular set of random constants, which is unlike
    # how DEAP would typically implement ephemeral constants.
    primitive_set.addEphemeralConstant(erc_name, lambda: ephemeral_constants[
        random.randint(0, num_constants-1)])

    return (primitive_set, ephemeral_constants)

def generate_program_(primitive_set, min_depth, max_depth, min_size, 
    max_size, desired_trait, ret_type, terminal_condition):
    """Generate a program as done by the `generate` function of the `deap.gp`
    library, except take into account minimum and maximum program sizes,
    by `min_size` and `max_size, respectively.
    """

    if ret_type is None:
        ret_type = primitive_set.ret

    program = []

    if desired_trait == 'depth':
        desired_value = random.randint(min_depth, max_depth)
    else:
        desired_value = random.randint(min_size, max_size)

    # Initial stack for constructing the relevant program.
    stack = [(0, 1)]

    while len(stack) != 0:

        # Retrieve the next relevant node within the stack.
        # The value `depth` represents the depth of this
        # node within the overall random program, the value
        # `size` represents the current size of the overall
        # program, and the value `ret_type` represents the 
        # return type of the current node.
        depth, size = stack.pop()

        if (terminal_condition(stack, depth, size, ret_type,
            primitive_set, min_depth, max_depth, min_size, 
            max_size, desired_trait, desired_value)):

            # A random terminal node is to be chosen.

            terminal = random.choice(primitive_set.terminals[ret_type])

            if isclass(terminal):
                terminal = terminal()

            program.append(terminal)

            # If the stack is nonempty, update the size of the
            # next element to be equivalent to the size of the
            # current node under consideration, so that, upon
            # considering this upcoming element, the `size` value
            # specified by this element will accurately represent 
            # the current program size. (The size of the upcoming
            # element may already be equal to `size`, but it will
            # never be greater than `size`.)
            if len(stack) != 0:
                depth, _ = stack.pop()
                stack.append((depth, size))

        else:

            # A random (valid) function node is to be chosen,
            # if one exists.

            # Valid functions for the current node, 
            # based on function arity.
            valid_functions = [f for f in primitive_set.primitives[ret_type] 
                if size+f.arity <= max_size]

            if valid_functions != [] and desired_trait == 'size':
                # Determine the subset of valid functions that are also
                # valid for potentially constructing a program of the 
                # specified size constraints, given the current program. 
                # (The choice of some functions may preclude the desired 
                # program size.)

                # Maximum function arity for the set of functions that
                # are valid for the current node.
                max_arity = max([f.arity for f in valid_functions])

                temp_functions = []

                for f in valid_functions:

                    # Maximum possible size of subprogram rooted at the 
                    # current node, excluding this node, if the current 
                    # node is given to be `f`.
                    max_possible_size = f.arity * get_max_size(
                        max_arity, max_depth-(depth+1))

                    # Maximum possible program size if the relevant node 
                    # under consideration was chosen to be the function 
                    # `f`. This maximum size would occur if every out-
                    # standing node within the current stack is made to 
                    # be the root of a full `max_arity`-ary subtree such 
                    # that the sum of the depth of this subtree and the 
                    # depth of the root node within the overall program 
                    # is equal to `max_depth`.
                    max_possible_size = (size + max_possible_size if stack==[]
                        else size + max_possible_size + sum([get_max_size(
                            max_arity, max_depth-d)-1 for (d,*_) in stack]))

                    if max_possible_size >= desired_value:
                        temp_functions.append(f)

                valid_functions = temp_functions

            
            function = (None if valid_functions == [] else 
                random.choice(valid_functions))

            if function == None:
                # The current program cannot be made to meet the 
                # specified size constraints.
                return None
            else:
                program.append(function)

            for _ in reversed(function.args):
                # Add a placeholder stack element for each 
                # argument needed by the chosen function.
                stack.append((depth+1, size+function.arity))

    return program

def generate_grow(primitive_set, min_depth, max_depth, min_size, max_size,
    desired_trait, ret_type=None):

    def terminal_condition(stack, depth, size, ret_type,
        primitive_set, min_depth, max_depth, min_size, max_size,
        desired_trait, desired_value):
        """Expression generation stops when the depth is equal to the desired
        depth or when it is randomly determined that a node should be a terminal.
        """

        # List of valid terminals for the current node.
        valid_terminals = [t for t in primitive_set.terminals[ret_type]] 

        # List of valid functions for the current node.
        valid_functions = [f for f in primitive_set.primitives[ret_type] 
            if size+f.arity <= max_size]

        # Maximum function arity for the set of functions that
        # are valid for the current node.
        max_arity = (1 if valid_functions == [] else 
            max([f.arity for f in valid_functions]))

        # Maximum possible program size if the relevant node under
        # consideration is chosen to be a terminal. This maximum size 
        # would occur if every outstanding node within the current stack 
        # is made to be the root of a full `max_arity`-ary subtree such 
        # that the sum of the depth of this subtree and the depth of the 
        # root node within the overall program is equal to `max_depth`.
        # (Note that when `valid_functions` is empty, the value of this 
        # variable is arbitrary.)
        max_possible_size = (size if stack == [] else size + 
            sum([get_max_size(max_arity, max_depth-d)-1
                for (d,*_) in stack]))

        ret = ((valid_terminals != []) and
                ((valid_functions == []) or 
                    (depth == max_depth) or
                    (size == max_size) or
                    ((desired_trait == 'depth') and 
                        (depth == desired_value)) or
                    ((desired_trait == 'size') and 
                        (size >= desired_value)) or
                    ((depth >= min_depth) and 
                        (size >= min_size) and
                        ((desired_trait == 'depth') or
                            ((desired_trait == 'size') and
                                (max_possible_size >= desired_value))) and
                        (random.random() < primitive_set.terminalRatio))))

        return ret

    return generate_program_(primitive_set, min_depth, max_depth, 
        min_size, max_size, desired_trait, ret_type, terminal_condition)
    
def generate_program(gen_strategy, primitive_set, min_depth, max_depth,
    min_size, max_size, desired_trait):
    """Generate a program expression based on the specified initialization
    strategy (`gen_strategy`), primitive set (`primitive_set`), and maximum
    program depth (`max_depth`)."""

    if gen_strategy == 'rhh':
        return gp.genHalfAndHalf(primitive_set, min_=min_depth, max_=max_depth)
    elif gen_strategy == 'full':
        return gp.genFull(primitive_set, min_=max_depth, max_=max_depth)
    else:
        return generate_grow(primitive_set, min_depth, max_depth, min_size,
            max_size, desired_trait)


########################################################################
# Some user-defined GP functions.
########################################################################

def add(x1, x2):
    """Return result of addition."""
    return x1 + x2

def aq(x1, x2):
    """Return result of analytical quotient.
    
    The analytical quotient is as defined by Ni et al. in their paper 
    'The use of an analytic quotient operator in genetic programming':  
    `aq(x1, x2) = (x1)/(sqrt(1+x2^(2)))`.
    """
    return (x1) / (math.sqrt(1 + x2 ** (2)))

def exp(x): 
    """Return result of exponentiation, base `e`."""
    return math.exp(x)

def log(x):
    """Return result of protected logarithm, base `e`."""
    if x != 0:
        return math.log(abs(x))
    else:
        return 0

def mul(x1, x2):
    """Return result of multiplication."""
    return x1 * x2

def sin(x):
    """Return result of sine."""
    return math.sin(x)

def sqrt(x):
    """Return result of protected square root."""
    try:
        return math.sqrt(x)
    except ValueError:
        # Input is negative.
        return 0

def sub(x1, x2):
    """Return result of subtraction."""
    return x1 - x2

def tanh(x):
    """Return result of hyperbolic tangent."""
    return math.tanh(x)


########################################################################
# Some user-defined GP function sets.
########################################################################

nicolau_a = [
  [add, 2], [sub, 2], [mul, 2], [aq, 2]]

nicolau_b = [
  [sin, 1], [tanh, 1], [add, 2], [sub, 2], [mul, 2], [aq, 2]]

nicolau_c = [
  [exp, 1], [log, 1], [sqrt, 1], [sin, 1], [tanh, 1],
  [add, 2], [sub, 2], [mul, 2], [aq, 2]]


########################################################################
# Generation of random programs.
########################################################################

# Program opcode width, used to calculate the number of constants.
opcode_width = 8

# Function sets.
function_sets = {
    'nicolau_a': (nicolau_a, 7, 2),
    'nicolau_b': (nicolau_b, 5, 1),
    'nicolau_c': (nicolau_c, 5, 1)
}

# Maximum arity for each function set.
max_arities = [max([arity for (_, arity) in function_set])
    for _, (function_set, *_) in function_sets.items()]

# Maximum number of size bins.
max_num_size_bins = max([int(math.ceil(
    get_max_size(max_arity, max_depth)/bin_size))
    for (_, (_, max_depth, bin_size)), max_arity in 
        zip(function_sets.items(), max_arities)])

# Desired number of programs to be stored within each size bin.
num_programs_per_size_bin = 1

# Program initialization strategy.
gen_strategy = 'grow'

# Dictionary to map each function set name to the list of files
# that track the programs generated for each size bin associated
# with the function set specified by this name.
program_dict = {name: [([], [], [], [], [], []) 
    for i in range(max_num_size_bins)] for name in function_sets}

# Dictionaries to store `PrimitiveSet` and `PrimitiveTree` 
# objects generated by DEAP.
primitive_sets = {name: None for name in function_sets}
primitive_trees = {name: [[] for _ in range(max_num_size_bins)]
    for name in function_sets}

########################################################################

# Generate random programs for all function sets.
for name, (function_set, max_depth, bin_size) in function_sets.items():

    # Number of functions within function set.
    num_functions = len(function_set)

    # Name strings for functions.
    function_names = [function_set[i][0].__name__ 
        for i in range(num_functions)]

    # Maximum arity for function set.
    max_arity = max([arity for _, arity in function_set])

    # Maximum program size for function set.
    max_possible_size = get_max_size(max_arity, max_depth)

    # Number of size bins.
    num_size_bins = int(math.ceil(max_possible_size/bin_size))

    # Number of variables within primitive set.
    num_variables = num_functions-1

    # Name strings for variables.
    variable_names = ['v'+str(i) for i in range(num_variables)]

    # Number of constants within primitive set.
    num_constants = 2**(opcode_width)-(num_functions+1)-num_variables

    # Desired "generation trait" for random programs.
    desired_trait = 'size'

    # Primitive set and list of (name strings for) constants.
    primitive_set, constant_names = generate_primitive_set(
        function_set, num_variables, num_constants, 'erc_'+name)

    primitive_sets[name] = primitive_set

    # Preserve random constants.
    with open(
        f'{root_dir}/{name}/constants.txt', 'w+') as f:
        for constant in constant_names:
            f.write(f'{constant}\n')

    # print('Opcode width: ', opcode_width)
    # print('Function set: ', function_set)
    # print('Maximum function arity: ', max_arity)
    # print('Number of functions: ', num_functions)
    # print('Number of variables: ', num_variables)
    # print('Number of constants: ', num_constants)
    # print('Maximum program depth: ', max_depth)
    # print('Maximum program size: ', max_possible_size)
    # print('Program generation, strategy: ', gen_strategy)
    # print('Program generation, desired trait:', desired_trait)
    # print('\n')

    ####################################################################

    # Create a uniform distribution of programs based on size bins.

    # Minimum depth for size-constrained programs.
    min_depth = 1

    for i in range(num_size_bins):

        # Minimum/maximum sizes of programs for size bin `i`.
        min_size = i*bin_size+1
        max_size = max_possible_size if i==num_size_bins-1 else (i+1)*bin_size

        for j in range(num_programs_per_size_bin):
            # Generate `num_programs_per_size_bin` random programs
            # for size bin `i`.

            program = generate_program(
                gen_strategy, primitive_set, min_depth, max_depth,
                min_size, max_size, desired_trait)

            if program is None: 
                continue

            # Extract some information about the program.

            program_nodes, _, program_node_labels = gp.graph(program)

            # Size of program.
            size = program_nodes[-1]+1

            # A tree representation of the program.
            program = gp.PrimitiveTree(program)

            # Preserve `PrimitiveTree` object.
            primitive_trees[name][i].append(program)

            # String representation of program.
            program_str = str(program)

            # Depth of program.
            depth = program.height

            # Ensure that the program depth and size are permissible.
            if (depth > max_depth) or (size > max_size): 
                print('Uh-oh...')
                continue

            # Retrieve the relevant program dictionary tuple.
            (programs, depths, sizes, function_counts,
                variable_counts, constant_counts) = program_dict[name][i]

            # Number of programs currently stored in bin with index `i`.
            num_programs = len(programs)

            # Write the newly generated program and its relevant 
            # information to the dictionary if the dictionary does 
            # not already contain `num_programs_per_size_bin` 
            # entries and if this new program is syntactically (not 
            # semantically) distinct from all other programs stored 
            # in the relevant bin.
            if ((num_programs < num_programs_per_size_bin) and
                (programs.count(program_str) == 0)):

                # Extract some additional information about the program.

                # Numbers of instances for each type of function,
                # variable terminal, and constant terminal.
                function_count = [0]*(num_functions)
                variable_count = [0]*(num_variables)
                constant_count = [0]*(num_constants)
                
                for node in program_nodes:

                    node_name = program_node_labels[node]

                    if (node_name in function_names):
                        index = function_names.index(node_name)
                        function_count[index] += 1
                    elif (node_name in variable_names):
                        index = variable_names.index(node_name)
                        variable_count[index] += 1
                    else:
                        index = constant_names.index(node_name)
                        constant_count[index] += 1


                # Update the elements of the relevant dictionary tuple.

                programs.append(program_str)
                depths.append(depth)
                sizes.append(size)

                function_counts = function_count if (
                    function_counts == []) else ([sum(i) for i in 
                        list(zip(function_counts, function_count))])
                    
                variable_counts = variable_count if (
                    variable_counts == []) else ([sum(i) for i in 
                        list(zip(variable_counts, variable_count))])

                constant_counts = constant_count if (
                    constant_counts == []) else ([sum(i) for i in 
                        list(zip(constant_counts, constant_count))])

                program_dict[name][i] = (programs, depths, sizes,
                    function_counts, variable_counts, constant_counts)
            
            
# Pickle the relevant dictionary, so that it can be used by
# other scripts (e.g., `stats.py`).
with open(f'{root_dir}/programs.pkl', 'wb') as f:
    pickle.dump(program_dict, f)


# For each function set, print the number of programs currently 
# within each size bin, and if each bin has been filled with 
# `num_programs_per_size_bin` programs, create a file that 
# contains the programs from every bin, if such a file does 
# not already exist.

print('Numbers of programs:')

for name, (_, max_depth, bin_size) in function_sets.items():

    # Maximum program size for function set.
    max_size = get_max_size(max_arity, max_depth)

    # Number of size bins.
    num_size_bins = int(math.ceil(max_size/bin_size))

    # Number of programs per size bin.
    num_programs = [len(programs) for programs,*_ in program_dict[name]]

    print(name, '=', num_programs, '\n')

    all_bins_are_filled = True if (min(num_programs[0:num_size_bins]) == 
        num_programs_per_size_bin) else False

    if (all_bins_are_filled):
        with open(
            f'{root_dir}/{name}/programs_deap.txt', 'w+') as f:
            for programs, *_ in program_dict[name]:
                for program in programs:
                    f.write(f'{program}\n')


######################################################################## Profiling of program evaluation mechanism given by DEAP.
########################################################################

# Note that the following was not relegated to another 
# script, since it was seemingly not trivial to preserve 
# the primitive sets and namespaces created by DEAP.

def evaluate(primitive_set, trees, fitness_cases, target):
    """Return list of fitness scores for programs.
    
    The "R-squared" function implemented by the `sklearn.metrics` 
    module is used as a fitness function.

    Keyword arguments:
    primitive_set -- Primitive set, of type `PrimitiveSet`, used to 
        compile each `PrimitiveTree` object given by `trees`.
    trees -- Tuple of `PrimitiveTree` objects.
    fitness_cases -- Tuple of fitness cases.
    target -- Tuple of target cases.
    """

    # Fitness scores.
    fitness = []

    for tree in trees:

        # Transform the `PrimitiveTree` object into a callable function.
        program = gp.compile(tree, primitive_set)

        # Calculate program outputs, i.e., estimations of target vector.
        estimated = tuple(program(*fitness_case) 
            for fitness_case in fitness_cases)

        # Calculate fitness.
        fitness.append(r2_score(target, estimated))

    return fitness


# Maximum number of variables across all functions sets.
max_num_variables = max([len(function_set)-1 
    for (function_set, *_) in function_sets.items()])

# Numbers of fitness cases.
num_fitness_cases = (10, 100, 1000, 10000, 100000)

# Random fitness case vector for maximum amount of fitness cases.
fitness_cases_ = np.array(
    [[random.random() for _ in range(max_num_variables)] 
    for _ in range(max(num_fitness_cases))])

# Preserve fitness cases for reference.
with open(f'{root_dir}/fitness_cases.pkl', 'wb') as f:
    pickle.dump(fitness_cases_, f)

# Random target vector for maximum amount of fitness cases.
target_ = np.array([random.random() for _ in range(max(num_fitness_cases))])

# Preserve target for reference.
with open(f'{root_dir}/target.pkl', 'wb') as f:
    pickle.dump(target_, f)

# Value for the `repeat` argument of the `timeit.repeat` method.
repeat = 1

# Value for the `number` argument of the `timeit.repeat` method.
number = 1

# Number of times in which the `timeit.repeat` function is
# called, in order to generate a list of minimum average
# runtimes.
num_epochs = 1

# # Programs sizes for each size bin, for each function set.
# sizes = []

# Minimum average runtimes for programs within each size bin,
# for each number of fitness cases, for each function set.
min_avg_runtimes = []

# # Average of *minimum average runtimes* for each size bin,
# # for each number of fitness cases, for each function set.
# avg_min_avg_runtimes = []

# # Median of *minimum average runtimes* for each size bin,
# # for each number of fitness cases, for each function set.
# med_min_avg_runtimes = []

# # Minimum of *minimum average runtimes* for each size bin,
# # for each number of fitness cases, for each function set.
# min_min_avg_runtimes = []

# # Maximum of *minimum average runtimes* for each size bin,
# # for each number of fitness cases, for each function set.
# max_min_avg_runtimes = []

# # Standard deviation of *minimum average runtimes* for each size 
# # bin, for each number of fitness cases, for each function set.
# std_dev_min_avg_runtimes = []

# # Interquartile range of *minimum average runtimes* for each size 
# # bin, for each number of fitness cases, for each function set.
# iqr_min_avg_runtimes = []

# # Median node evaluations per second (NEPS) for each size bin,
# # for each number of fitness cases, for each function set.
# med_neps = []

for name, (function_set, max_depth, bin_size) in function_sets.items():
    # For each function set...
    print(f'Function set `{name}`:')

    # Number of functions within function set.
    num_functions = len(function_set)

    # Maximum arity for function set.
    max_arity = max([arity for _, arity in function_set])

    # Maximum program size for function set.
    max_possible_size = get_max_size(max_arity, max_depth)

    # Number of size bins.
    num_size_bins = int(math.ceil(max_possible_size/bin_size))

    # Primitive set relevant to function set.
    primitive_set = primitive_sets[name]

    # Number of variables for primitive set.
    num_variables = num_functions - 1

    # Prepare for statistics relevant to function set.
    # sizes.append([])
    min_avg_runtimes.append([])
    # avg_min_avg_runtimes.append([])
    # med_min_avg_runtimes.append([])
    # min_min_avg_runtimes.append([])
    # max_min_avg_runtimes.append([])
    # std_dev_min_avg_runtimes.append([])
    # iqr_min_avg_runtimes.append([])
    # med_neps.append([])

    # For each amount of fitness cases, and for each size bin, 
    # calculate the relevant statistics.

    for nfc in num_fitness_cases:
        # For each number of fitness cases...
        print(f'Number of fitness cases: `{nfc}`')

        # Fitness cases relevant to function set and `nfc`.
        fitness_cases = fitness_cases_[:nfc, :num_variables]

        # Target relevant to `nfc`.
        target = target_[:nfc]

        # Prepare for statistics relevant to the 
        # numbers of fitness cases and size bins.
        min_avg_runtimes[-1].append([[] for _ in range(num_size_bins)])

        for i in range(num_size_bins):

            # `PrimitiveTree` objects for size bin `i`.
            trees = tuple(primitive_trees[name][i])

            # Size of trees. (All sizes are the same for a single bin.)
            # (_, _, sizes_, *_) = program_dict[name][i]
            # sizes[-1].append(sizes_[0])

            for _ in range(num_epochs):
                # For each epoch...

                # Raw runtimes after running `evaluate` function
                # `repeat * number` times.
                runtimes = timeit.Timer(
                    'evaluate(primitive_set, trees, fitness_cases, target)',
                    globals=globals()).repeat(repeat=repeat, number=number)

                # Calculate and append minimum average runtime.
                min_avg_runtimes[-1][-1][i].append(
                    min(runtimes)/(repeat * number))

# Preserve results.
with open(f'{root_dir}/../results_deap.pkl', 'wb') as f:
    pickle.dump(min_avg_runtimes, f)

#print('Shape of `min_avg_runtimes`:', np.shape(np.array(min_avg_runtimes)))

#     # Average of *minimum average runtimes* for each size bin.
#     avg_min_avg_runtimes.append([np.mean(min_avg_runtimes[-1][i]) 
#         for i in range(num_size_bins)])
#     print('Averages of minimum average runtimes:', avg_min_avg_runtimes[-1])
#     print('\n')

#     # Median of *minimum average runtimes* for each size bin.
#     med_min_avg_runtimes.append([np.median(min_avg_runtimes[-1][i]) 
#         for i in range(num_size_bins)])
#     print('Medians of minimum average runtimes:', med_min_avg_runtimes[-1])
#     print('\n')

#     # Minimum of *minimum average runtimes* for each size bin.
#     min_min_avg_runtimes.append([min(min_avg_runtimes[-1][i]) 
#         for i in range(num_size_bins)])
#     print('Minimums of minimum average runtimes:', min_min_avg_runtimes[-1])
#     print('\n')

#     # Maximum of *minimum average runtimes* for each size bin.
#     max_min_avg_runtimes.append([max(min_avg_runtimes[-1][i]) 
#         for i in range(num_size_bins)])
#     print('Maximums of minimum average runtimes:', max_min_avg_runtimes[-1])
#     print('\n')

#     # Standard deviation of minimum average runtimes for each size bin.
#     std_dev_min_avg_runtimes.append([np.std(min_avg_runtimes[-1][i]) 
#         for i in range(num_size_bins)])
#     print('Standard deviations of minimum average runtimes:', 
#         std_dev_min_avg_runtimes[-1])
#     print('\n')

#     # Interquartile range of minimum average runtimes for each size bin.
#     iqr_min_avg_runtimes.append([iqr(min_avg_runtimes[-1][i]) 
#         for i in range(num_size_bins)])
#     print('Interquartile range of minimum average runtimes:', 
#         iqr_min_avg_runtimes[-1])
#     print('\n\n')

#     print('Sizes:', sizes[-1])

#     # Median node evaluations per second relevant to function set.
#     med_neps.append([(size*nfc)/med 
#         for size, med in zip(sizes[-1], med_min_avg_runtimes[-1])])
#     print('Median node evaluations per second:', med_neps[-1])
#     print('\n')


# # Plot graph of median node evaluations per second, 
# # for each function set.
# for i, (name, (function_set, max_depth, bin_size)) in enumerate(
#     function_sets.items()):

#     # Maximum arity for function set.
#     max_arity = max([arity for _, arity in function_set])

#     # Maximum program size for function set.
#     max_possible_size = get_max_size(max_arity, max_depth)

#     # Number of size bins.
#     num_size_bins = int(math.ceil(max_possible_size/bin_size))

#     # Index range for plot.
#     index = range(1, num_size_bins+1)

#     # Plot for function set.
#     # plt.plot(index, [size*nfc for size in sizes[i]])
#     plt.plot(index, med_neps[i], label=f'Function set {name}')
#     # plt.plot(index, [0.00000676*x+0.00009423622 for x in index])

# plt.xlabel('Size bin number')
# plt.ylabel('Median of node evaluations per second')
# plt.title('Median of node evaluations per second vs. size bin number')
# plt.legend(loc='upper left')

# plt.show()
        
