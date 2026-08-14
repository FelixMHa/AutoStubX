#!/usr/bin/env python3
"""Evolutionary learner for sequence-based PushGP Java method models.

The public function names from the original module are retained. The
implementation is compatible with the revised ``pushbase.py`` and treats a full
method-call sequence as one fitness case while preserving per-call errors for
lexicase selection.
"""
from __future__ import annotations

import copy
import difflib
import math
import os
import random
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from itertools import zip_longest
from statistics import median
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, TYPE_CHECKING

# Keep the original module's accidental re-export of pushbase symbols so code that
# imports PushProgram/PushGPGenome from pushgp_learner continues to work.
from pushbase import *  # noqa: F401,F403

if TYPE_CHECKING:
    from trainingexample import TrainingExample
else:
    try:
        from trainingexample import TrainingExample
    except ImportError:
        # TrainingExample is only required structurally by this module. Keeping the
        # import optional also avoids circular-import failures in small tools/tests.
        TrainingExample = Any

try:
    import Levenshtein
except ImportError:
    Levenshtein = None


EPS = 1e-9
DEFAULT_TOURNAMENT_SIZE = 5
DEFAULT_MAX_PROGRAM_ATOMS = 64
DEFAULT_MAX_PROGRAM_DEPTH = 6

GLOBAL_TRAINING_DATA: Optional[List[Any]] = None
GLOBAL_INTERPRETER: Optional[PushGPInterpreter] = None
GLOBAL_EVALUATION_CONFIG: Optional["EvaluationConfig"] = None


@dataclass(frozen=True)
class EvaluationConfig:
    """Weights and tolerances used by ``evaluate_genome``."""

    complexity_weight: float = 0.001
    argument_use_weight: float = 0.1
    state_weight: float = 0.1
    correctness_tolerance: float = 0.01

    def __post_init__(self) -> None:
        for name in ("complexity_weight", "argument_use_weight", "state_weight"):
            value = getattr(self, name)
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be a finite non-negative number")
        if not math.isfinite(self.correctness_tolerance) or self.correctness_tolerance < 0.0:
            raise ValueError("correctness_tolerance must be finite and non-negative")


def init_worker(
    training_data: List[Any],
    interpreter: PushGPInterpreter,
    evaluation_config: Optional[EvaluationConfig] = None,
) -> None:
    """Initialize one worker process with immutable evaluation inputs."""
    global GLOBAL_TRAINING_DATA, GLOBAL_INTERPRETER, GLOBAL_EVALUATION_CONFIG
    GLOBAL_TRAINING_DATA = training_data
    GLOBAL_INTERPRETER = interpreter
    GLOBAL_EVALUATION_CONFIG = evaluation_config or EvaluationConfig()


def _validate_evolution_params(
    training_data: Sequence[Any],
    population_size: int,
    generations: int,
    *,
    no_improve_generations: Optional[int] = None,
    processes: Optional[int] = None,
    log_every: Optional[int] = None,
    smart_initialization_probability: float = 0.2,
    crossover_rate: float = 0.5,
    elite_fraction: float = 0.1,
) -> None:
    """Validate the public evolution parameters before allocating a population."""
    if not training_data:
        raise ValueError("Training data cannot be empty")
    if isinstance(population_size, bool) or population_size <= 0:
        raise ValueError("Population size must be greater than 0")
    if isinstance(generations, bool) or generations <= 0:
        raise ValueError("Number of generations must be greater than 0")
    if no_improve_generations is not None and no_improve_generations <= 0:
        raise ValueError("no_improve_generations must be positive or None")
    if processes is not None and processes <= 0:
        raise ValueError("processes must be positive or None")
    if log_every is not None and log_every <= 0:
        raise ValueError("log_every must be positive or None")
    for name, value in (
        ("smart_initialization_probability", smart_initialization_probability),
        ("crossover_rate", crossover_rate),
        ("elite_fraction", elite_fraction),
    ):
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must be in [0, 1]")


def _extract_method_names(training_data: Sequence[Any]) -> List[str]:
    """Extract unique method names in deterministic first-seen order."""
    seen: set[str] = set()
    method_names: List[str] = []
    for example in training_data:
        for raw_name in list(getattr(example, "sequence", None) or []):
            name = str(raw_name)
            if name not in seen:
                seen.add(name)
                method_names.append(name)
    return method_names


def serialize_program(code: Iterable[Any]) -> List[Any]:
    """Convert a Push program to a JSON-friendly nested representation."""
    result: List[Any] = []
    for item in code or []:
        if hasattr(item, "name"):
            result.append(str(item.name))
        elif isinstance(item, (list, tuple)):
            result.append(serialize_program(item))
        elif item is None or isinstance(item, (bool, int, float, str)):
            result.append(item)
        else:
            result.append(repr(item))
    return result


def _reset_genome_evaluation(genome: PushGPGenome) -> None:
    """Invalidate cached fitness after crossover or mutation."""
    genome.fitness = float("inf")
    genome.accuracy = 0.0
    genome.method_accuracies = {}
    genome.complexity_penalty = 0.0
    genome.case_errors = []
    genome.invalidate_signature()


def _select_parent(
    population: List[PushGPGenome],
    *,
    selection: str,
    tournament_size: int,
    lexicase_cases: int,
) -> PushGPGenome:
    selection_key = (selection or "tournament").strip().lower()
    if selection_key in {"lexicase", "exact_lexicase"}:
        return lexicase_selection(population, num_cases=lexicase_cases, epsilon=1e-6)
    if selection_key in {"epsilon_lexicase", "epsilon-lexicase", "eplexicase"}:
        return lexicase_selection(population, num_cases=lexicase_cases, epsilon=None)
    if selection_key != "tournament":
        raise ValueError(
            "selection must be 'tournament', 'lexicase', or 'epsilon_lexicase'"
        )
    return tournament_selection(population, tournament_size)


def _evaluate_population_serial(
    population: List[PushGPGenome],
    training_data: List[Any],
    interpreter: PushGPInterpreter,
    early_threshold: Optional[float],
    evaluation_config: EvaluationConfig,
) -> List[PushGPGenome]:
    return [
        evaluate_genome(
            genome,
            training_data,
            interpreter,
            early_stop_threshold=early_threshold,
            evaluation_config=evaluation_config,
        )
        for genome in population
    ]


def run_pushgp_evolution(
    training_data: List[TrainingExample],
    population_size: int = 100,
    generations: int = 300,
    no_improve_generations: Optional[int] = 100,
    profile: str = "primitives_full",
    processes: Optional[int] = None,
    log_every: Optional[int] = 25,
    max_steps: Optional[int] = None,
    *,
    random_seed: Optional[int] = None,
    smart_initialization_probability: float = 0.2,
    selection: str = "tournament",
    tournament_size: int = DEFAULT_TOURNAMENT_SIZE,
    lexicase_cases: int = 40,
    crossover_rate: float = 0.5,
    elite_fraction: float = 0.1,
    diversity_interval: Optional[int] = 10,
    diversity_threshold: float = 0.3,
    base_mutation_rate: float = 0.4,
    max_program_atoms: int = DEFAULT_MAX_PROGRAM_ATOMS,
    max_program_depth: int = DEFAULT_MAX_PROGRAM_DEPTH,
    evaluation_config: Optional[EvaluationConfig] = None,
    parallel_fallback: bool = True,
) -> Optional[PushGPGenome]:
    """Evolve one Push program per method name found in the training traces.

    The original positional arguments remain valid. New controls are keyword-only.
    Set ``processes=1`` for deterministic in-process debugging.
    """
    training_data = list(training_data or [])
    if processes is None:
        processes = min(population_size, os.cpu_count() or 2)
    if max_steps is None:
        max_steps = 80
    if tournament_size <= 0:
        raise ValueError("tournament_size must be positive")
    if lexicase_cases <= 0:
        raise ValueError("lexicase_cases must be positive")
    if diversity_interval is not None and diversity_interval <= 0:
        raise ValueError("diversity_interval must be positive or None")
    if not 0.0 <= diversity_threshold <= 1.0:
        raise ValueError("diversity_threshold must be in [0, 1]")
    if not 0.0 <= base_mutation_rate <= 1.0:
        raise ValueError("base_mutation_rate must be in [0, 1]")
    if max_program_atoms <= 0 or max_program_depth <= 0:
        raise ValueError("program size and depth limits must be positive")
    selection_key = (selection or "tournament").strip().lower()
    if selection_key not in {
        "tournament",
        "lexicase",
        "exact_lexicase",
        "epsilon_lexicase",
        "epsilon-lexicase",
        "eplexicase",
    }:
        raise ValueError(
            "selection must be 'tournament', 'lexicase', or 'epsilon_lexicase'"
        )

    _validate_evolution_params(
        training_data,
        population_size,
        generations,
        no_improve_generations=no_improve_generations,
        processes=processes,
        log_every=log_every,
        smart_initialization_probability=smart_initialization_probability,
        crossover_rate=crossover_rate,
        elite_fraction=elite_fraction,
    )

    if random_seed is not None:
        random.seed(random_seed)

    evaluation_config = evaluation_config or EvaluationConfig()
    interpreter = PushGPInterpreter(profile=profile, max_steps=max_steps)
    method_names = _extract_method_names(training_data)
    if not method_names:
        raise ValueError("Training data contains no method calls")

    print(f"Learning PushGP programs for {len(method_names)} methods: {method_names}")

    population: List[PushGPGenome] = []
    for _ in range(population_size):
        genome = PushGPGenome()
        for method_name in method_names:
            if random.random() < smart_initialization_probability:
                program_code = interpreter.create_smart_initial_program(method_name)
            else:
                program_code = interpreter.random_program(max_depth=2, max_length=10)
            genome.add_method(
                method_name,
                PushProgram(_bounded_program_copy(program_code, max_program_atoms, max_program_depth)),
            )
        population.append(genome)

    best_genome: Optional[PushGPGenome] = None
    best_fitness = float("inf")
    stall_count = 0
    executor: Optional[ProcessPoolExecutor] = None
    use_parallel = processes > 1

    if use_parallel:
        try:
            executor = ProcessPoolExecutor(
                max_workers=min(processes, population_size),
                initializer=init_worker,
                initargs=(training_data, interpreter, evaluation_config),
            )
        except Exception as exc:
            if not parallel_fallback:
                raise
            print(
                "Could not initialize parallel evaluation; continuing serially: "
                f"{type(exc).__name__}: {exc}"
            )
            executor = None

    try:
        for generation in range(generations):
            # Exact per-case errors are required for lexicase; do not truncate them.
            selection_key = (selection or "tournament").strip().lower()
            supports_early_abort = "lexicase" not in selection_key
            early_threshold = (
                best_fitness
                if supports_early_abort and best_genome is not None and math.isfinite(best_fitness)
                else None
            )

            if executor is not None:
                try:
                    population = list(
                        executor.map(
                            evaluate_wrapper,
                            [(genome, early_threshold) for genome in population],
                        )
                    )
                except Exception as exc:
                    if not parallel_fallback:
                        raise
                    print(
                        "Parallel evaluation failed; continuing serially: "
                        f"{type(exc).__name__}: {exc}"
                    )
                    executor.shutdown(wait=True)
                    executor = None
                    population = _evaluate_population_serial(
                        population,
                        training_data,
                        interpreter,
                        early_threshold,
                        evaluation_config,
                    )
            else:
                population = _evaluate_population_serial(
                    population,
                    training_data,
                    interpreter,
                    early_threshold,
                    evaluation_config,
                )

            population.sort(key=lambda genome: genome.fitness)
            generation_best = population[0]

            if generation_best.fitness + EPS < best_fitness:
                best_fitness = generation_best.fitness
                best_genome = generation_best.copy()
                stall_count = 0
            else:
                stall_count += 1

            if log_every is not None and generation % log_every == 0:
                print(
                    f"Gen {generation}: Fitness={generation_best.fitness:.6f}, "
                    f"Acc={generation_best.accuracy:.3f}, "
                    f"Complexity={generation_best.complexity_penalty:.3f}"
                )
                for method_name, program in generation_best.methods.items():
                    print(f"  {method_name}: {serialize_program(program.code)}")

            if generation_best.accuracy >= 0.99 and generation_best.fitness < 0.02:
                print(f"Solution found at generation {generation}")
                break
            if (
                no_improve_generations is not None
                and stall_count >= no_improve_generations
            ):
                print(
                    f"Stopping after {no_improve_generations} generations "
                    "without improvement"
                )
                break

            reproduction_pool = population
            if (
                diversity_interval is not None
                and generation > 0
                and generation % diversity_interval == 0
            ):
                reproduction_pool = maintain_diversity(
                    population,
                    training_data,
                    interpreter,
                    diversity_threshold=diversity_threshold,
                )
                reproduction_pool.sort(key=lambda genome: genome.fitness)

            new_population: List[PushGPGenome] = []
            elite_count = max(1, int(round(population_size * elite_fraction)))
            elite_count = min(elite_count, len(population), population_size)
            new_population.extend(genome.copy() for genome in population[:elite_count])

            while len(new_population) < population_size:
                if random.random() < crossover_rate and len(reproduction_pool) >= 2:
                    parent1 = _select_parent(
                        reproduction_pool,
                        selection=selection,
                        tournament_size=tournament_size,
                        lexicase_cases=lexicase_cases,
                    )
                    parent2 = _select_parent(
                        reproduction_pool,
                        selection=selection,
                        tournament_size=tournament_size,
                        lexicase_cases=lexicase_cases,
                    )
                    offspring = crossover_genomes(
                        parent1,
                        parent2,
                        max_program_atoms=max_program_atoms,
                        max_program_depth=max_program_depth,
                    )
                else:
                    parent = _select_parent(
                        reproduction_pool,
                        selection=selection,
                        tournament_size=tournament_size,
                        lexicase_cases=lexicase_cases,
                    )
                    offspring = parent.copy()

                adaptive_mutate_genome(
                    offspring,
                    interpreter,
                    generation,
                    generations,
                    stall_count,
                    base_rate=base_mutation_rate,
                    max_program_atoms=max_program_atoms,
                    max_program_depth=max_program_depth,
                )
                _reset_genome_evaluation(offspring)
                new_population.append(offspring)

            population = new_population
    finally:
        if executor is not None:
            executor.shutdown(wait=True)

    return best_genome


def evaluate_wrapper(args: tuple[Any, ...]) -> PushGPGenome:
    """Process-pool wrapper using data installed by ``init_worker``."""
    if GLOBAL_TRAINING_DATA is None or GLOBAL_INTERPRETER is None:
        raise RuntimeError("Worker was not initialized with training data/interpreter")
    genome, early_threshold = args[:2]
    return evaluate_genome(
        genome,
        GLOBAL_TRAINING_DATA,
        GLOBAL_INTERPRETER,
        early_stop_threshold=early_threshold,
        evaluation_config=GLOBAL_EVALUATION_CONFIG or EvaluationConfig(),
    )


def _canonical_object_type(obj_type: Any, data: Any) -> str:
    raw = str(obj_type or "").strip().lower().replace("/", ".")
    if "map" in raw or raw == "dict" or isinstance(data, dict):
        return "map"
    if "set" in raw or isinstance(data, set):
        return "set"
    if "list" in raw or "arraylist" in raw or isinstance(data, (list, tuple)):
        return "list"
    if raw in {"null", "none"}:
        return "null"
    if raw and raw not in {"unknown", "generic"}:
        return raw
    if data is None:
        return "null" if not raw else raw
    return raw or type(data).__name__.lower()


def _summary_from_value(value: Any) -> ObjectSummary:
    if isinstance(value, ObjectSummary):
        return ObjectSummary(
            size=value.size,
            keys=value.keys,
            field_hashes=value.field_hashes,
            obj_type=_canonical_object_type(value.obj_type, None),
        )
    if isinstance(value, Mapping) and "data" in value and "type" in value:
        data = value.get("data")
        obj_type = _canonical_object_type(value.get("type"), data)
        fields = {
            str(key): _stable_value(item)
            for key, item in dict(value.get("fields") or {}).items()
        }
    else:
        data = value
        obj_type = _canonical_object_type(None, data)
        fields = {}

    if isinstance(data, (list, tuple)):
        return ObjectSummary(
            size=len(data),
            field_hashes={"elements": _stable_value(data), **fields},
            obj_type="list",
        )
    if isinstance(data, dict):
        return ObjectSummary(
            size=len(data),
            keys=data.keys(),
            field_hashes={"entries": _stable_value(data), **fields},
            obj_type="map",
        )
    if isinstance(data, set):
        return ObjectSummary(
            size=len(data),
            field_hashes={"elements": _stable_value(data), **fields},
            obj_type="set",
        )
    if data is None:
        return ObjectSummary(size=0, field_hashes=fields, obj_type="null")
    return ObjectSummary(
        size=1,
        field_hashes={"value": _stable_value(data), **fields},
        obj_type=obj_type,
    )


def evaluate_state(pred: Any, target: Any) -> float:
    """Return an unbounded structural state-distance score.

    ``pred`` and ``target`` may be ObjectSummary instances, raw collections, or
    heap-entry dictionaries from ``PushGPInterpreter.execute_sequence``.
    """
    if pred is None and target is None:
        return 0.0
    if pred is None or target is None:
        return 1.0

    pred_summary = _summary_from_value(pred)
    target_summary = _summary_from_value(target)
    score = float(abs(pred_summary.size - target_summary.size))
    if pred_summary.obj_type != target_summary.obj_type:
        score += 1.0
    score += float(len(pred_summary.keys.symmetric_difference(target_summary.keys)))

    all_fields = set(pred_summary.field_hashes) | set(target_summary.field_hashes)
    for key in all_fields:
        if key not in pred_summary.field_hashes or key not in target_summary.field_hashes:
            score += 1.0
        else:
            score += _rec_error(
                pred_summary.field_hashes[key],
                target_summary.field_hashes[key],
            )
    return score


def _normalised_state_error(pred: Any, target: Any) -> float:
    if target is None:
        return 0.0
    pred_summary = _summary_from_value(pred) if pred is not None else ObjectSummary()
    target_summary = _summary_from_value(target)
    scale = (
        1.0
        + max(pred_summary.size, target_summary.size)
        + len(pred_summary.keys | target_summary.keys)
        + len(set(pred_summary.field_hashes) | set(target_summary.field_hashes))
    )
    return min(1.0, evaluate_state(pred, target) / scale)


def _extract_expected_final_state(example: Any) -> Any:
    """Find an optional final-state oracle without requiring a schema revision."""
    attributes = (
        "expected_final_state",
        "expected_state_after",
        "expected_state",
        "final_state",
        "expected_heap",
    )
    for name in attributes:
        if not hasattr(example, name):
            continue
        value = getattr(example, name)
        if value is None:
            continue

        if isinstance(value, Mapping) and "heap" in value:
            value = value["heap"]

        # Heap-shaped expected states are commonly {ref_id: data}. Do not unwrap a
        # raw Map model unless the attribute explicitly names a heap.
        data_structure_type = str(getattr(example, "data_structure_type", "")).lower()
        looks_like_ref_map = False
        if isinstance(value, Mapping) and value:
            looks_like_ref_map = all(
                isinstance(key, int) or (isinstance(key, str) and key.lstrip("-").isdigit())
                for key in value
            )
        heap_entry_values = bool(value) and isinstance(value, Mapping) and all(
            isinstance(item, Mapping) and "data" in item
            for item in value.values()
        )
        if isinstance(value, Mapping) and (
            "heap" in name
            or heap_entry_values
            or (looks_like_ref_map and "map" not in data_structure_type)
        ):
            refs = list(getattr(example, "receiver_refs", None) or [])
            preferred_ref = refs[-1] if refs else 0
            for candidate in (preferred_ref, str(preferred_ref), 0, "0"):
                if candidate in value:
                    return value[candidate]
            return next(iter(value.values())) if value else None
        return value
    return None


def _finalize_genome_metrics(
    genome: PushGPGenome,
    *,
    total_error: float,
    total_examples: int,
    correct_predictions: int,
    method_stats: Mapping[str, Mapping[str, float]],
    case_errors: List[float],
    evaluation_config: EvaluationConfig,
) -> PushGPGenome:
    base_fitness = total_error / total_examples if total_examples else 1.0
    complexity_penalty = genome.get_complexity_penalty()
    genome.fitness = base_fitness + evaluation_config.complexity_weight * complexity_penalty
    genome.accuracy = correct_predictions / total_examples if total_examples else 0.0
    genome.complexity_penalty = complexity_penalty
    genome.case_errors = list(case_errors)

    method_accuracies: Dict[str, float] = {}
    for method_name, stats in method_stats.items():
        direct_acc = float(stats["correct"]) / max(1.0, float(stats["total"]))
        if stats["downstream_total"]:
            downstream_acc = float(stats["downstream_correct"]) / float(
                stats["downstream_total"]
            )
        else:
            downstream_acc = direct_acc
        method_accuracies[method_name] = 0.7 * direct_acc + 0.3 * downstream_acc
    genome.method_accuracies = method_accuracies
    return genome


def evaluate_genome(
    genome: PushGPGenome,
    training_data: Sequence[Any],
    interpreter: PushGPInterpreter,
    early_stop_threshold: Optional[float] = None,
    evaluation_config: Optional[EvaluationConfig] = None,
) -> PushGPGenome:
    """Evaluate a genome on complete traces and cache per-trace errors."""
    evaluation_config = evaluation_config or EvaluationConfig()
    training_data = list(training_data or [])
    total_error = 0.0
    total_examples = 0
    correct_predictions = 0
    case_errors: List[float] = []
    method_stats: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {
            "correct": 0.0,
            "total": 0.0,
            "downstream_correct": 0.0,
            "downstream_total": 0.0,
        }
    )
    evaluation_failures: List[str] = []

    abort_sum: Optional[float] = None
    if early_stop_threshold is not None and math.isfinite(early_stop_threshold):
        abort_sum = max(0.0, early_stop_threshold) * len(training_data)

    for example_index, example in enumerate(training_data):
        sequence = [str(name) for name in list(getattr(example, "sequence", None) or [])]
        expected_outputs = list(getattr(example, "expected_outputs", None) or [])
        try:
            predicted_outputs, used_inputs, state_after = interpreter.execute_sequence(
                genome, example
            )
            per_call_errors = calculate_per_call_errors(
                sequence, predicted_outputs, expected_outputs
            )
            call_correct = [
                error <= evaluation_config.correctness_tolerance
                for error in per_call_errors[: len(sequence)]
            ]

            for index, method_name in enumerate(sequence):
                is_correct = call_correct[index] if index < len(call_correct) else False
                stats = method_stats[method_name]
                stats["correct"] += float(is_correct)
                stats["total"] += 1.0
                downstream = call_correct[index + 1 :]
                stats["downstream_correct"] += float(sum(downstream))
                stats["downstream_total"] += float(len(downstream))

            output_error = aggregate_genome_error(
                sequence, predicted_outputs, expected_outputs
            )
            input_args = list(getattr(example, "input_args", None) or [])
            unused_penalty = compute_arg_unused_penalty(
                sequence, used_inputs, input_args
            )
            expected_state = _extract_expected_final_state(example)
            state_error = _normalised_state_error(state_after, expected_state)

            case_error = min(
                1.0,
                output_error
                + evaluation_config.argument_use_weight * unused_penalty
                + evaluation_config.state_weight * state_error,
            )
            case_errors.append(case_error)
            total_error += case_error
            total_examples += 1

            output_correct = bool(per_call_errors) and all(
                error <= evaluation_config.correctness_tolerance
                for error in per_call_errors
            )
            if not sequence:
                output_correct = True
            if (
                output_correct
                and state_error <= evaluation_config.correctness_tolerance
            ):
                correct_predictions += 1

        except Exception as exc:
            case_errors.append(1.0)
            total_error += 1.0
            total_examples += 1
            evaluation_failures.append(
                f"case {example_index}: {type(exc).__name__}: {exc}"
            )
            for method_name in sequence:
                method_stats[method_name]["total"] += 1.0

        if abort_sum is not None and total_error > abort_sum:
            # The accumulated non-negative error already proves this candidate cannot
            # beat the threshold. Fill missing cases so lexicase consumers never see
            # vectors of inconsistent length.
            remaining_examples = training_data[example_index + 1 :]
            case_errors.extend([1.0] * len(remaining_examples))
            total_error += float(len(remaining_examples))
            total_examples += len(remaining_examples)
            for remaining in remaining_examples:
                for method_name in list(getattr(remaining, "sequence", None) or []):
                    method_stats[str(method_name)]["total"] += 1.0
            break

    genome = _finalize_genome_metrics(
        genome,
        total_error=total_error,
        total_examples=total_examples,
        correct_predictions=correct_predictions,
        method_stats=method_stats,
        case_errors=case_errors,
        evaluation_config=evaluation_config,
    )
    genome.evaluation_failures = evaluation_failures
    return genome


def _case_error(genome: PushGPGenome, index: int) -> float:
    if index >= len(genome.case_errors):
        return 1.0
    value = genome.case_errors[index]
    try:
        value = float(value)
    except (TypeError, ValueError):
        return 1.0
    return value if math.isfinite(value) else 1.0


def _mad_epsilon(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    center = median(values)
    return median(abs(value - center) for value in values)


def lexicase_selection(
    population: List[PushGPGenome],
    num_cases: int = 40,
    epsilon: Optional[float] = 1e-6,
) -> PushGPGenome:
    """Select using cached per-example errors without re-executing candidates.

    Set ``epsilon=None`` for median-absolute-deviation epsilon lexicase.
    """
    if not population:
        raise ValueError("population cannot be empty")
    candidates = [genome for genome in population if genome.case_errors]
    if not candidates:
        return random.choice(population)

    n_cases = max(len(genome.case_errors) for genome in candidates)
    if n_cases == 0:
        return random.choice(candidates)
    case_indices = random.sample(range(n_cases), min(max(1, num_cases), n_cases))

    for index in case_indices:
        if len(candidates) <= 1:
            break
        errors = [_case_error(genome, index) for genome in candidates]
        best = min(errors)
        case_epsilon = _mad_epsilon(errors) if epsilon is None else max(0.0, epsilon)
        candidates = [
            genome
            for genome, error in zip(candidates, errors)
            if error <= best + case_epsilon + EPS
        ]
        if not candidates:
            return random.choice(population)
    return random.choice(candidates)


def tournament_selection(
    population: List[PushGPGenome],
    tournament_size: Any = DEFAULT_TOURNAMENT_SIZE,
    *_legacy_args: Any,
) -> PushGPGenome:
    """Tournament selection with compatibility for the old broken call shape.

    Older code passed ``(population, training_data, interpreter)``. When the second
    argument is not an integer, a default tournament size is used instead.
    """
    if not population:
        raise ValueError("population cannot be empty")
    if isinstance(tournament_size, bool) or not isinstance(tournament_size, int):
        tournament_size = DEFAULT_TOURNAMENT_SIZE
    tournament_size = max(1, min(tournament_size, len(population)))
    tournament = random.sample(population, tournament_size)
    return min(tournament, key=lambda genome: genome.fitness)


def _ordered_method_union(parent1: PushGPGenome, parent2: PushGPGenome) -> List[str]:
    names = list(parent1.methods)
    names.extend(name for name in parent2.methods if name not in parent1.methods)
    return names


def _bounded_program_copy(
    code: Iterable[Any],
    max_atoms: int = DEFAULT_MAX_PROGRAM_ATOMS,
    max_depth: int = DEFAULT_MAX_PROGRAM_DEPTH,
) -> List[Any]:
    """Deep-copy a program while enforcing atom and nesting limits."""
    remaining = [max(1, int(max_atoms))]

    def visit(items: Iterable[Any], depth: int) -> List[Any]:
        output: List[Any] = []
        for item in items or []:
            if remaining[0] <= 0:
                break
            if isinstance(item, (list, tuple)):
                if depth >= max_depth:
                    continue
                nested = visit(item, depth + 1)
                if nested:
                    output.append(nested)
            else:
                output.append(copy.deepcopy(item))
                remaining[0] -= 1
        return output

    return visit(code, 1)


def crossover_genomes(
    parent1: PushGPGenome,
    parent2: PushGPGenome,
    *,
    max_program_atoms: int = DEFAULT_MAX_PROGRAM_ATOMS,
    max_program_depth: int = DEFAULT_MAX_PROGRAM_DEPTH,
) -> PushGPGenome:
    """Cross over method programs without sharing mutable nested code."""
    offspring = PushGPGenome()
    for method_name in _ordered_method_union(parent1, parent2):
        if method_name in parent1.methods and method_name in parent2.methods:
            accuracy1 = parent1.method_accuracies.get(method_name, 0.0)
            accuracy2 = parent2.method_accuracies.get(method_name, 0.0)
            if random.random() < 0.8:
                new_code = crossover_programs(
                    parent1.methods[method_name].code,
                    parent2.methods[method_name].code,
                    max_program_atoms=max_program_atoms,
                    max_program_depth=max_program_depth,
                )
            else:
                source = (
                    parent1.methods[method_name].code
                    if accuracy1 >= accuracy2
                    else parent2.methods[method_name].code
                )
                new_code = _bounded_program_copy(
                    source, max_program_atoms, max_program_depth
                )
        elif method_name in parent1.methods:
            new_code = _bounded_program_copy(
                parent1.methods[method_name].code,
                max_program_atoms,
                max_program_depth,
            )
        else:
            new_code = _bounded_program_copy(
                parent2.methods[method_name].code,
                max_program_atoms,
                max_program_depth,
            )
        offspring.add_method(method_name, PushProgram(new_code))
        if method_name in parent1.methods and method_name in parent2.methods:
            offspring.method_accuracies[method_name] = max(
                parent1.method_accuracies.get(method_name, 0.0),
                parent2.method_accuracies.get(method_name, 0.0),
            )
        elif method_name in parent1.methods:
            offspring.method_accuracies[method_name] = parent1.method_accuracies.get(
                method_name, 0.0
            )
        else:
            offspring.method_accuracies[method_name] = parent2.method_accuracies.get(
                method_name, 0.0
            )
    offspring.fitness = float("inf")
    offspring.accuracy = 0.0
    offspring.complexity_penalty = 0.0
    offspring.case_errors = []
    offspring.invalidate_signature()
    return offspring


def crossover_programs(
    program1: List[Any],
    program2: List[Any],
    *,
    max_program_atoms: int = DEFAULT_MAX_PROGRAM_ATOMS,
    max_program_depth: int = DEFAULT_MAX_PROGRAM_DEPTH,
) -> List[Any]:
    """Perform bounded top-level crossover and deep-copy the result."""
    if not program1 and not program2:
        return []
    if not program1:
        return _bounded_program_copy(program2, max_program_atoms, max_program_depth)
    if not program2:
        return _bounded_program_copy(program1, max_program_atoms, max_program_depth)

    strategy = random.choice(("single_point", "uniform", "block"))
    if strategy == "single_point":
        point1 = random.randint(0, len(program1))
        point2 = random.randint(0, len(program2))
        raw = list(program1[:point1]) + list(program2[point2:])
    elif strategy == "uniform":
        raw = []
        for index in range(max(len(program1), len(program2))):
            if index < len(program1) and index < len(program2):
                raw.append(program1[index] if random.random() < 0.5 else program2[index])
            elif index < len(program1):
                raw.append(program1[index])
            else:
                raw.append(program2[index])
    else:
        raw = list(program1[: len(program1) // 2]) + list(
            program2[len(program2) // 2 :]
        )
    return _bounded_program_copy(raw, max_program_atoms, max_program_depth)


def _fresh_instruction(interpreter: PushGPInterpreter) -> PushInstruction:
    return interpreter._get_random_instruction()


def _all_code_containers(program: List[Any]) -> List[List[Any]]:
    containers = [program]
    for item in list(program):
        if isinstance(item, list):
            containers.extend(_all_code_containers(item))
    return containers


def _all_atom_locations(program: List[Any]) -> List[tuple[List[Any], int, Any]]:
    locations: List[tuple[List[Any], int, Any]] = []
    for container in _all_code_containers(program):
        for index, item in enumerate(container):
            if not isinstance(item, list):
                locations.append((container, index, item))
    return locations


def _bound_program_in_place(
    program: List[Any],
    max_program_atoms: int,
    max_program_depth: int,
) -> None:
    program[:] = _bounded_program_copy(
        program, max_program_atoms, max_program_depth
    )


def adaptive_mutate_genome(
    genome: PushGPGenome,
    interpreter: PushGPInterpreter,
    generation: int,
    max_generations: int,
    stall_count: int,
    base_rate: float = 0.4,
    *,
    max_program_atoms: int = DEFAULT_MAX_PROGRAM_ATOMS,
    max_program_depth: int = DEFAULT_MAX_PROGRAM_DEPTH,
) -> None:
    """Adapt mutation strength to progress, stalling, and method accuracy."""
    progress = generation / max(1, max_generations)
    stall_boost = 1.0 + min(0.75, max(0, stall_count) / 50.0)
    mutation_rate = min(1.0, base_rate * (1.0 - 0.5 * progress) * stall_boost)
    old_accuracies = dict(genome.method_accuracies)

    for method_name, program in genome.methods.items():
        if not program.code:
            program.code = interpreter.random_program(max_depth=2, max_length=8)
            _bound_program_in_place(
                program.code, max_program_atoms, max_program_depth
            )
            continue
        if random.random() >= mutation_rate:
            continue

        accuracy = old_accuracies.get(method_name, 0.0)
        if stall_count > 25 and accuracy > 0.5:
            mutate_program_aggressive(
                program.code,
                interpreter,
                max_program_atoms=max_program_atoms,
                max_program_depth=max_program_depth,
            )
        elif accuracy < 0.4:
            mutate_program_aggressive(
                program.code,
                interpreter,
                max_program_atoms=max_program_atoms,
                max_program_depth=max_program_depth,
            )
        elif accuracy < 0.98:
            mutate_program(
                program.code,
                interpreter,
                mutation_rate=0.4,
                max_program_atoms=max_program_atoms,
                max_program_depth=max_program_depth,
            )
        elif random.random() < 0.5:
            mutate_program_conservative(
                program.code,
                interpreter,
                max_program_atoms=max_program_atoms,
                max_program_depth=max_program_depth,
            )
        else:
            mutate_program(
                program.code,
                interpreter,
                mutation_rate=0.2,
                max_program_atoms=max_program_atoms,
                max_program_depth=max_program_depth,
            )
    genome.invalidate_signature()


def mutate_program_aggressive(
    program: List[Any],
    interpreter: PushGPInterpreter,
    *,
    max_program_atoms: int = DEFAULT_MAX_PROGRAM_ATOMS,
    max_program_depth: int = DEFAULT_MAX_PROGRAM_DEPTH,
) -> None:
    """Replace a block or many atoms for broad exploration."""
    if not program or random.random() < 0.5:
        replacement = interpreter.random_program(max_depth=3, max_length=8)
        if len(program) > 2:
            start = random.randint(0, len(program) - 2)
            end = random.randint(start + 1, len(program))
            program[start:end] = replacement
        else:
            program[:] = replacement
    else:
        locations = _all_atom_locations(program)
        if not locations:
            program.append(_fresh_instruction(interpreter))
        for container, index, _ in locations:
            if random.random() < 0.5:
                container[index] = _fresh_instruction(interpreter)
    _bound_program_in_place(program, max_program_atoms, max_program_depth)


def mutate_program_conservative(
    program: List[Any],
    interpreter: PushGPInterpreter,
    *,
    max_program_atoms: int = DEFAULT_MAX_PROGRAM_ATOMS,
    max_program_depth: int = DEFAULT_MAX_PROGRAM_DEPTH,
) -> None:
    """Apply a small local mutation to a high-performing program."""
    if not program:
        program.append(_fresh_instruction(interpreter))
        return

    mutation_type = random.choice(("swap", "tweak_constant", "insert", "replace"))
    containers = [container for container in _all_code_containers(program) if container]

    if mutation_type == "swap":
        swappable = [container for container in containers if len(container) >= 2]
        if swappable:
            container = random.choice(swappable)
            index = random.randint(0, len(container) - 2)
            container[index], container[index + 1] = container[index + 1], container[index]
        else:
            mutation_type = "replace"

    if mutation_type == "tweak_constant":
        constants = [
            location
            for location in _all_atom_locations(program)
            if isinstance(location[2], (INT_CONST, ERC_INT, FLOAT_CONST, ERC_FLOAT))
        ]
        if constants:
            container, index, instruction = random.choice(constants)
            if isinstance(instruction, (INT_CONST, ERC_INT)):
                container[index] = instruction.__class__(
                    int(instruction.value) + random.choice((-1, 1))
                )
            else:
                scale = max(0.1, abs(float(instruction.value)) * 0.1)
                container[index] = instruction.__class__(
                    float(instruction.value) + random.choice((-scale, scale))
                )
        else:
            mutation_type = "replace"

    if mutation_type == "insert":
        container = random.choice(_all_code_containers(program))
        position = random.randint(0, len(container))
        container.insert(position, _fresh_instruction(interpreter))

    if mutation_type == "replace":
        locations = _all_atom_locations(program)
        if locations:
            container, index, _ = random.choice(locations)
            container[index] = _fresh_instruction(interpreter)
        else:
            program.append(_fresh_instruction(interpreter))

    _bound_program_in_place(program, max_program_atoms, max_program_depth)


def mutate_program(
    program: List[Any],
    interpreter: PushGPInterpreter,
    mutation_rate: float = 0.4,
    *,
    max_program_atoms: int = DEFAULT_MAX_PROGRAM_ATOMS,
    max_program_depth: int = DEFAULT_MAX_PROGRAM_DEPTH,
) -> None:
    """Perform structural and atom-level mutation on nested Push code."""
    mutation_rate = min(1.0, max(0.0, mutation_rate))
    if not program:
        program.extend(
            _fresh_instruction(interpreter) for _ in range(random.randint(2, 5))
        )
        _bound_program_in_place(program, max_program_atoms, max_program_depth)
        return

    def mutate_recursive(container: List[Any], depth: int) -> None:
        for index in range(len(container)):
            item = container[index]
            if isinstance(item, list):
                if random.random() < mutation_rate:
                    if depth < max_program_depth and random.random() < 0.5:
                        mutate_recursive(item, depth + 1)
                    else:
                        container[index] = _fresh_instruction(interpreter)
                else:
                    mutate_recursive(item, depth + 1)
            elif random.random() < mutation_rate:
                if depth < max_program_depth and random.random() >= 0.7:
                    container[index] = interpreter.random_program(
                        max_depth=min(2, max_program_depth - depth), max_length=4
                    )
                else:
                    container[index] = _fresh_instruction(interpreter)

    if random.random() < mutation_rate:
        containers = _all_code_containers(program)
        container = random.choice(containers)
        if container and random.random() < 0.55:
            container.pop(random.randrange(len(container)))
        else:
            container.insert(
                random.randint(0, len(container)), _fresh_instruction(interpreter)
            )

    mutate_recursive(program, 1)
    if not program:
        program.append(_fresh_instruction(interpreter))
    _bound_program_in_place(program, max_program_atoms, max_program_depth)


def _stable_value(value: Any) -> Any:
    if value is MISSING_RESULT:
        return ("missing-result",)
    if isinstance(value, HeapReference):
        return ("reference", value.ref_id)
    if isinstance(value, ObjectSummary):
        return (
            "summary",
            value.obj_type,
            value.size,
            tuple(sorted((_stable_value(key) for key in value.keys), key=repr)),
            _stable_value(value.field_hashes),
        )
    if isinstance(value, Mapping):
        return tuple(
            sorted(
                ((_stable_value(key), _stable_value(item)) for key, item in value.items()),
                key=repr,
            )
        )
    if isinstance(value, (list, tuple)):
        return tuple(_stable_value(item) for item in value)
    if isinstance(value, set):
        return tuple(sorted((_stable_value(item) for item in value), key=repr))
    if isinstance(value, float) and math.isnan(value):
        return ("nan",)
    try:
        hash(value)
        return value
    except (TypeError, ValueError):
        return repr(value)


def _behavior_sample_indices(length: int, sample_size: int) -> List[int]:
    if length <= 0 or sample_size <= 0:
        return []
    count = min(length, sample_size)
    if count == length:
        return list(range(length))
    if count == 1:
        return [0]
    return sorted(
        {round(index * (length - 1) / (count - 1)) for index in range(count)}
    )


def _calculate_behavioral_signature(
    genome: PushGPGenome,
    training_data: List[TrainingExample],
    interpreter: PushGPInterpreter,
    sample_size: int = 5,
) -> tuple[Any, ...]:
    """Create a deterministic output-and-final-state signature."""
    indices = _behavior_sample_indices(len(training_data), sample_size)
    cache_key = (
        id(training_data),
        tuple(indices),
        interpreter.profile,
        interpreter.max_steps,
    )
    if (
        genome._behavioral_signature is not None
        and getattr(genome, "_behavioral_signature_key", None) == cache_key
    ):
        return genome._behavioral_signature

    signature: List[Any] = []
    for index in indices:
        example = training_data[index]
        try:
            predicted, used_inputs, final_state = interpreter.execute_sequence(
                genome, example
            )
            signature.append(
                (
                    tuple(_stable_value(value) for value in predicted),
                    tuple(bool(value) for value in used_inputs),
                    _stable_value(interpreter.to_summary(final_state)),
                )
            )
        except Exception as exc:
            signature.append(("evaluation-error", type(exc).__name__))

    genome._behavioral_signature = tuple(signature)
    genome._behavioral_signature_key = cache_key
    return genome._behavioral_signature


def _signature_similarity(left: Sequence[Any], right: Sequence[Any]) -> float:
    if not left and not right:
        return 1.0
    missing = object()
    pairs = list(zip_longest(left, right, fillvalue=missing))
    if not pairs:
        return 1.0
    return sum(first == second for first, second in pairs) / len(pairs)


def maintain_diversity(
    population: List[PushGPGenome],
    training_data: List[TrainingExample],
    interpreter: PushGPInterpreter,
    diversity_threshold: float = 0.3,
) -> List[PushGPGenome]:
    """Retain a fitness-ordered behaviorally diverse reproduction pool."""
    if len(population) < 2:
        return list(population)
    if not 0.0 <= diversity_threshold <= 1.0:
        raise ValueError("diversity_threshold must be in [0, 1]")

    ordered = sorted(population, key=lambda genome: genome.fitness)
    signatures = [
        _calculate_behavioral_signature(genome, training_data, interpreter)
        for genome in ordered
    ]
    target_minimum = max(2, math.ceil(len(ordered) * 0.5))
    diverse_population = [ordered[0]]
    diverse_signatures = [signatures[0]]

    for genome, signature in zip(ordered[1:], signatures[1:]):
        is_diverse = all(
            _signature_similarity(signature, existing) <= 1.0 - diversity_threshold
            for existing in diverse_signatures
        )
        if is_diverse or len(diverse_population) < target_minimum:
            diverse_population.append(genome)
            diverse_signatures.append(signature)
    return diverse_population


def _string_error(left: str, right: str) -> float:
    if left == right:
        return 0.0
    if Levenshtein is not None:
        distance = Levenshtein.distance(left, right)
        return min(distance / max(len(left), len(right), 1), 1.0)
    ratio = difflib.SequenceMatcher(None, left, right).ratio()
    return 1.0 - ratio


def _numeric_error(predicted: float, expected: float) -> float:
    if math.isnan(predicted) or math.isnan(expected):
        return 0.0 if math.isnan(predicted) and math.isnan(expected) else 1.0
    if math.isinf(predicted) or math.isinf(expected):
        return 0.0 if predicted == expected else 1.0
    if math.isclose(predicted, expected, rel_tol=1e-9, abs_tol=EPS):
        return 0.0
    denominator = max(abs(expected), 1.0)
    return min(abs(predicted - expected) / denominator, 1.0)


def _normalise_reference_id(value: Any) -> Any:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        text = str(value)
        if len(text) > 1 and text[0].lower() in {"o", "r"} and text[1:].isdigit():
            return int(text[1:])
        return text


def _normalise_observed_value(value: Any) -> Any:
    """Normalize common JSON trace wrappers before comparing outcomes."""
    if value is MISSING_RESULT:
        return MISSING_RESULT
    if isinstance(value, HeapReference):
        return ("reference", _normalise_reference_id(value.ref_id))
    if isinstance(value, Mapping):
        kind = str(value.get("kind", "")).lower()
        if kind in {"return", "returned"} and "value" in value:
            return _normalise_observed_value(value["value"])
        if kind in {"null", "none"}:
            return None
        if kind in {"reference", "ref"}:
            ref_id = value.get("id", value.get("ref_id"))
            return ("reference", _normalise_reference_id(ref_id))
        if kind in {"exception", "throw", "thrown", "error"}:
            exception_type = value.get("exceptionType", value.get("type"))
            return ("exception", str(exception_type) if exception_type else None)
    return value


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _rec_error(pred: Any, exp: Any, _depth: int = 0) -> float:
    """Recursive normalized error in [0, 1] for Java/JSON-like values."""
    if _depth > 32:
        return 0.0 if _stable_value(pred) == _stable_value(exp) else 1.0

    pred = _normalise_observed_value(pred)
    exp = _normalise_observed_value(exp)

    if pred is MISSING_RESULT or exp is MISSING_RESULT:
        return 0.0 if pred is MISSING_RESULT and exp is MISSING_RESULT else 1.0
    if pred is None and exp is None:
        return 0.0
    if pred is None or exp is None:
        return 1.0

    # Current pushbase represents exceptions generically as "error". Preserve that
    # compatibility while allowing future typed exception tuples.
    if exp == "error" and (
        pred == "error" or (isinstance(pred, tuple) and pred[:1] == ("exception",))
    ):
        return 0.0
    if pred == "error" and isinstance(exp, tuple) and exp[:1] == ("exception",):
        return 0.0
    if isinstance(pred, tuple) and pred[:1] == ("exception",):
        return 0.0 if pred == exp else 1.0
    if isinstance(exp, tuple) and exp[:1] == ("exception",):
        return 1.0

    if isinstance(exp, bool) or isinstance(pred, bool):
        return 0.0 if type(pred) is bool and type(exp) is bool and pred == exp else 1.0
    if _is_number(pred) and _is_number(exp):
        return _numeric_error(float(pred), float(exp))
    if isinstance(pred, str) and isinstance(exp, str):
        return _string_error(pred, exp)
    if isinstance(pred, ObjectSummary) or isinstance(exp, ObjectSummary):
        return _normalised_state_error(pred, exp)

    if isinstance(pred, Mapping) and isinstance(exp, Mapping):
        keys = set(pred) | set(exp)
        if not keys:
            return 0.0
        errors = []
        for key in keys:
            if key not in pred or key not in exp:
                errors.append(1.0)
            else:
                errors.append(_rec_error(pred[key], exp[key], _depth + 1))
        return sum(errors) / len(errors)

    if isinstance(pred, (list, tuple)) and isinstance(exp, (list, tuple)):
        if not pred and not exp:
            return 0.0
        missing = object()
        errors = [
            1.0
            if left is missing or right is missing
            else _rec_error(left, right, _depth + 1)
            for left, right in zip_longest(pred, exp, fillvalue=missing)
        ]
        return sum(errors) / max(1, len(errors))

    if isinstance(pred, set) and isinstance(exp, set):
        frozen_pred = {_stable_value(value) for value in pred}
        frozen_exp = {_stable_value(value) for value in exp}
        union = frozen_pred | frozen_exp
        return len(frozen_pred ^ frozen_exp) / max(1, len(union))

    if type(pred) is not type(exp):
        return 1.0
    try:
        return 0.0 if pred == exp else 1.0
    except Exception:
        return 1.0



def calculate_per_call_errors(
    sequence: List[str],
    predicted: List[Any],
    expected: List[Any],
) -> List[float]:
    """Return errors aligned across calls without treating absent values as null."""
    length = max(len(sequence), len(predicted), len(expected))
    errors: List[float] = []
    for index in range(length):
        pred = predicted[index] if index < len(predicted) else MISSING_RESULT
        exp = expected[index] if index < len(expected) else MISSING_RESULT
        errors.append(_rec_error(pred, exp))
    return errors


def aggregate_genome_error(
    sequence: List[str],
    predicted: List[Any],
    expected: List[Any],
) -> float:
    """Combine sequence-order and method-balanced output errors."""
    per_call = calculate_per_call_errors(sequence, predicted, expected)
    if not per_call:
        return 0.0

    # sqrt emphasizes small semantic mismatches instead of letting them disappear.
    shaped = [math.sqrt(min(1.0, max(0.0, error))) for error in per_call]
    recency_weights = [1.0 + index * 0.1 for index in range(len(shaped))]
    recency_mean = sum(
        error * weight for error, weight in zip(shaped, recency_weights)
    ) / sum(recency_weights)

    grouped: Dict[str, List[float]] = defaultdict(list)
    for index, error in enumerate(shaped):
        name = sequence[index] if index < len(sequence) else "<extra-output>"
        grouped[name].append(error)
    method_mean = sum(
        sum(errors) / len(errors) for errors in grouped.values()
    ) / len(grouped)

    return float(min(1.0, max(0.0, 0.7 * recency_mean + 0.3 * method_mean)))


def compute_arg_unused_penalty(
    sequence: List[str],
    used_inputs: List[bool],
    input_args: List[List[Any]],
) -> float:
    """Return a small penalty for argument-bearing calls that consume no input."""
    if not sequence:
        return 0.0
    misses = 0
    applicable = 0
    for index in range(len(sequence)):
        args = input_args[index] if index < len(input_args) else []
        if not args:
            continue
        applicable += 1
        used = used_inputs[index] if index < len(used_inputs) else False
        misses += int(not used)
    if applicable == 0:
        return 0.0
    return min(1.0, 0.3 * misses / applicable)
