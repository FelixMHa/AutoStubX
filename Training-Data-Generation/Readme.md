# Training Data Generation

This component of AutoStub generates input-output training data for Java standard library methods. The collected data is used by the Symbolic Regression component to derive expressions that approximate function behavior.

## Overview

The Training Data Generation module:
- Identifies suitable methods in Java standard libraries
- Uses reflection to dynamically invoke methods with random inputs
- Collects input-output pairs for each method
- Applies stratified sampling to ensure diverse inputs
- Generates approximately 10,000 samples per method

## Files

- `src/main/java/org/example/Main.java`: Entry point for the training data generation process
- `src/main/java/org/example/GenerateTrainingDataPerClass.java`: Core logic for generating training data
- `src/main/java/org/example/RandomDataProvider.java`: Generates diverse inputs for different types
- `src/main/java/org/example/JavaFunctionExport.java`: Exports method metadata
- `java_classes.json`: List of Java classes to analyze
- `methods_in_scope.json`: Output mapping of viable methods

## Method Selection Criteria

To be eligible for training data generation, methods must:
- Return a primitive type or String
- Accept only primitive types or Strings as parameters
- Not have side effects on the caller
- Not throw errors during random input generation

## Input Generation Strategy

The system employs a stratified sampling approach tailored for different data types:

- **Integer types** (byte, short, int, long): 
  - Randomly selects bit-length within the allowed range
  - Generates numbers across different magnitudes

- **Floating-point types** (float, double):
  - Stratified selection of exponent and mantissa
  - Ensures coverage of different scales

- **Strings**:
  - Random sequences of characters with variable length

- **Booleans**:
  - Random true/false values

Special values (e.g., NaN, Infinity, MIN_VALUE, MAX_VALUE, 0, 1, -1) are included with 5% probability to ensure edge cases are represented.

## Building and Running

### Prerequisites
- Java JDK 11 or higher
- Gradle

### Setup Java Classes
1. Build the list of Java classes to analyze:
```bash
# Option 1: Use the provided java_classes.json

# Option 2: Generate a new list from Java documentation
# Visit: https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/lang/package-summary.html
# Run this in browser console to extract class names:
var jq = document.createElement('script');
jq.src = "https://ajax.googleapis.com/ajax/libs/jquery/3.5.1/jquery.min.js";
document.getElementsByTagName('head')[0].appendChild(jq);
# After jQuery loads:
JSON.stringify($('#class-summary .class-summary.class-summary-tab2 a').toArray().map(x => $(x)).filter($x => $x.attr('title')).filter($x => $x.attr('title').startsWith('class in')).map($x => $x.attr('title').substring(9) + '.' + $x.text()));
```

2. Save the output to `java_classes.json`

### Generate Training Data
```bash
./gradlew clean run
```

For extended dataset generation (100x more samples), set `EXTENDED = true` in `Main.java`.

## Output

The training data is stored in the `symbolic-regression-data/training/` directory:
- Each method has its own JSON file
- Each file contains approximately 10,000 input-output pairs
- The filename format encodes the method signature

Additionally, `methods_in_scope.json` is generated containing metadata about all successfully processed methods.

## Performance

- Generating 10,000 samples takes an average of 13ms per method
- The system successfully processes 273 methods from Java standard libraries

## Statistics

After execution, the program prints statistics including:
- Total classes processed
- Total methods found
- Methods in scope (meeting selection criteria)
- Average generation time per method
- Data diversity across different types