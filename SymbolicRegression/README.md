# Symbolic Regression

This component is the core of AutoStub, implementing Grammar-Guided Genetic Programming (G3P) to generate symbolic expressions that approximate the behavior of Java methods.

## Overview

Symbolic Regression uses evolutionary computation to discover mathematical expressions that best fit input-output training data. Key features include:

- Type-aware genetic programming that respects Java's type system
- Comprehensive set of operators matching SMT-Lib standards
- Efficient fitness evaluation for different output types (numeric, boolean, string)
- Parallelized computation for faster expression discovery

## Files

- `Main.pyx`: Entry point that orchestrates the symbolic regression process
- `GeneticAlgorithm.pyx`: Core implementation of the genetic algorithm
- `CustomFunctions.pyx`: Implementations of operators used in expressions
- `DummyTypes.pyx`: Type system that ensures type consistency
- `compile.sh`: Compilation script for Cython components
- `clean.sh`: Script to clean compiled files
- `setup.py`: Python setup file for Cython compilation

## Operators

The symbolic expressions are built from a subset of SMT-Lib standard operators, including:

### Numeric Operators
- Arithmetic: Addition, subtraction, multiplication, division
- Comparison: Less than, equality
- Functions: Absolute value, floor

### String Operators
- Manipulation: Concatenation, substring, replace
- Analysis: Length, contains, index of
- Conversion: String to int/float, int/float to string

### Boolean Operators
- Logical: And, or, not, xor
- Conditional: If-then-else for various types

### Type Conversion
- Between all supported types (int, float, boolean, string)

## Building

To compile the Cython code:

```bash
./compile.sh
```

This will generate optimized C code from the Cython source and compile it into Python extension modules.

## Running

To run the symbolic regression:

```bash
python3 Main.pyx
```

By default, this will:
1. Load training data from `../Trainig-Data-Generation/symbolic-regression-data/training/`
2. Run the genetic algorithm in parallel using all available CPU cores
3. Save the best expressions to `../Trainig-Data-Generation/symbolic-regression-data/formulas/`

## Customization

The genetic algorithm can be customized with the following parameters:

- Population size (default: 5000)
- Number of iterations (default: 100)
- Timeout duration (default: 15 minutes per function)
- Mutation rate
- Selection algorithm (tournament selection by default)

## How It Works

1. **Input Processing**: Training data is loaded and preprocessed
2. **Primitive Set Setup**: Type-specific operators are registered based on input/output types
3. **Evolution**: Population evolves through selection, crossover, and mutation
4. **Fitness Evaluation**:
   - Numeric outputs: Normalized Root Mean Squared Error (NRMSE)
   - Boolean outputs: Classification accuracy
   - String outputs: Levenshtein distance
5. **Result Selection**: The best-performing expression is selected and formatted

## Requirements

- Python 3.7+
- Cython
- DEAP (Distributed Evolutionary Algorithms in Python)
- NumPy
- python-Levenshtein

## Performance Considerations

- Large expressions can be computationally expensive
- A caching mechanism is implemented to avoid redundant evaluations
- The search space is restricted to expressions of reasonable complexity
- Early stopping is implemented when suitable expressions are found