# AutoStubX: AutoStub for Complex Data Types

AutoStubX is an extension of AutoStub to automatically generate symbolic stubs for not only stateless functions but stateful ones too. 

## Overview

Symbolic execution faces significant limitations when encountering external functions that cannot be symbolically analyzed. AutoStubX addresses this challenge through a three-step process:

1. **Training Data Generation**: When encountering an external function, AutoStub collects input-output pairs by executing the function with diverse inputs
2. **Symbolic Expression Synthesis**: PushGP derives expressions that approximate function behavior

## Key Features

- **Automatic Stub Generation**: No manual intervention required
- **Type-Aware Expressions**: Supports multiple data types including primitives and strings and collections
- **Language-Specific Behavior**: Infers edge cases essential for testing
- **Seamless Integration**: Compatible with existing symbolic execution engines

## Repository Structure

The repository is organized into two main components:

### [Training Data Generation](/Training-Data-Generation/)

Java component that generates sequenecs of input-output pairs from Java standard library methods:
- Uses reflection to dynamically invoke methods with random inputs
- Employs stratified sampling to ensure diverse inputs

### [Symbolic Regression](/PushSymbolicLearner/)

Cython implementation of Grammar-Guided Genetic Programming:
- Implements a comprehensive set of operators from SMT-Lib standard
- Ensures type consistency through a custom typing system
- Uses tailored fitness functions for different output types (numeric, boolean, string)



## Getting Started

### Prerequisites

- Java JDK 11 or higher
- Python 3.7 or higher

### Building and Running

#### 1. Training Data Generation

Generate sequences with input-output pairs for Java methods:

```bash
cd Trainig-Data-Generation
./gradlew clean run
```

#### 2. PushGP Learner

Generate Push programs from training data:

```bash
cd PushSymbolicLearner
python3 runAll.py
```


## Results

Our evaluation demonstrates that AutoStubX can:

- Approximate external functions with high accuracy
- Infer language-specific behaviors that reveal edge cases crucial for software testing
- Enable symbolic execution to explore previously intractable program paths




## License

This project is licensed under the cc-by-4.0 license.
