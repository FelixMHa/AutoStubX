from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class TrainingExample:
    initial_state: dict[int, Any]
    data_structure_type: str
    sequence: list[str]
    input_args: list[list[Any]]
    type_inputs: list[list[str]]
    type_outputs: list[str]
    expected_outputs: list[Any]
    receiver_refs: list[int] = field(default_factory=list)
    target_class: str | None = None
    expected_final_state: Any = None


_ALIGNED_FIELDS = (
    "receiver_refs",
    "input_args",
    "type_inputs",
    "type_outputs",
    "expected_outputs",
)


def load_training_examples(path: str | Path) -> list[TrainingExample]:
    with Path(path).open("r", encoding="utf-8") as handle:
        rows = json.load(handle)  # Your Java generator writes one JSON array.

    if not isinstance(rows, list):
        raise ValueError("Training file must contain a JSON array")

    examples: list[TrainingExample] = []

    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"Trace {index} is not a JSON object")

        sequence = row.get("sequence")
        if not isinstance(sequence, list) or not sequence:
            raise ValueError(f"Trace {index} has no method sequence")

        call_count = len(sequence)

        row.setdefault("receiver_refs", [0] * call_count)
        row.setdefault("target_class", None)
        row.setdefault("expected_final_state", None)

        for field_name in _ALIGNED_FIELDS:
            value = row.get(field_name)
            if not isinstance(value, list) or len(value) != call_count:
                actual = len(value) if isinstance(value, list) else "missing"
                raise ValueError(
                    f"Trace {index}: {field_name} has length {actual}; "
                    f"expected {call_count}"
                )

        initial_state = row.get("initial_state")
        if not isinstance(initial_state, dict):
            raise ValueError(f"Trace {index} has no valid initial_state")

        # JSON object keys are strings; the runtime uses numeric reference IDs.
        row["initial_state"] = {
            int(ref_id): value
            for ref_id, value in initial_state.items()
        }

        examples.append(TrainingExample(**row))

    return examples