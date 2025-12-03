from typing import List
import json
from pathlib import Path
from pushgp_learner import run_pushgp_evolution, TrainingExample
import argparse
import time

def loadtrainingdata(data_directory: str, max_samples_per_file: int = 1000, file_pattern: str = "*.json") -> List[TrainingExample]:

    data_path = Path(data_directory)
    if not data_path.exists():
        raise FileNotFoundError(f"Data not found: {data_directory}")
    
    
    training_examples = []
    file_count = 0
    total_samples = 0
    
    print(f"Loading training data from {data_directory}")
    print(f"Max samples per file: {max_samples_per_file}")
    print("-" * 60)
    
    if not data_path.is_dir():
        json_files = [data_path]
    else:
        json_files = sorted(data_path.glob(file_pattern))
    # Process all matching JSON files
    for json_file in json_files:
        print(f"Loading {json_file.name}...", end=" ")
        
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            # Handle both single objects and arrays
            if isinstance(data, dict):
                data = [data]
            
            # Limit samples per file to manage memory
            if len(data) > max_samples_per_file:
                print(f"(limiting to {max_samples_per_file} of {len(data)} samples)")
                # Sample evenly across the dataset
                step = len(data) // max_samples_per_file
                data = data[::step][:max_samples_per_file]
            else:
                print(f"({len(data)} samples)")
            
            # Infer method name and data structure type from filename
            ds_type = infer_type_from_filename(json_file.name)
            
            # Convert to TrainingExample objects
            file_examples = []
            for item in data:
                example = TrainingExample(
                    sequence=item.get('sequence', []),
                    input_args=item.get('input', []),
                    expected_outputs=item.get('output', []),
                    type_inputs=item.get('typeInput', []),
                    type_outputs=item.get('typeOutput', []),
                    data_structure_type=ds_type
                )
                if example.expected_outputs != "error":
                    file_examples.append(example)
            
            training_examples.extend(file_examples)
            file_count += 1
            total_samples += len(file_examples)
            
        except Exception as e:
            print(f"ERROR loading {json_file.name}: {e}")
            continue
    
    print("-" * 60)
    print(f"Loaded {total_samples} total samples from {file_count} files")
    
    
    return training_examples

def save_genome(genome, output_file: str):
    """Save the best genome to a JSON file."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(genome, f, indent=4)

    print(f"Genome saved to {output_file}")

def save_genome(genome, output_path: str):
    """Save improved PushGP genome"""
    
    def serialize_program(code):
        """Convert program to serializable format"""
        result = []
        for item in code:
            if hasattr(item, 'name'):  # PushInstruction
                result.append(item.name)
            elif isinstance(item, list):
                result.append(serialize_program(item))
            else:
                result.append(str(item))
        return result
    
    genome_data = {
        'fitness': genome.fitness,
        'accuracy': genome.accuracy,
        'complexity_penalty': genome.complexity_penalty,
        'method_accuracies': genome.method_accuracies,
        'methods': {}
    }
    
    for method_name, program in genome.methods.items():
        genome_data['methods'][method_name] = {
            'program': serialize_program(program.code),
            'accuracy': genome.method_accuracies.get(method_name, 0.0),
            'complexity': genome._count_instructions(program.code),
        }
    
    with open(output_path, 'w') as f:
        json.dump(genome_data, f, indent=2)
    
    print(f"PushGP genome saved to: {output_path}")

def infer_type_from_filename(filename: str) -> str:
    """
    Infer data structure type from filename
    """
    filename_lower = filename.lower().replace('.json', '')
    
    # Infer data structure type
    ds_type = "list"  # default
    if any(part in filename_lower for part in ['hashmap', 'treemap', 'map']):
        ds_type = "map"
    elif any(part in filename_lower for part in ['stack']):
        ds_type = "stack"
    elif any(part in filename_lower for part in ['queue']):
        ds_type = "queue"
    elif any(part in filename_lower for part in ['set', 'hashset', 'treeset']):
        ds_type = "set"
    elif any(part in filename_lower for part in ['linkedlist']):
        ds_type = "list"  # LinkedList is still list-like
    elif any(part in filename_lower for part in ['arraylist', 'list']):
        ds_type = "list"
    
    
    return ds_type

    
def main():
    parser = argparse.ArgumentParser(description="PushGP for data structure learning")
    parser.add_argument("data_directory", help="JSON file with training data")
    parser.add_argument("--population", type=int, default=200,
                       help="Population size for evolution")
    parser.add_argument("--generations", type=int, default=200,
                       help="Number of generations")
    parser.add_argument("--output", default="pushgp_genome.json",
                       help="Output file for learned genome")
    parser.add_argument("--test-examples", type=int, default=15,
                       help="Number of examples to test on")
    parser.add_argument("--profile", type=str, default="primitives_full",
                       help="Number of examples to test on")
    
    args = parser.parse_args()

    start_time = time.time()
    best_genome = run_pushgp_evolution(
        training_data = loadtrainingdata(args.data_directory, 10000), 
        population_size=args.population,
        generations=args.generations,
        profile=args.profile
    )
    evolution_time = time.time() - start_time
    print(f"Evolution completed in {evolution_time:.2f} seconds")

    save_genome(best_genome, args.output)
    print(f"Best genome saved to {args.output}")
if __name__ == "__main__":
    main()