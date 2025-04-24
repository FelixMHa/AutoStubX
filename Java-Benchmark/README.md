# Java Benchmark

This component of AutoStub creates and evaluates benchmark programs to assess the accuracy of the generated symbolic stubs in real Java applications.

## Overview

The Java Benchmark consists of:
- 10 test cases per Java method (273 methods × 10 = 2730 test cases)
- Each test verifies that the stub function correctly models the original function behavior
- Special design to avoid trivial solutions by requiring two distinct outputs

## Files

- `CreateBenchmark.py`: Generates benchmark programs for evaluating stubs
- `Helper.py`: Utility functions for benchmark generation

## Creating Benchmarks

Run the following command to generate the benchmark:

```bash
python3 CreateBenchmark.py
```

This will:
1. Create the `java-benchmark` directory with subdirectories for each Java class
2. Generate 10 Java test cases for each method that meets specific criteria
3. Compile all Java test cases
4. Create a `sample.json` file for each method containing test inputs and expected outputs


## Benchmark Structure

Each benchmark program follows this template:
1. Parse input arguments
2. Execute the target method with the provided inputs
3. Compare the output to expected values
4. Report success or failure

## Design Principles

The benchmarks are specifically designed to:
- Test method behavior with diverse inputs
- Ensure each method returns two different outputs for different inputs (avoiding trivial solutions)
- Provide coverage across various primitive types and String operations
- Be compatible with symbolic execution engines

## Requirements

- Python 3.7+
- Java JDK 11+