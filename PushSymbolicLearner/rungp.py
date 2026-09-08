from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any, Iterable, List, Mapping, Sequence
from pushgp_smt import UnsupportedInstructionError, export_genome_to_smt, SMTExportConfig

from pushgp_learner import (
    EvaluationConfig,
    run_pushgp_evolution,
    serialize_program,
)
from trainingexample import TrainingExample


_JSON_SUFFIXES = {".json", ".jsonl", ".ndjson"}
_MISSING = object()


def _first_present(row: Mapping[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in row:
            return row[name]
    return default


def _normalise_ref_id(value: Any) -> int:
    """Normalise numeric and common prefixed object-reference identifiers."""
    if isinstance(value, bool):
        raise ValueError(f"Boolean is not a valid reference id: {value!r}")
    if isinstance(value, int):
        if value < 0:
            raise ValueError(f"Reference id must be non-negative: {value}")
        return value
    if isinstance(value, Mapping):
        value = _first_present(value, "id", "ref_id", "refId", default=_MISSING)
        if value is _MISSING:
            raise ValueError("Reference object is missing id/ref_id")
        return _normalise_ref_id(value)

    text = str(value).strip()
    if text.isdigit():
        return int(text)

    match = re.fullmatch(r"(?:o|r|ref)[:#_-]?(\d+)", text, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    raise ValueError(f"Invalid reference id: {value!r}")


def _decode_json_value(value: Any) -> Any:
    """Decode the small set of wrappers needed by the revised abstract heap."""
    if isinstance(value, list):
        return [_decode_json_value(item) for item in value]

    if not isinstance(value, dict):
        return value

    kind = str(value.get("kind", "")).strip().lower()
    if kind in {"set", "java.util.set", "hashset", "treeset"}:
        raw_values = value.get("values", value.get("data", []))
        return {_decode_json_value(item) for item in (raw_values or [])}

    decoded = {key: _decode_json_value(item) for key, item in value.items()}

    # Heap entries can explicitly declare their domain type. Convert set-backed
    # entries to Python sets because SET.* instructions expect set storage.
    obj_type = str(decoded.get("type", "")).strip().lower()
    if "set" in obj_type and "data" in decoded and isinstance(decoded["data"], list):
        decoded["data"] = set(decoded["data"])

    return decoded


def _default_initial_state(data_structure_type: str) -> dict[int, Any]:
    kind = (data_structure_type or "list").strip().lower()
    if "map" in kind:
        return {0: {}}
    if "set" in kind:
        return {0: {"type": "set", "data": set(), "fields": {}}}
    return {0: []}


def _normalise_initial_state(raw_state: Any, data_structure_type: str) -> dict[int, Any]:
    if raw_state is None:
        return _default_initial_state(data_structure_type)
    if not isinstance(raw_state, Mapping):
        raise ValueError("initial_state must be a JSON object mapping reference ids to objects")

    state: dict[int, Any] = {}
    for raw_ref, raw_value in raw_state.items():
        state[_normalise_ref_id(raw_ref)] = _decode_json_value(raw_value)
    return state or _default_initial_state(data_structure_type)


def _normalise_args(raw: Any, call_count: int, field_name: str) -> list[list[Any]]:
    if raw is None:
        return [[] for _ in range(call_count)]

    if call_count == 1:
        if not isinstance(raw, list):
            return [[raw]]
        if len(raw) == 1 and isinstance(raw[0], list):
            return [[_decode_json_value(item) for item in raw[0]]]
        return [[_decode_json_value(item) for item in raw]]

    if not isinstance(raw, list) or len(raw) != call_count:
        actual = len(raw) if isinstance(raw, list) else "non-list"
        raise ValueError(f"{field_name} has length {actual}; expected {call_count}")

    result: list[list[Any]] = []
    for item in raw:
        if item is None:
            result.append([])
        elif isinstance(item, list):
            result.append([_decode_json_value(value) for value in item])
        else:
            result.append([_decode_json_value(item)])
    return result


def _normalise_type_inputs(raw: Any, call_count: int) -> list[list[str]]:
    if raw is None:
        return [[] for _ in range(call_count)]

    if call_count == 1:
        if isinstance(raw, str):
            return [[raw]]
        if not isinstance(raw, list):
            return [[str(raw)]]
        if len(raw) == 1 and isinstance(raw[0], list):
            return [[str(value) for value in raw[0]]]
        return [[str(value) for value in raw]]

    if not isinstance(raw, list) or len(raw) != call_count:
        actual = len(raw) if isinstance(raw, list) else "non-list"
        raise ValueError(f"type_inputs has length {actual}; expected {call_count}")

    result: list[list[str]] = []
    for item in raw:
        if item is None:
            result.append([])
        elif isinstance(item, list):
            result.append([str(value) for value in item])
        else:
            result.append([str(item)])
    return result


def _infer_output_type(value: Any) -> str:
    if value == "error":
        return "error"
    if value is None:
        return "object"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "double"
    if isinstance(value, str):
        return "java.lang.String"
    return "object"


def _normalise_expected_outputs(raw: Any, call_count: int) -> list[Any]:
    if call_count == 1 and not isinstance(raw, list):
        return [_decode_json_value(raw)]
    if not isinstance(raw, list):
        raise ValueError("expected_outputs/output must be a call-aligned list")
    if len(raw) == call_count:
        return [_decode_json_value(value) for value in raw]
    if call_count == 1:
        # Legacy single-call traces occasionally stored a collection return directly.
        return [[_decode_json_value(value) for value in raw]]
    raise ValueError(f"expected_outputs has length {len(raw)}; expected {call_count}")


def _normalise_type_outputs(raw: Any, call_count: int, expected_outputs: Sequence[Any]) -> list[str]:
    if raw is None:
        return [_infer_output_type(value) for value in expected_outputs]
    if isinstance(raw, str):
        if call_count != 1:
            raise ValueError("type_outputs/typeOutput must be call-aligned")
        return [raw]
    if not isinstance(raw, list):
        if call_count == 1:
            return [str(raw)]
        raise ValueError("type_outputs/typeOutput must be call-aligned")
    if len(raw) != call_count:
        raise ValueError(f"type_outputs has length {len(raw)}; expected {call_count}")
    return [str(value) for value in raw]


def _normalise_receiver_refs(raw: Any, call_count: int) -> list[int]:
    if raw is None or raw == []:
        return [0] * call_count
    if not isinstance(raw, list):
        if call_count == 1:
            raw = [raw]
        else:
            raise ValueError("receiver_refs/receiverRefs must be call-aligned")
    if len(raw) != call_count:
        raise ValueError(f"receiver_refs has length {len(raw)}; expected {call_count}")
    return [_normalise_ref_id(value) for value in raw]


def _normalise_trace(row: Mapping[str, Any], source_name: str) -> TrainingExample:
    if not isinstance(row, Mapping):
        raise ValueError("Trace is not a JSON object")

    sequence = _first_present(row, "sequence", "methods")
    if not isinstance(sequence, list) or not sequence:
        raise ValueError("Trace has no non-empty sequence")
    sequence = [str(name) for name in sequence]
    call_count = len(sequence)

    data_structure_type = str(
        _first_present(
            row,
            "data_structure_type",
            "dataStructureType",
            default=infer_type_from_filename(source_name),
        )
        or infer_type_from_filename(source_name)
    )

    raw_expected_outputs = _first_present(
        row, "expected_outputs", "output", "outputs", default=_MISSING
    )
    if raw_expected_outputs is _MISSING:
        raise ValueError("Trace is missing expected_outputs/output")
    expected_outputs = _normalise_expected_outputs(raw_expected_outputs, call_count)
    type_outputs = _normalise_type_outputs(
        _first_present(row, "type_outputs", "typeOutput", "outputTypes", default=None),
        call_count,
        expected_outputs,
    )

    initial_state = _normalise_initial_state(
        _first_present(row, "initial_state", "initialState", default=None),
        data_structure_type,
    )
    input_args = _normalise_args(
        _first_present(row, "input_args", "input", "inputs", default=None),
        call_count,
        "input_args",
    )
    type_inputs = _normalise_type_inputs(
        _first_present(row, "type_inputs", "typeInput", "inputTypes", default=None),
        call_count,
    )
    receiver_refs = _normalise_receiver_refs(
        _first_present(row, "receiver_refs", "receiverRefs", default=None),
        call_count,
    )

    expected_final_state = _first_present(
        row,
        "expected_final_state",
        "expectedFinalState",
        "final_state",
        "finalState",
        default=None,
    )
    expected_final_state = _decode_json_value(expected_final_state)

    target_class = _first_present(row, "target_class", "targetClass", default=None)
    if target_class is not None:
        target_class = str(target_class)

    return TrainingExample(
        initial_state=initial_state,
        data_structure_type=data_structure_type,
        sequence=sequence,
        input_args=input_args,
        type_inputs=type_inputs,
        type_outputs=type_outputs,
        expected_outputs=expected_outputs,
        receiver_refs=receiver_refs,
        target_class=target_class,
        expected_final_state=expected_final_state,
    )


def _read_json_rows(path: Path) -> list[Mapping[str, Any]]:
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return []

    # Prefer normal JSON. If it is not a complete JSON value, fall back to JSONL.
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        rows: list[Mapping[str, Any]] = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at line {line_number}: {exc}") from exc
            if not isinstance(row, Mapping):
                raise ValueError(f"JSONL line {line_number} is not a JSON object")
            rows.append(row)
        return rows

    if isinstance(payload, Mapping):
        return [payload]
    if isinstance(payload, list):
        if not all(isinstance(row, Mapping) for row in payload):
            raise ValueError("Training JSON array must contain only objects")
        return list(payload)
    raise ValueError("Training file must contain a JSON object, JSON array, or JSONL objects")


def _sample_evenly(rows: Sequence[Mapping[str, Any]], limit: int | None) -> list[Mapping[str, Any]]:
    if limit is None or limit <= 0 or len(rows) <= limit:
        return list(rows)
    if limit == 1:
        return [rows[0]]
    scale = (len(rows) - 1) / (limit - 1)
    return [rows[round(index * scale)] for index in range(limit)]


def _training_files(data_path: Path, file_pattern: str | None) -> list[Path]:
    if data_path.is_file():
        return [data_path]

    if file_pattern:
        return sorted(path for path in data_path.glob(file_pattern) if path.is_file())

    files: set[Path] = set()
    for suffix in _JSON_SUFFIXES:
        files.update(path for path in data_path.glob(f"*{suffix}") if path.is_file())
    return sorted(files)


def loadtrainingdata(
    data_directory: str | Path,
    max_samples_per_file: int | None = 1000,
    file_pattern: str | None = None,
    *,
    strict: bool = False,
) -> List[TrainingExample]:
    """Load revised sequence traces, with compatibility for the old runner schema.

    Supported inputs:
      * a JSON array of traces
      * a single JSON trace object
      * JSONL/NDJSON (one trace object per line)
      * a directory containing .json/.jsonl/.ndjson files

    The revised snake_case TrainingExample fields are preferred. Legacy aliases used
    by the previous runner (input/output/typeInput/typeOutput) are still accepted.
    """
    data_path = Path(data_directory)
    if not data_path.exists():
        raise FileNotFoundError(f"Data not found: {data_directory}")

    training_examples: list[TrainingExample] = []
    loaded_files = 0
    failed_files = 0

    print(f"Loading training data from {data_path}")
    print(f"Max samples per file: {max_samples_per_file or 'unlimited'}")
    print("-" * 60)

    files = _training_files(data_path, file_pattern)
    if not files:
        pattern_text = file_pattern or "*.json / *.jsonl / *.ndjson"
        raise FileNotFoundError(f"No training files matching {pattern_text!r} in {data_path}")

    for json_file in files:
        print(f"Loading {json_file.name}...", end=" ")
        try:
            rows = _read_json_rows(json_file)
            sampled_rows = _sample_evenly(rows, max_samples_per_file)
            if len(sampled_rows) < len(rows):
                print(f"(limiting to {len(sampled_rows)} of {len(rows)} samples)")
            else:
                print(f"({len(sampled_rows)} samples)")

            file_examples: list[TrainingExample] = []
            for index, row in enumerate(sampled_rows):
                try:
                    file_examples.append(_normalise_trace(row, json_file.name))
                except Exception as exc:
                    raise ValueError(f"trace {index}: {exc}") from exc

            training_examples.extend(file_examples)
            loaded_files += 1
        except Exception as exc:
            failed_files += 1
            print(f"ERROR: {type(exc).__name__}: {exc}")
            if strict:
                raise

    print("-" * 60)
    print(
        f"Loaded {len(training_examples)} total samples from {loaded_files} files"
        + (f" ({failed_files} failed)" if failed_files else "")
    )

    if not training_examples:
        raise ValueError("No valid training examples were loaded")
    return training_examples


def save_simple_genome(genome: Any, output_file: str | Path, execution_time: float) -> None:
    """Save a generic JSON-serialisable genome payload."""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump({"genome": genome, "execution_time": execution_time}, handle, indent=4)
    print(f"Genome saved to {output_path}")


def save_genome(genome: Any, output_path: str | Path, execution_time: float) -> None:
    """Save a learned PushGP genome using the learner's canonical serializer."""
    if genome is None:
        raise RuntimeError("Evolution did not return a genome")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    genome_data = {
        "fitness": genome.fitness,
        "accuracy": genome.accuracy,
        "complexity_penalty": genome.complexity_penalty,
        "method_accuracies": genome.method_accuracies,
        "executionTime": execution_time,
        "case_errors": list(getattr(genome, "case_errors", []) or []),
        "evaluation_failures": list(getattr(genome, "evaluation_failures", []) or []),
        "methods": {},
    }

    for method_name, program in genome.methods.items():
        genome_data["methods"][method_name] = {
            "program": serialize_program(program.code),
            "accuracy": genome.method_accuracies.get(method_name, 0.0),
            "complexity": genome._count_instructions(program.code),
        }

    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(genome_data, handle, indent=2, allow_nan=False)

    print(f"PushGP genome saved to: {output_path}")


def infer_type_from_filename(filename: str) -> str:
    """Infer a default data-structure type for legacy traces."""
    filename_lower = Path(filename).name.lower()

    if any(part in filename_lower for part in ("hashmap", "treemap", "map")):
        return "map"
    if any(part in filename_lower for part in ("hashset", "treeset", "set")):
        return "set"
    if "stack" in filename_lower:
        return "stack"
    if "queue" in filename_lower or "deque" in filename_lower:
        return "queue"
    return "list"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="PushGP sequence learner for Java collection/data-structure traces"
    )
    parser.add_argument("data_directory", help="Training JSON/JSONL file or directory")
    parser.add_argument("--population", type=int, default=200, help="Population size")
    parser.add_argument("--generations", type=int, default=200, help="Number of generations")
    parser.add_argument("--output", default="pushgp_genome.json", help="Output genome JSON")
    parser.add_argument(
        "--profile",
        default="java_ds_full",
        choices=(
            "primitives_full",
            "ds_smt_minimal",
            "java_ds_minimal",
            "java_ds_full",
            "ds_full",
            "collections_full",
        ),
        help="Push instruction profile (default: java_ds_full)",
    )
    parser.add_argument("--processes", type=int, default=None, help="Parallel worker count")
    parser.add_argument("--log-every", type=int, default=25, help="Log every N generations")
    parser.add_argument("--max-steps", type=int, default=None, help="Max interpreter steps per call")
    parser.add_argument("--max-samples-per-file", type=int, default=10000)
    parser.add_argument("--file-pattern", default=None, help="Optional glob when data_directory is a directory")
    parser.add_argument("--strict-loader", action="store_true", help="Stop on the first malformed training file")

    # New evolution controls exposed by the revised learner.
    parser.add_argument("--no-improve-generations", type=int, default=100)
    parser.add_argument("--random-seed", type=int, default=None)
    parser.add_argument("--smart-initialization-probability", type=float, default=0)
    parser.add_argument(
        "--selection",
        default="tournament",
        choices=("tournament", "lexicase", "epsilon_lexicase"),
    )
    parser.add_argument("--tournament-size", type=int, default=5)
    parser.add_argument("--lexicase-cases", type=int, default=40)
    parser.add_argument("--crossover-rate", type=float, default=0.5)
    parser.add_argument("--elite-fraction", type=float, default=0.1)
    parser.add_argument("--diversity-interval", type=int, default=10)
    parser.add_argument("--diversity-threshold", type=float, default=0.3)
    parser.add_argument("--base-mutation-rate", type=float, default=0.4)
    parser.add_argument("--max-program-atoms", type=int, default=64)
    parser.add_argument("--max-program-depth", type=int, default=6)
    parser.add_argument(
        "--no-parallel-fallback",
        action="store_true",
        help="Raise instead of falling back to serial evaluation when multiprocessing fails",
    )

    # Revised fitness configuration.
    parser.add_argument("--complexity-weight", type=float, default=0.001)
    parser.add_argument("--argument-use-weight", type=float, default=0.1)
    parser.add_argument("--state-weight", type=float, default=0.1)
    parser.add_argument("--correctness-tolerance", type=float, default=0.01)

    # Kept so old command lines do not break; the old runner never used this value.
    parser.add_argument("--test-examples", type=int, default=15, help=argparse.SUPPRESS)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _build_parser().parse_args(list(argv) if argv is not None else None)

    training_data = loadtrainingdata(
        args.data_directory,
        max_samples_per_file=args.max_samples_per_file,
        file_pattern=args.file_pattern,
        strict=args.strict_loader,
    )

    evaluation_config = EvaluationConfig(
        complexity_weight=args.complexity_weight,
        argument_use_weight=args.argument_use_weight,
        state_weight=args.state_weight,
        correctness_tolerance=args.correctness_tolerance,
    )

    start_time = time.time()
    best_genome = run_pushgp_evolution(
        training_data=training_data,
        population_size=args.population,
        generations=args.generations,
        no_improve_generations=args.no_improve_generations,
        profile=args.profile,
        processes=args.processes,
        log_every=args.log_every,
        max_steps=args.max_steps,
        random_seed=args.random_seed,
        smart_initialization_probability=args.smart_initialization_probability,
        selection=args.selection,
        tournament_size=args.tournament_size,
        lexicase_cases=args.lexicase_cases,
        crossover_rate=args.crossover_rate,
        elite_fraction=args.elite_fraction,
        diversity_interval=args.diversity_interval,
        diversity_threshold=args.diversity_threshold,
        base_mutation_rate=args.base_mutation_rate,
        max_program_atoms=args.max_program_atoms,
        max_program_depth=args.max_program_depth,
        evaluation_config=evaluation_config,
        parallel_fallback=not args.no_parallel_fallback,
    )
    evolution_time = time.time() - start_time
    print(f"Evolution completed in {evolution_time:.2f} seconds")

    save_genome(best_genome, args.output, evolution_time)
    print(f"Best genome saved to {args.output}")
    

    try:
        # First try the sound/strict translation.
        module = export_genome_to_smt(
            genome=best_genome,
            output_path="pushgp_model.smt2",
            training_data=training_data,
            config=SMTExportConfig(
                strict=True,
                max_steps=256,
                max_paths=256,
            ),
            manifest_path="pushgp_model_manifest.json",
        )
    
        print("Strict SMT export successful.")
    
    except UnsupportedInstructionError as exc:
        print(f"Strict SMT export failed: {exc}")
        print("Retrying with unsupported instructions treated as no-ops...")
    
        module = export_genome_to_smt(
            genome=best_genome,
            output_path=args.output.replace(".json", ".smt2"),
            training_data=training_data,
            config=SMTExportConfig(
                strict=False,
                max_steps=256,
                max_paths=256,
            ),
            manifest_path=args.output.replace(".json", "_manifest.json"),
        )
    
        print("Permissive SMT export successful.")
    
        for warning in module.warnings:
            print("WARNING:", warning)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
