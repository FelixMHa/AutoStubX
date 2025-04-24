#
# bash compile.sh && python3 Main.pyx
#

from GeneticAlgorithm import GeneticAlgorithm
import json
import os
import time
import multiprocessing
from multiprocessing import Pool

def run_single_instance(input_data, output_data):
    ga = GeneticAlgorithm()
    ga.setup(input_data, output_data)
    hof, func, score = ga.run(use_multiprocessing=False, timeout=60*15, n_population=5000, n_iterations=100, save_best_individual=False)
    return str(hof), score

def generate_formula(input_data, output_data, output_path=None):
    """
    Generates a formula for the given input and output data

    :param input_data: input data from training data
    :param output_data: output data from training data
    :param output_path: path to save the best individual
    :return: None
    """

    # print the first two samples
    for i in range(2):
        print(input_data[i], type(input_data[i][0]))
        print(output_data[i], type(output_data[i]))
        print()


    cpu_count = max(multiprocessing.cpu_count() - 1, 1)
    start_time = time.time()

    # run the genetic algorithm in parallel
    tasks = [(input_data, output_data) for i in range(cpu_count)]
    pool = Pool(processes=cpu_count)
    results = pool.starmap(run_single_instance, tasks)

    # find the best individual
    best_score = 9999999
    best_func = None
    for func, score in results:
        print(func, score)
        if score < best_score or best_func is None:
            best_score = score
            best_func = func
    print('Best individual')
    print(best_func, best_score)

    # save the best individual as json
    duration = time.time() - start_time
    if output_path is not None:

        with open(output_path, 'w') as f:
            json.dump({'hof' : best_func, 'score': best_score, 'time': duration, 'perplexity': len(best_func.split('('))}, f)

def construct_input_data(samples, max_samples_cnt=1000):
    input_data = []
    output_data = []
    print(samples[0])
    for sample in samples:

        # filter large values as they introduce trouble in Cython
        if sample['typeOutput'] == "java.lang.Integer" or sample['typeOutput'] == "java.lang.Long":
            if abs(sample['output']) >= 2147483648:
                continue

        # skip if the sample if any in - or output is bigger than 2147483648
        input_allowed = True
        for v, t in zip(sample['input'], sample['typeInput']):
            if t == "java.lang.Integer" or t == "java.lang.Long":
                if abs(v) >= 2147483648:
                    input_allowed = False
                    break
        if not input_allowed:
            continue

        input_data.append(sample['input'])
        output_data.append(sample['output'])

        if len(input_data) >= max_samples_cnt:
            break

    if len(input_data) < max_samples_cnt:
        return None, None

    return input_data, output_data


ALREADY_PROCESSED = []

if __name__ == '__main__':
    # start using: bash compile.sh && python3 Main.pyx
    sample_base_path = "../Trainig-Data-Generation/symbolic-regression-data/training/"

    # list all json files in sample_base_path
    sample_files = [f for f in os.listdir(sample_base_path) if f.endswith('.json') and '.extended.' not in f]

    # DEBUG: only look at a single sample!
    # sample_files = [x for x in sample_files if 'isEmpty' in x]

    print(f'Found {len(sample_files)} samples')

    # remove samples that are already processed
    sample_files = [x for x in sample_files if x not in ALREADY_PROCESSED]

    # iterate over all samples
    sample_files_to_process = []
    for sample_file in sample_files:

        # build the save path
        sample_file_path = os.path.join(sample_base_path, sample_file)
        save_path = (sample_file_path
                     .replace('.json', '_best_individual.json')
                     .replace('/training/', '/formulas/'))
        filename = os.path.basename(save_path)
        if filename not in ALREADY_PROCESSED:
            sample_files_to_process.append((sample_file, sample_file_path, save_path))

    print(f'Found {len(sample_files_to_process)} samples to process')

    for sample_file, sample_file_path, save_path in sample_files_to_process:
        # skip if already exists
        #if os.path.exists(save_path):
        #    print('Skipping ' + sample_file)
        #    continue

        # Load training data
        with open(sample_file_path, 'r') as f:
            samples = json.load(f)

        # make sure that we have enough samples
        if len(samples) < 10000:
            print(f'Skipping, as input is too small ({len(samples)}): ' + sample_file)
            continue

        # construct input data
        input_data, output_data = construct_input_data(samples)
        if input_data is None:
            print('Skipping, as input is None: ' + sample_file)
            continue

        print(sample_file)
        try:
            generate_formula(input_data, output_data, save_path)
        except Exception as e:
            print('Error: ' + str(e))
        # break

