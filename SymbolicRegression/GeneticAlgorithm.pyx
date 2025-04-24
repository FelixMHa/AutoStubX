import CustomFunctions as cf
from deap import gp, base, creator, tools, algorithms
import random
import numpy as np
import operator
import Levenshtein # pip3 install levenshtein
import multiprocessing
from DummyTypes import BOOL, FLOAT, INT, STRING
import time



class GeneticAlgorithm:

    _pset = None
    _cache = {}
    _toolbox = None
    global_input_data = None
    global_output_data = None

    # constructor
    def setup(self, input_data, output_data, use_strings=False, use_floats=False, max_height=None, selection_algorithm='tournament'):

        # clear cache
        self._cache = {}

        input_data, output_data = self._check_input_output_data(input_data, output_data)

        # gather input types
        input_type = []
        string_present = False
        float_present = False
        for x in input_data[0]:
            string_present = string_present or isinstance(x, STRING) # check if string
            float_present = float_present or isinstance(x, FLOAT) # check if float
            input_type.append(type(x))

        # Dynamically set the allowed input types
        if not use_strings and (string_present or isinstance(output_data[0], STRING)):
            #print("use_strings is False but input or output data contains strings -> settint use_strings to True")
            use_strings = True
        if not use_floats and float_present:
            #print("use_floats is False but input data contains floats -> settint use_floats to True")
            use_floats = True

        # Define the Primitive Set
        self._setup_pset(input_type, type(output_data[0]), use_strings, use_floats)

        # Define Fitness Function and Type
        creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
        creator.create("Individual", gp.PrimitiveTree, fitness=creator.FitnessMin)

        # Define the Toolbox
        toolbox = base.Toolbox()
        toolbox.register("expr", gp.genHalfAndHalf, pset=self._pset, min_=0, max_=0)
        toolbox.register("individual", tools.initIterate, creator.Individual, toolbox.expr)
        toolbox.register("population", tools.initRepeat, list, toolbox.individual)
        toolbox.register("compile", gp.compile, pset=self._pset)


        if selection_algorithm == 'tournament':
            toolbox.register("select", tools.selTournament, tournsize=8) # tournament size of 4, i.e., 4 individuals are selected at random and the best one is chosen
        elif selection_algorithm == 'lexicase':
            toolbox.register("select", tools.selLexicase)
        else:
            raise Exception("Selection algorithm not supported")
        toolbox.register("mate", gp.cxOnePoint)
        toolbox.register("expr_mut", gp.genFull, min_=0, max_=3) # minimum and maximum depth of the generated tree
        toolbox.register("mutate", gp.mutUniform, expr=toolbox.expr_mut, pset=self._pset)

        # define max height of trees
        if max_height is None:
            max_height = len(input_data[0])
            max_height = min(max(max_height, 3), 8) # bound between 4 and 8 (used to be 7 and 12)
        max_height = 1 # DEBUG!

        self.global_input_data = input_data
        self.global_output_data = output_data
        toolbox.register("evaluate", self._safe_eval_wrapper)
        toolbox.decorate("mutate", gp.staticLimit(key=operator.attrgetter("height"), max_value=max_height))
        toolbox.decorate("mate", gp.staticLimit(key=operator.attrgetter("height"), max_value=max_height))

        toolbox.register("population", tools.initRepeat, list, toolbox.individual)
        #toolbox.register("expr", gp.genHalfAndHalf, pset=self._pset, min_=0, max_=3) # initialize the population with trees of depth 1 and 2

        self._toolbox = toolbox


    def _check_input_output_data(self, input_data, output_data):

        # check if input_data is a list of lists containing either floats or strings
        if not isinstance(input_data, list):
            raise Exception("input_data must be a list of lists")
        if not isinstance(output_data, list):
            raise Exception("output_data must be a list")

        # check if input_data and output_data have the same length
        if len(input_data) != len(output_data):
            raise Exception("input_data and output_data must have the same length")

        # check if input_data is a list of lists containing either floats or strings
        for inp in input_data:
            if not isinstance(inp, list):
                raise Exception("input_data must be a list of lists")

        # output must not be a list of lists
        for out in output_data:
            if isinstance(out, list):
                raise Exception("output_data must not be a list")

        # convert all types to float or string
        input_data = [[self.convert_single_value(x) for x in sublist] for sublist in input_data]
        output_data = [self.convert_single_value(x) for x in output_data]

        return input_data, output_data


    def convert_single_value(self, v):
        if isinstance(v, str):
            return STRING(v)
        if isinstance(v, bool):
            return BOOL(v)
        if isinstance(v, int):
            return INT(v)

        return FLOAT(float(v))


    def _setup_pset(self, input_type, output_type, use_strings=False, use_floats=False):
        pset = gp.PrimitiveSetTyped("MAIN", input_type, output_type)  # Example: Main set takes a string and a float, returns a float

        # Real theory https://smtlib.cs.uiowa.edu/theories-Reals.shtml
        if use_floats:
            pset.addPrimitive(cf.real_neg, [FLOAT], FLOAT)
            pset.addPrimitive(cf.real_sub, [FLOAT, FLOAT], FLOAT)
            pset.addPrimitive(cf.real_add, [FLOAT, FLOAT], FLOAT)
            pset.addPrimitive(cf.real_mul, [FLOAT, FLOAT], FLOAT)
            pset.addPrimitive(cf.real_div, [FLOAT, FLOAT], FLOAT)
            pset.addPrimitive(cf.real_cos, [FLOAT], FLOAT)
            pset.addPrimitive(cf.real_less_than, [FLOAT, FLOAT], BOOL)
            pset.addPrimitive(cf.real_floor, [FLOAT], FLOAT) # Custom
            pset.addPrimitive(cf.real_abs, [FLOAT], FLOAT) # Custom
            pset.addPrimitive(cf.real_if_then_else, [BOOL, FLOAT, FLOAT], FLOAT) # Custom
            pset.addPrimitive(cf.real_compare_as_int, [FLOAT, FLOAT], BOOL) # Custom
        
        # Int
        pset.addPrimitive(cf.int_neg, [INT], INT)
        pset.addPrimitive(cf.int_sub, [INT, INT], INT)
        pset.addPrimitive(cf.int_add, [INT, INT], INT)
        pset.addPrimitive(cf.int_mul, [INT, INT], INT)
        pset.addPrimitive(cf.int_div, [INT, INT], FLOAT)
        pset.addPrimitive(cf.int_less_than, [INT, INT], BOOL)
        pset.addPrimitive(cf.int_abs, [INT], INT) # Custom
        pset.addPrimitive(cf.int_if_then_else, [BOOL, INT, INT], INT) # Custom
        pset.addPrimitive(cf.int_compare, [INT, INT], BOOL) # Custom
        pset.addPrimitive(cf.int_compare_range, [INT, INT, INT], BOOL) # Custom

        # Logic theory https://smtlib.cs.uiowa.edu/theories-Core.shtml
        pset.addPrimitive(cf.logic_not, [BOOL], BOOL)
        #pset.addPrimitive(logic_conditional, 2)
        pset.addPrimitive(cf.logic_and, [BOOL, BOOL], BOOL)
        pset.addPrimitive(cf.logic_or, [BOOL, BOOL], BOOL)
        pset.addPrimitive(cf.logic_xor, [BOOL, BOOL], BOOL)

        if use_strings:
            # String theory https://smtlib.cs.uiowa.edu/theories-UnicodeStrings.shtml
            # http://cvc4.cs.stanford.edu/wiki/Strings
            pset.addPrimitive(cf.string_concat, [STRING, STRING], STRING)
            pset.addPrimitive(cf.string_length,[STRING], INT)
            pset.addPrimitive(cf.string_contains, [STRING, STRING], BOOL)
            pset.addPrimitive(cf.string_index_of, [STRING, STRING], INT)
            pset.addPrimitive(cf.string_replace_all, [STRING, STRING, STRING], STRING)
            pset.addPrimitive(cf.string_replace, [STRING, STRING, STRING], STRING)
            pset.addPrimitive(cf.string_substring, [STRING, INT, INT], STRING)
            pset.addPrimitive(cf.string_to_int, [STRING], INT)
            pset.addPrimitive(cf.int_to_string, [INT], STRING)
            pset.addPrimitive(cf.str_compare, [STRING, STRING], BOOL)
            pset.addPrimitive(cf.str_if_then_else, [BOOL, STRING, STRING], STRING)
            pset.addPrimitive(cf.ascii_to_string, [INT], STRING)
            pset.addPrimitive(cf.string_to_ascii, [STRING], INT)

        if use_strings and use_floats:
            pset.addPrimitive(cf.string_to_float, [STRING], FLOAT)
            pset.addPrimitive(cf.float_to_string, [FLOAT], STRING)
            print('Added string to float and float to string')

        # Add Terminal Set (= Constants)
        pset.addTerminal(FLOAT(float(-1.0)), ret_type=FLOAT)
        pset.addTerminal(FLOAT(float(0.0)), ret_type=FLOAT)
        pset.addTerminal(FLOAT(float(1.0)), ret_type=FLOAT)

        # boolean
        pset.addTerminal(BOOL(True), ret_type=BOOL)
        pset.addTerminal(BOOL(False), ret_type=BOOL)

        # String
        pset.addTerminal(STRING(" "), ret_type=STRING)
        pset.addTerminal(STRING(""), ret_type=STRING)

        # Add Ephemeral Random Constants
        pset.addEphemeralConstant("ERC_FLOAT", self._generate_erc_float, ret_type=FLOAT)
        pset.addEphemeralConstant("ERC_INT", self._generate_erc_int, ret_type=INT)

        # register types
        pset.context['INT'] = INT
        pset.context['FLOAT'] = FLOAT
        pset.context['STRING'] = STRING
        pset.context['BOOL'] = BOOL

        self._pset = pset


    def _generate_erc_float(self):
        if random.random() < 0.5:
            return FLOAT(float(random.uniform(-256, 256)))
        return FLOAT(float(random.uniform(-1, 1)))


    def _generate_erc_int(self):
        return INT(int(random.uniform(-10, 256)))


    def _safe_eval_wrapper(self, individual):

        # Random baseline: Return a random fitness value
        return (random.random()*10 + 11, )

        individual_as_string = str(individual)

        # Checks
        if 'ARG' not in individual_as_string:
            return (np.inf, ) # No constant functions allowed

        # cache
        if individual_as_string in self._cache:
            return (self._cache[individual_as_string], )

        try:
            v = self._eval_func(individual)

            # calculate the number of nodes in the tree
            nodes = len(individual)
            fitness = v + (nodes / 10000.0)

            # cache
            self._cache[individual_as_string] = fitness
            return (fitness, ) # syntax for DEAP
        except Exception as e:

            #print(individual)
            #print(f"Error evaluating individual: {e}")
            #print('-')
            # raise e
            # Return a default fitness value in case of error
            return (float("inf"),)


    def _eval_func(self, individual):
        func = self._toolbox.compile(expr=individual)
        #print(individual)

        # 64bit float
        errors = []
        for inp, out in zip(self.global_input_data, self.global_output_data):
            # Ensure inp is a list of inputs for the function
            predicted = func(*inp)  # Assuming inp is already a list of arguments for the function

            #print(f"Predicted: {predicted} | Expected: {out}")
            #print(f'Predicted type: {type(predicted)} | Expected type: {type(out)}')

            # check if output is nan
            if predicted.error:
                #print('error in prediction. If it does not happen often, ignore it. If it happens often, check the function.')
                return np.inf

            # check if output is a string
            if isinstance(out, STRING):
                # calculate the levenstein distance between the predicted and the actual output
                #if str(individual) == 'float_to_string(ARG0)':
                #    print(f"Predicted: {predicted.value} | Expected: {out.value}")
                #    print(f'{len(predicted.value)} | {len(out.value)}')
                err = Levenshtein.distance(str(predicted.value), str(out.value)) ** 2

            elif isinstance(out, FLOAT) or isinstance(out, INT):
                # Calculate the squared error between the predicted and the actual output
                err = (predicted.value - out.value)**2

            elif isinstance(out, BOOL):
                err = 0 if predicted.value == out.value else 1

            else:
                raise Exception("Output type not supported: ", type(predicted))

            #if str(individual) == 'int_abs(ARG0)' and err > 1:
            #    print(f"Predicted: {predicted.value} | Expected: {out.value}")
            #    print(f'Error: {err}')
            #    print('-')

            errors.append(err)

        mean_error = sum(errors) / len(errors)
        # check if mean_error is nan
        if np.isnan(mean_error):
            return np.inf

        return np.sqrt(mean_error)


    def save_best_individual(self, score, hof):
        # Save the best individual
        with open("best_individual.txt", "w") as f:
            f.write(str(score) + "\n" + str(hof[0]))


    def run(self, n_population=500, n_iterations=100, mutation_rate=0.25, use_multiprocessing=True, save_best_individual=True, timeout=3600):

        # multiprocessing
        if use_multiprocessing:
            cpu_count = max(multiprocessing.cpu_count() - 1, 1)
            print(f"Multiprocessing using {cpu_count} cores")
            pool = multiprocessing.Pool(cpu_count)
            self._toolbox.register("map", pool.map)

        # setup population
        population = self._toolbox.population(n=n_population)

        # setup statistics
        hof = tools.HallOfFame(1)  # keeps track of the single best individual
        stats = tools.Statistics(lambda ind: ind.fitness.values)
        stats.register("avg", np.mean)
        stats.register("min", np.min)


        # Run the algorithm
        best_score = 10000000000
        last_score_increase = 0
        start_time = time.time()
        for gen in range(n_iterations):  # Number of generations
            population = algorithms.varAnd(population, self._toolbox, cxpb=0.5, mutpb=mutation_rate)
            fits = self._toolbox.map(self._toolbox.evaluate, population)
            for fit, ind in zip(fits, population):
                ind.fitness.values = fit
            population = self._toolbox.select(population, k=len(population))
            hof.update(population)
            record = stats.compile(population) if stats is not None else {}
            #print(f"{gen}   {len(population)}   {record['avg']:.4f}    {record['min']:.4f}")
            if record['min'] < best_score:
                last_score_increase = gen
                best_score = record['min']
                if save_best_individual:
                    self.save_best_individual(best_score, hof)
                print(hof[0], best_score)

            # early stopping
            if best_score < 0.0000001:
                break

            # check if one hour has passed
            if time.time() - start_time > timeout:
                break

            # if the score has not improved for 75 generations
            if gen - last_score_increase > 75:
                break
        #print('Final:')
        #print(f"Best score: {best_score}")
        #print(hof[0])

        func = self._toolbox.compile(expr=hof[0])
        error = best_score - (len(hof[0]) / 10000.0)
        return hof[0], func, error # return the best individual and the function