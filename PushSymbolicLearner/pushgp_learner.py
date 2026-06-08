#!/usr/bin/env python3
"""
PushGP Implementation for Data Structure Method Learning

This fixes the issues from the initial implementation and provides a more
robust PushGP system specifically designed for learning Java method approximations.
"""
from pushbase import *
from trainingexample import TrainingExample
import random
import copy
import os
from itertools import zip_longest
import math
import difflib
from collections import defaultdict

from concurrent.futures import ProcessPoolExecutor
try:
    import Levenshtein
    _levenshtein = lambda a, b: Levenshtein.distance(a, b)
except Exception:
    _levenshtein = None

GLOBAL_TRAINING_DATA = None
GLOBAL_INTERPRETER = None
EPS = 1e-9
def init_worker(training_data, interpreter):
    """Initialize worker process with shared data"""
    global GLOBAL_TRAINING_DATA, GLOBAL_INTERPRETER
    GLOBAL_TRAINING_DATA = training_data
    GLOBAL_INTERPRETER = interpreter   



def _validate_evolution_params(training_data: List[TrainingExample], population_size: int, generations: int):
    """Validate evolution parameters"""
    if not training_data:
        raise ValueError("Training data cannot be empty")
    if generations <= 0:
        raise ValueError("Number of generations must be greater than 0")
    if population_size <= 0:
        raise ValueError("Population size must be greater than 0")

def _extract_method_names(training_data: List[TrainingExample]) -> List[str]:
    """Extract unique method names from training data"""
    method_names = set()
    for example in training_data:
        for call_str in example.sequence:
            method_name = call_str
            method_names.add(method_name)
    return list(method_names)


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

def run_pushgp_evolution(training_data: List[TrainingExample],
                        population_size: int = 100,
                        generations: int = 300,
                        no_improve_generations: int = 100,
                        profile: str = 'primitives_full',
                        processes: Optional[int] = None,
                        log_every: int = 25,
                        max_steps: Optional[int] = None) -> Optional[PushGPGenome]:
    
    _validate_evolution_params(training_data, population_size, generations)
    
    if processes is None:
        processes = min(population_size, os.cpu_count() or 2)
    if max_steps is None:
        max_steps = 80
    
    interpreter = PushGPInterpreter(profile=profile, max_steps=max_steps)
    method_names = _extract_method_names(training_data)

    
    print(f"Learning PushGP programs for {len(method_names)} methods: {method_names}")
    

    population = []
    for _ in range(population_size):
        genome = PushGPGenome()
        for method_name in method_names:
            if random.random() < 0:  
                program_code = interpreter.create_smart_initial_program(method_name)
            else:
                program_code = interpreter.random_program(max_depth=2, max_length=10)
            
            program = PushProgram(program_code)
            genome.add_method(method_name, program)
        population.append(genome)
    
    best_genome = None
    best_fitness = float('inf')
    stall_count = 0
    with ProcessPoolExecutor(
        max_workers=max(1, min(processes, population_size)),
        initializer=init_worker,
        initargs=(training_data, interpreter)
    ) as executor:
        
        for generation in range(generations):
            # Parallel evaluation - only pass genome and threshold now
            early_threshold = best_fitness if best_genome else None
            
            population = list(executor.map(
                evaluate_wrapper,
                [(g, early_threshold) for g in population]
            ))
        
        
            if generation % 10 == 0 and generation > 0:
                population = maintain_diversity(population, training_data, interpreter)

            # Sort and track best
            population.sort(key=lambda x: x.fitness)

            if population[0].fitness < best_fitness:
                best_fitness = population[0].fitness
                best_genome = population[0].copy()
                stall_count = 0
            else:
                stall_count += 1

            # Progress logging
            if generation % log_every == 0:
                best = population[0]
                print(f"Gen {generation}: Fitness={best.fitness:.6f}, "
                      f"Acc={best.accuracy:.3f}, Complexity={best.complexity_penalty:.3f}")
                for method_name, program in best.methods.items():
                    print(f"  {method_name}: {serialize_program(program.code)}")

            # Early stopping
            if population[0].accuracy >= 0.99 and population[0].fitness < 0.02:
                print(f"Solution found at generation {generation}")
                break
            
            if stall_count >= no_improve_generations:
                print(f"Stopping after {no_improve_generations} gens without improvement")
                break

            
            new_population = []

            # Elitism (keep top 10%)
            elite_count = max(2, population_size // 10)
            new_population.extend([g.copy() for g in population[:elite_count]])

            # Generate offspring
            while len(new_population) < population_size:
                if random.random() < 0.5:  # Crossover
                    parent1 = tournament_selection(population, training_data, interpreter)
                    parent2 = tournament_selection(population, training_data, interpreter)
                    offspring = crossover_genomes(parent1, parent2)
                else:  # Clone + mutate
                    parent = tournament_selection(population, training_data, interpreter)
                    offspring = parent.copy()


                adaptive_mutate_genome(offspring, interpreter, generation, generations, stall_count)
                offspring.invalidate_signature()
                new_population.append(offspring)

            population = new_population
    
    return best_genome

def evaluate_wrapper(args):
    global GLOBAL_TRAINING_DATA, GLOBAL_INTERPRETER
    genome, early_threshold = args 
    return evaluate_genome(genome, GLOBAL_TRAINING_DATA, GLOBAL_INTERPRETER, early_stop_threshold=early_threshold)


def evaluate_state(pred, target):
    score = 0
    
    # Size difference
    score += abs(pred.size - target.size)
    
    # Key mismatch
    score += len(pred.keys.symmetric_difference(target.keys))
    
    # Field hash mismatch
    for k in target.keys:
        if pred.field_hashes.get(k) != target.field_hashes.get(k):
            score += 1
    
    return score

def evaluate_genome(genome: PushGPGenome, training_data, interpreter, early_stop_threshold: Optional[float] = None):
    total_error = 0.0
    total_examples = 0
    correct_predictions = 0
    case_errors: List[float] = []
    method_stats = defaultdict(lambda: {'correct': 0, 'total': 0, 'downstream_correct': 0, 'downstream_total': 0})
    abort_sum = None
    if early_stop_threshold is not None:
        abort_sum = early_stop_threshold * len(training_data)
    
    for example in training_data:
        try:
            predicted_outputs, used_inputs, state_after = interpreter.execute_sequence(genome, example)
            # Calculate per-call correctness
            call_correct = []
            for pred, exp in zip_longest(predicted_outputs, example.expected_outputs, fillvalue=None):
                is_correct = _rec_error(pred, exp) < 0.01
                call_correct.append(is_correct)
            
            # Update method stats
            for i, method_name in enumerate(example.sequence):
                is_correct = call_correct[i] if i < len(call_correct) else False
                
                # Direct accuracy
                method_stats[method_name]['correct'] += int(is_correct)
                method_stats[method_name]['total'] += 1
                
                # Downstream accuracy: if this call is correct, how many later calls are correct?
                if is_correct and i + 1 < len(call_correct):
                    downstream_calls = call_correct[i + 1:]
                    method_stats[method_name]['downstream_correct'] += sum(downstream_calls)
                    method_stats[method_name]['downstream_total'] += len(downstream_calls)
     
            genome_error = aggregate_genome_error(
                example.sequence, predicted_outputs, example.expected_outputs
            )
            
            # Penalties
            unused_pen = compute_arg_unused_penalty(example.sequence, used_inputs, example.input_args)
            fitness_error = min(1.0, genome_error + 0.1 * unused_pen)
            case_errors.append(fitness_error)
            total_error += fitness_error
            total_examples += 1
            
            if genome_error < 0.01:
                correct_predictions += 1
            else:
                pass
            # Early abort
            if abort_sum is not None and total_error > abort_sum:
                genome.fitness = 1e5
                genome.accuracy = correct_predictions / total_examples
                genome.complexity_penalty = genome.get_complexity_penalty()
                return genome
                
        except Exception:
            case_errors.append(1.0)
            total_error += 1
            total_examples += 1
            for method_name in example.sequence:
                method_stats[method_name]['total'] += 1
    
    base_fitness = total_error / total_examples if total_examples > 0 else 1.0
    complexity_penalty = genome.get_complexity_penalty()
    
 
    genome.fitness = base_fitness + 0.001 * complexity_penalty  
    genome.accuracy = correct_predictions / total_examples if total_examples > 0 else 0.0
    genome.complexity_penalty = complexity_penalty
    
    #method accuracies
    method_accuracies = {}
    for method_name, stats in method_stats.items():
        # Direct accuracy
        direct_acc = stats['correct'] / max(1, stats['total'])
        
        # Downstream accuracy (how enabling is this method?)
        if stats['downstream_total'] > 0:
            downstream_acc = stats['downstream_correct'] / stats['downstream_total']
        else:
            downstream_acc = direct_acc  # No downstream calls, use direct
        
        # Weighted combination: direct accuracy is primary, downstream is a bonus
        # This rewards methods that are both correct AND enable correct behavior
        combined_acc = 0.7 * direct_acc + 0.3 * downstream_acc
        method_accuracies[method_name] = combined_acc
    genome.method_accuracies = method_accuracies
    genome.case_errors = case_errors

    return genome


def lexicase_selection(population: List[PushGPGenome],
                       num_cases: int = 40) -> PushGPGenome:
    """
    Lexicase selection using pre-cached per-example errors — zero re-execution.
    Subsamples num_cases per call for speed; still gives full diversity benefit.
    """
    candidates = [g for g in population if len(g.case_errors) > 0]
    if not candidates:
        return random.choice(population)

    n_cases = len(candidates[0].case_errors)
    case_indices = random.sample(range(n_cases), min(num_cases, n_cases))

    for idx in case_indices:
        if len(candidates) == 1:
            break
        best = min(g.case_errors[idx] for g in candidates)
        candidates = [g for g in candidates if g.case_errors[idx] <= best + 1e-6]

    return random.choice(candidates)

def tournament_selection(population: List[PushGPGenome], tournament_size: int) -> PushGPGenome:
    """Tournament selection"""
    tournament = random.sample(population, min(tournament_size, len(population)))
    return min(tournament, key=lambda x: x.fitness)

def crossover_genomes(parent1: PushGPGenome, parent2: PushGPGenome) -> PushGPGenome:
    """ crossover"""
    offspring = PushGPGenome()
    
    all_methods = set(parent1.methods.keys()) | set(parent2.methods.keys())
    
    for method_name in all_methods:
        if method_name in parent1.methods and method_name in parent2.methods:
            # Choose better parent or crossover
            acc1 = parent1.method_accuracies.get(method_name, 0)
            acc2 = parent2.method_accuracies.get(method_name, 0)
            
            if random.random() < 0.8:  # favor crossover
                program1 = parent1.methods[method_name].code
                program2 = parent2.methods[method_name].code
                new_code = crossover_programs(program1, program2)
            else:
                new_code = parent1.methods[method_name].code if acc1 >= acc2 else parent2.methods[method_name].code
                new_code = copy.deepcopy(new_code)
        elif method_name in parent1.methods:
            new_code = copy.deepcopy(parent1.methods[method_name].code)
        else:
            new_code = copy.deepcopy(parent2.methods[method_name].code)
        
        offspring.add_method(method_name, PushProgram(new_code))
    
    return offspring

def crossover_programs(program1: List, program2: List) -> List:
    """ program crossover"""
    if not program1 or not program2:
        return program1 if program1 else program2
    
    # Multiple crossover strategies
    strategy = random.choice(['single_point', 'uniform', 'block'])
    
    if strategy == 'single_point':
        point1 = random.randint(0, len(program1))
        point2 = random.randint(0, len(program2))
        return program1[:point1] + program2[point2:]
    elif strategy == 'uniform':
        max_len = max(len(program1), len(program2))
        result = []
        for i in range(max_len):
            if i < len(program1) and i < len(program2):
                result.append(program1[i] if random.random() < 0.5 else program2[i])
            elif i < len(program1):
                result.append(program1[i])
            elif i < len(program2):
                result.append(program2[i])
        return result
    else:  # block
        # Take blocks from each parent
        mid1 = len(program1) // 2
        mid2 = len(program2) // 2
        return program1[:mid1] + program2[mid2:]

def adaptive_mutate_genome(genome: PushGPGenome, interpreter: PushGPInterpreter,
                          generation: int, max_generations: int, stall_count: int,
                          base_rate: float = 0.4):
    """genome mutation"""
    # High early exploration, low late refinement
    progress = generation / max(1, max_generations)
    mutation_rate = base_rate * (1.0 - 0.5 * progress)  # Drops to 50% of base
    

    for method_name, program in genome.methods.items():
        if len(program.code) == 0:
                program.code = interpreter.random_program(max_depth=2, max_length=8)
                continue
        if random.random() < mutation_rate:
            # Choose mutation type based on program quality
            acc = genome.method_accuracies.get(method_name, 0.0)
            if stall_count >25 and acc > 0.5:
                # If stalled, increase mutation aggressiveness
                mutate_program_aggressive(program.code, interpreter)
                continue
            if acc < 0.4:
                # Poor performance: major changes
                mutate_program_aggressive(program.code, interpreter)
            elif acc < 0.98:
                # Medium performance: moderate changes
                mutate_program(program.code, interpreter, mutation_rate=0.4)
            else:
                # Good performance: minor tweaks only
                if random.random()<0.5:
                    mutate_program_conservative(program.code, interpreter)
                else:
                    mutate_program(program.code, interpreter, mutation_rate=0.2)

def mutate_program_aggressive(program: List, interpreter: PushGPInterpreter):
    """Aggressive mutation for poor performers"""
    # Replace large chunks
    if random.random() < 0.5:
        replacement = interpreter.random_program(max_depth=3, max_length=6)
        if len(program) > 2:
            start = random.randint(0, len(program) - 2)
            end = random.randint(start + 1, len(program))
            program[start:end] = replacement
        else:
            program[:] = replacement
    else:
        # Replace multiple random instructions
        for i in range(len(program)):
            if random.random() < 0.5:
                program[i] = random.choice(interpreter.instruction_list)

def mutate_program_conservative(program: List, interpreter: PushGPInterpreter):
    """Conservative mutation for good performers"""
    if not program:
        return
    
    mutation_type = random.choice(['swap', 'tweak_constant', 'insert'])
    
    if mutation_type == 'swap' and len(program) >= 2:
        # Swap two adjacent instructions
        i = random.randint(0, len(program) - 2)
        program[i], program[i+1] = program[i+1], program[i]
    
    elif mutation_type == 'tweak_constant':
        # Modify a constant slightly
        for i, instr in enumerate(program):
            if hasattr(instr, 'value') and type(instr.value) is int:
                if random.random() < 0.3:
                    delta = random.choice([-1, 0, 1])
                    new_val = instr.value + delta
                    if hasattr(instr, '__class__'):
                        program[i] = instr.__class__(new_val)
    
    elif mutation_type == 'insert' and len(program) < 10:
        # Insert single instruction
        pos = random.randint(0, len(program))
        program.insert(pos, random.choice(interpreter.instruction_list))

def mutate_program(program: List, interpreter: PushGPInterpreter, mutation_rate: float = 0.4):
    """ program mutation"""

    if len(program) == 0:
        if random.random() < 0.8:
            # Add several instructions
            num_to_add = random.randint(2, 5)
            for _ in range(num_to_add):
                program.append(interpreter._get_random_instruction())
        return
    def mutate_recursive(prog):
        for i, item in enumerate(prog):
            if random.random() < mutation_rate:
                if isinstance(item, list):
                    if random.random() < 0.5:
                        mutate_recursive(item)
                    else:
                        # Replace with single instruction
                        prog[i] = random.choice(interpreter.instruction_list)
                else:
                    if random.random() < 0.7:
                        # Replace with random instruction
                        prog[i] = random.choice(interpreter.instruction_list)
                    else:
                        # Replace with small subprogram
                        subprog = interpreter.random_program(max_depth=2, max_length=4)
                        prog[i] = subprog
            elif isinstance(item, list):
                mutate_recursive(item)
    
    # Structural mutations
    if random.random() < mutation_rate:
        if len(program) > 1 and random.random() < 0.6:
            # Remove instruction
            program.pop(random.randint(0, len(program) - 1))
        elif len(program) < 8 and random.random() < 0.5:
            # Add instruction
            pos = random.randint(0, len(program))
            program.insert(pos, random.choice(interpreter.instruction_list))
    
    mutate_recursive(program)

def _calculate_behavioral_signature(genome: PushGPGenome,
                                    training_data: List[TrainingExample],
                                    interpreter: PushGPInterpreter,
                                    sample_size: int = 5) -> tuple:
    """Create behavioral signature for diversity measurement. Cached on genome."""
    if genome._behavioral_signature is not None:
        return genome._behavioral_signature

    signature = []
    samples = random.sample(training_data, min(sample_size, len(training_data)))

    for example in samples:
        try:
            predicted, _ = interpreter.execute_sequence(genome, example)
            sig = tuple(str(p) for p in predicted)
            signature.append(sig)
        except:
            signature.append(None)

    genome._behavioral_signature = tuple(signature)
    return genome._behavioral_signature


def maintain_diversity(population: List[PushGPGenome],
                      training_data: List[TrainingExample],
                      interpreter: PushGPInterpreter,
                      diversity_threshold: float = 0.3) -> List[PushGPGenome]:
    """Ensure population maintains behavioral diversity"""
    if len(population) < 10:
        return population
    
    # Calculate signatures
    signatures = [_calculate_behavioral_signature(g, training_data, interpreter) 
                  for g in population]
    
    # Keep diverse individuals
    diverse_pop = [population[0]]  # Keep best
    diverse_sigs = [signatures[0]]
    
    for genome, sig in zip(population[1:], signatures[1:]):
        # Check if sufficiently different from existing
        is_diverse = True
        for existing_sig in diverse_sigs:
            similarity = sum(1 for a, b in zip(sig, existing_sig) if a == b) / len(sig)
            if similarity > (1 - diversity_threshold):
                is_diverse = False
                break
        
        if is_diverse:
            diverse_pop.append(genome)
            diverse_sigs.append(sig)
        elif len(diverse_pop) < len(population) * 0.5:
            # Still accept some similar ones to maintain population size
            diverse_pop.append(genome)
            diverse_sigs.append(sig)
    
    return diverse_pop


def _string_error(a: str, b: str) -> float:
    if a == b:
        return 0.0
    if _levenshtein:
        dist = _levenshtein(a, b)
        denom = max(len(a), len(b), 1)
        return min(dist / denom, 1.0)
    # fallback: difflib ratio -> distance
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    return 1.0 - ratio

def _numeric_error(pred: float, exp: float) -> float:
    if math.isclose(pred, exp, rel_tol=1e-9, abs_tol=EPS):
        return 0.0
    denom = max(abs(exp), 1.0)
    return min(abs(pred - exp) / denom, 1.0)

def _rec_error(pred: Any, exp: Any) -> float:
    # None handling
    if pred is None and exp is None:
        return 0.0
    if pred is None or exp is None:
        return 1.0
    def is_number(x):
        return isinstance(x, (int, float)) and not isinstance(x, bool)
    # Type mismatch -> full penalty except numeric cross-types
    if type(pred) != type(exp):
        if is_number(pred) and is_number(exp):
            pass
        else:
            return 1.0

    # Booleans: exact
    if isinstance(exp, bool):
        return 0.0 if pred == exp else 1.0

    # Numbers
    if isinstance(exp, (int, float)) and isinstance(pred, (int, float)):
        return _numeric_error(float(pred), float(exp))

    # Strings
    if isinstance(exp, str) and isinstance(pred, str):
        return _string_error(pred, exp)


    # Fallback to exact string equality
    try:
        return 0.0 if pred == exp else 1.0
    except Exception:
        return 1.0

def calculate_per_call_errors(sequence: List[str], predicted: List[Any], expected: List[Any]) -> List[float]:
    """Return list of per-call errors aligned to 'sequence' length (zip_longest)."""
    errs = []
    for _, p, e in zip_longest(sequence, predicted, expected, fillvalue=None):
        errs.append(_rec_error(p, e))
    return errs


def aggregate_genome_error(sequence: List[str],
                           predicted: List[Any],
                           expected: List[Any]) -> float:
    if not sequence:
        return 0.0

    per_call = calculate_per_call_errors(sequence, predicted, expected)
    
    # Exponential penalty for errors
    exp_errors = [err ** 0.5 for err in per_call]  # sqrt makes small errors less costly
    
    # Group by method name
    grouped = defaultdict(list)
    for name, err in zip(sequence, exp_errors):
        grouped[name].append(err)
    
    # Average per method
    method_errors = [sum(errs)/len(errs) for errs in grouped.values()]
    # Weight recent errors more heavily (they depend on earlier correctness)
    weights = [1.0 + i * 0.1 for i in range(len(method_errors))]
    total_w = sum(weights)
    weighted_mean = sum(e * w for e, w in zip(method_errors, weights)) / total_w
    
    return float(max(0.0, min(1.0, weighted_mean)))




def compute_arg_unused_penalty(sequence: List[str], used_inputs: List[bool], input_args: List[List[Any]]) -> float:
    """Penalize calls that ignore all of their input arguments.
    Returns value in [0..1]. Weight applied per unused call.
    """
    if not sequence or not used_inputs:
        return 0.0
    # weight controls strength of penalty per unused call
    weight = 0.3
    misses = 0
    total = 0
    for used, args in zip_longest(used_inputs, input_args, fillvalue=[]):
        if args:  # only penalize when arguments exist
            total += 1
            if not used:
                misses += 1
    if total == 0 or misses == 0:
        return 0.0
    return min(1.0, weight * misses / max(1, len(sequence)))


