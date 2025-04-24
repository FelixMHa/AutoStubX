import json
import glob
import os
from pathlib import Path
from Helper import *
import subprocess
from tqdm import tqdm
import random

# clear all old files
os.system('cd java-benchmark && rm -rf *')
benchmark_dir = Path('java-benchmark')

# list all training data files
training_files = glob.glob('../Trainig-Data-Generation/symbolic-regression-data/training/*.json')
print(f'Found {len(training_files)} training files')

# open base mapping
with open('../Trainig-Data-Generation/methods_in_scope.json', 'r') as f:
    base_mapping = json.load(f)

java_template = """

public class Benchmark%idx% {
    public static void main(String[] args) {
        // fetch input
%input_fetch_code%

        // Perform computation         
%function_code%
        
        // Compare output
        if (%compare_code%) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

"""

# go trough all training files and create a benchmark file
for sample_idx, training_file in enumerate(tqdm(training_files)):

    # DEBUG
    #if 'isEmpty' not in training_file:
    #    continue

    #print(sample_idx, training_file)
    training_file = Path(training_file)
    with open(training_file, 'r') as f:
        training_data = json.load(f)

    base_mapping_key = training_file.name
    key = training_file.name.replace('_.json', '')
    if base_mapping_key not in base_mapping:
        print(base_mapping_key)
        continue
    types = base_mapping[base_mapping_key]
    filtered_type = types['owner'].replace('java.lang.', '')

    # Create directory if not exists
    testcase_dir = benchmark_dir / filtered_type / key
    os.makedirs(testcase_dir, exist_ok=True)

    # filter so that only readables are considered
    training_data = [x for x in training_data if is_ascii_printable(x['output'])]
    training_data = [x for x in training_data if len(x['input']) == len([y for y in x['input'] if is_ascii_printable(y)])]

    if len(training_data) < 10:
        continue

    samples = []
    for test_idx in range(10):
        # create a single sample
        code = java_template.replace('%idx%', str(test_idx))

        # shuffle the training data
        random.shuffle(training_data)
        sample1, sample2 = find_two_with_different_output(training_data)
        if sample1 is None:
            break
        samples.append((sample1, sample2))

        input_fetch_code = ""
        input_names = {
            1: [],
            2: []
        }

        for i in range(len(sample1['input'])):
            input_type = sample1['typeInput'][i].replace('java.lang.', '')
            if input_type == 'Character':
                input_fetch_code += f"        {input_type} input_1_{i} = args[{i}].charAt(0);\n"
            else:
                input_fetch_code += f"        {input_type} input_1_{i} = {input_type}.valueOf(args[{i}]);\n"
            input_names[1].append(f'input_1_{i}')
        offset = len(sample1['input'])
        for i in range(len(sample2['input'])):
            input_type = sample2['typeInput'][i].replace('java.lang.', '')
            if input_type == 'Character':
                input_fetch_code += f"        {input_type} input_2_{i} = args[{i + offset}].charAt(0);\n"
            else:
                input_fetch_code += f"        {input_type} input_2_{i} = {input_type}.valueOf(args[{i + offset}]);\n"
            input_names[2].append(f'input_2_{i}')

        # Generate computation code
        output_type = sample1['typeOutput'].replace('java.lang.', '')
        function_code = ""
        for i in [1, 2]:
            if '_static_' in key:
                function_code += f'        {output_type} output_{i} = {filtered_type}.{types["name"]}({", ".join(input_names[i])});\n'
            else:
                function_code += f'        {output_type} output_{i} = {input_names[i][0]}.{types["name"]}({", ".join(input_names[i][1:])});\n'

        compare_code = ''
        if output_type == 'String':
            o1 = json.dumps(sample1["output"])
            o2 = json.dumps(sample2["output"])
            compare_code = f'output_1.equals({o1}) && output_2.equals({o2})'
        elif output_type == 'Character':
            o1 = sample1["output"].replace("'", "\\'")
            o2 = sample2["output"].replace("'", "\\'")
            compare_code = f'output_1 == \'{o1}\' && output_2 == \'{o2}\''
        elif output_type == 'Long':
            compare_code = f'output_1 == {sample1["output"]}L && output_2 == {sample2["output"]}L'
        elif output_type == 'Boolean':
            compare_code = f'output_1 == {str(sample1["output"]).lower()} && output_2 == {str(sample2["output"]).lower()}'
        else:
            compare_code = f'output_1 == {sample1["output"]} && output_2 == {sample2["output"]}'


        code = code.replace('%input_fetch_code%', input_fetch_code)
        code = code.replace('%compare_code%', compare_code)
        code = code.replace('%function_code%', function_code)

        # save code
        with open(testcase_dir / f'Benchmark{test_idx}.java', 'w') as f:
            f.write(code)

    if len(samples) < 10:
        continue

    # save correct input and output values
    with open(testcase_dir / 'sample.json', 'w') as f:
        json.dump({
            'key': key,
            'samples': samples
        }, f)

    # compile
    status = subprocess.run('javac *.java', cwd=testcase_dir, shell=True)
    if status.returncode != 0:
        raise Exception(f'Error compiling {testcase_dir}')
