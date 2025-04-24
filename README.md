# AutoStub: Genetic Programming-Based Stub Creation for Symbolic Execution

[![Dataset](https://img.shields.io/badge/🤗%20Hugging%20Face-Dataset-yellow)](https://huggingface.co/datasets/Felix6326727/AutoStub/) 

AutoStub is a novel approach to automatically generate symbolic stubs for external functions during symbolic execution using Genetic Programming. When the symbolic executor encounters an external function (such as a native method or third-party library), AutoStub generates training data and uses Genetic Programming to derive expressions that approximate the function's behavior.

## Overview

Symbolic execution faces significant limitations when encountering external functions that cannot be symbolically analyzed. AutoStub addresses this challenge through a three-step process:

1. **Training Data Generation**: When encountering an external function, AutoStub collects input-output pairs by executing the function with diverse inputs
2. **Symbolic Expression Synthesis**: Grammar-Guided Genetic Programming derives expressions that approximate function behavior
3. **Stub Integration**: Generated expressions serve as symbolic stubs that enable the symbolic executor to continue analysis

## Key Features

- **Automatic Stub Generation**: No manual intervention required
- **Type-Aware Expressions**: Supports multiple data types including primitives and strings
- **Language-Specific Behavior**: Infers edge cases essential for testing
- **Seamless Integration**: Compatible with existing symbolic execution engines

## Repository Structure

The repository is organized into four main components:

### [Training Data Generation](/Trainig-Data-Generation/)

Java component that generates input-output pairs from Java standard library methods:
- Uses reflection to dynamically invoke methods with random inputs
- Employs stratified sampling to ensure diverse inputs
- Generates datasets for 273 methods from Java's standard libraries

### [Symbolic Regression](/SymbolicRegression/)

Cython implementation of Grammar-Guided Genetic Programming:
- Implements a comprehensive set of operators from SMT-Lib standard
- Ensures type consistency through a custom typing system
- Uses tailored fitness functions for different output types (numeric, boolean, string)

### [Java Benchmark](/Java-Benchmark/)

Python scripts and Java classes for evaluating stub accuracy:
- Creates 10 test cases for each method (2730 total test cases)
- Each test verifies stub function behavior against original function
- Special design ensures robust testing by requiring multiple distinct outputs


## Getting Started

### Prerequisites

- Java JDK 11 or higher
- Python 3.7 or higher with pandas, tqdm
- Cython
- DEAP (Python library for evolutionary algorithms)

### Building and Running

#### 1. Training Data Generation

Generate input-output pairs for Java methods:

```bash
cd Trainig-Data-Generation
./gradlew clean run
```

#### 2. Symbolic Regression

Generate symbolic expressions from training data:

```bash
cd SymbolicRegression
./compile.sh
python3 Main.pyx
```

#### 3. Java Code Benchmark

Create a Java Benchmark for all testcases using:

```bash
cd Java-Benchmark
python3 CreateBenchmark.py
```

## Dataset

The training dataset is available on Hugging Face:

<div style="text-align: center">
  <a href="https://huggingface.co/datasets/Felix6326727/AutoStub/" target="_blank">
    <img src="https://huggingface.co/datasets/huggingface/badges/resolve/main/dataset-on-hf-xl.svg" alt="Open in HuggingFace"/>
  </a>
</div>

The dataset contains:
- Input-output pairs for 284 Java standard library methods
- Approximately 2.84 million samples in total
- Coverage across various data types (boolean, numeric, string)

To download and use the dataset programmatically:

```python
from datasets import load_dataset

# Load the dataset
dataset = load_dataset("Felix6326727/AutoStub")

# Access a specific sample
sample = dataset["train"][0]
print(f"Method: {sample['method_name']}")
print(f"Input: {sample['input']}")
print(f"Output: {sample['output']}")
```

## Results

Our evaluation demonstrates that AutoStub can:

- Approximate external functions with high accuracy (>90% for 55% of methods)
- Infer language-specific behaviors that reveal edge cases crucial for software testing
- Enable symbolic execution to explore previously intractable program paths

## Example

One notable example is the approximation of `Double.isNaN(double)`:

```
!(−1 < |x|)
```

This expression effectively captures the behavior that any comparison operation involving NaN returns false in Java, demonstrating how AutoStub can infer language-specific behavior without explicit knowledge of internal implementations.

## Citation

If you use AutoStub in your research, please cite our paper:

```bibtex
@inproceedings{maechtle2025autostub,
  title={AutoStub: Genetic Programming-Based Stub Creation for Symbolic Execution},
  author={Mächtle, Felix and Loose, Nils and Serr, Jan-Niclas and Sander, Jonas and Eisenbarth, Thomas},
  booktitle={Proceedings of the 18th ACM/IEEE International Workshop on Search-Based and Fuzz Testing, SBFT 2025},
  year={2025}
}
```

## License

This project is licensed under the cc-by-4.0 license.