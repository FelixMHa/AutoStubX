from __future__ import annotations

import copy
import math
import random
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from trainingexample import TrainingExample
else:
    # The class is only needed for annotations. Avoid a runtime/circular import while
    # keeping ``typing.get_type_hints`` and legacy imports functional.
    TrainingExample = Any


class _MissingResult:
    """Sentinel used to distinguish no result from a Java ``null`` result."""

    __slots__ = ()

    def __repr__(self) -> str:
        return "MISSING_RESULT"

    def __copy__(self) -> "_MissingResult":
        return self

    def __deepcopy__(self, memo: Dict[int, Any]) -> "_MissingResult":
        return self

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _MissingResult)

    def __hash__(self) -> int:
        return hash(_MissingResult)

    def __reduce__(self):
        return (_get_missing_result, ())


MISSING_RESULT = _MissingResult()


def _get_missing_result() -> _MissingResult:
    return MISSING_RESULT


@dataclass(frozen=True)
class HeapReference:
    """Typed reference value used when a reference must not be confused with an int."""

    ref_id: int


class PushState:
    """Mutable Push interpreter state.

    Primitive/code stacks are transient for a single method invocation. ``heap`` and
    ``next_ref_id`` are persistent across all calls of one training sequence.

    The public attributes from the original implementation are intentionally kept so
    existing mutation, fitness, and code-generation code can continue to use them.
    ``data_structure_stack`` and ``map_storage`` are compatibility properties backed
    by the currently active heap object.
    """

    def __init__(self, max_steps: int = 150):
        if max_steps <= 0:
            raise ValueError("max_steps must be greater than zero")

        # Core Push stacks.
        self.integer_stack: List[int] = []
        self.boolean_stack: List[bool] = []
        self.string_stack: List[str] = []
        self.float_stack: List[float] = []
        self.object_stack: List[Any] = []
        self.value_stack: List[Any] = []
        self.exec_stack: List[Any] = []
        self.error_stack: List[str] = []
        self.diagnostics: List[str] = []

        # Persistent abstract heap.
        self.heap: Dict[int, Dict[str, Any]] = {}
        self.next_ref_id: int = 0
        self.ref_stack: List[int] = []
        self.active_ref: Optional[int] = None

        # Current-call context. Expected outputs are deliberately not stored here.
        self.current_method_name: Optional[str] = None
        self.current_args: List[Any] = []
        self.current_arg_types: List[str] = []

        # Backward-compatible result field plus an explicit presence bit. Keeping
        # ``result`` as None preserves callers that inspected it directly.
        self.result: Any = None
        self.result_is_set: bool = False

        # Execution accounting.
        self.step_count: int = 0
        self.max_steps: int = max_steps
        self.noop_count: int = 0
        self.instruction_error_count: int = 0
        self.halted: bool = False

    def copy(self) -> "PushState":
        """Return a deep copy suitable for isolated candidate evaluation."""
        new_state = PushState(max_steps=self.max_steps)
        for name in (
            "integer_stack",
            "boolean_stack",
            "string_stack",
            "float_stack",
            "object_stack",
            "value_stack",
            "exec_stack",
            "error_stack",
            "diagnostics",
            "heap",
            "ref_stack",
            "current_args",
            "current_arg_types",
        ):
            setattr(new_state, name, copy.deepcopy(getattr(self, name)))

        new_state.next_ref_id = self.next_ref_id
        new_state.active_ref = self.active_ref
        new_state.current_method_name = self.current_method_name
        new_state.result = copy.deepcopy(self.result)
        new_state.result_is_set = self.result_is_set
        new_state.step_count = self.step_count
        new_state.noop_count = self.noop_count
        new_state.instruction_error_count = self.instruction_error_count
        new_state.halted = self.halted
        return new_state

    def begin_call(
        self,
        method_name: Optional[str] = None,
        args: Optional[Iterable[Any]] = None,
        arg_types: Optional[Iterable[str]] = None,
        receiver_ref: Optional[int] = None,
    ) -> None:
        """Reset transient state while preserving the abstract heap."""
        self.clear_temporary_stacks()
        self.current_method_name = method_name
        self.current_args = list(args or [])
        self.current_arg_types = list(arg_types or [])
        self.result = None
        self.result_is_set = False
        self.step_count = 0
        self.noop_count = 0
        self.instruction_error_count = 0
        self.halted = False

        if receiver_ref is not None:
            self.set_active_ref(receiver_ref)
        elif self.active_ref is None and self.heap:
            self.active_ref = min(self.heap)

        if self.active_ref is not None:
            self.ref_stack.append(self.active_ref)

    def clear_temporary_stacks(self) -> None:
        """Clear all per-call stacks, including errors from the previous call."""
        self.integer_stack.clear()
        self.boolean_stack.clear()
        self.string_stack.clear()
        self.float_stack.clear()
        self.object_stack.clear()
        self.value_stack.clear()
        self.exec_stack.clear()
        self.error_stack.clear()
        self.diagnostics.clear()
        self.ref_stack.clear()

    def value_stacks(self) -> List[List[Any]]:
        """Return typed value stacks in the legacy ``*_ANY`` priority order."""
        return [
            self.string_stack,
            self.integer_stack,
            self.boolean_stack,
            self.float_stack,
            self.object_stack,
        ]

    def try_pop_from_any_stack(self) -> tuple[bool, Any]:
        """Pop a legacy typed value, preserving the active receiver reference."""
        for stack in self.value_stacks():
            if stack:
                return True, stack.pop()

        # A receiver ref is kept at ref_stack[0]. Additional refs are values.
        if len(self.ref_stack) > 1:
            return True, HeapReference(self.ref_stack.pop())
        if self.ref_stack and self.ref_stack[-1] != self.active_ref:
            return True, HeapReference(self.ref_stack.pop())
        return False, None

    def pop_from_any_stack(self) -> Any:
        """Backward-compatible wrapper; ``None`` still means missing or Java null."""
        found, value = self.try_pop_from_any_stack()
        return value if found else None

    def _remove_typed_duplicate(self, value: Any) -> None:
        """Remove the right-most typed copy created by ``push_argument``."""
        if isinstance(value, HeapReference):
            for index in range(len(self.ref_stack) - 1, 0, -1):
                if self.ref_stack[index] == value.ref_id:
                    self.ref_stack.pop(index)
                    return
            return

        if value is None:
            target_stack = self.object_stack
        elif isinstance(value, bool):
            target_stack = self.boolean_stack
        elif isinstance(value, int):
            target_stack = self.integer_stack
        elif isinstance(value, float):
            target_stack = self.float_stack
        elif isinstance(value, str):
            target_stack = self.string_stack
        else:
            target_stack = self.object_stack

        for index in range(len(target_stack) - 1, -1, -1):
            try:
                matches = target_stack[index] is value or target_stack[index] == value
            except Exception:
                matches = target_stack[index] is value
            if matches:
                target_stack.pop(index)
                return

    def try_pop_domain_value(self) -> tuple[bool, Any]:
        """Pop an ordered argument/domain value and consume its typed duplicate."""
        if self.value_stack:
            value = self.value_stack.pop()
            self._remove_typed_duplicate(value)
            return True, value
        return self.try_pop_from_any_stack()

    def push_to_appropriate_stack(self, value: Any) -> None:
        """Push a Python/abstract-Java value to its corresponding Push stack."""
        if isinstance(value, HeapReference):
            self.ref_stack.append(value.ref_id)
        elif value is None:
            self.object_stack.append(None)
        elif isinstance(value, bool):  # bool must be tested before int
            self.boolean_stack.append(value)
        elif isinstance(value, int):
            self.integer_stack.append(value)
        elif isinstance(value, float):
            self.float_stack.append(value)
        elif isinstance(value, str):
            self.string_stack.append(value)
        else:
            self.object_stack.append(value)

    def push_argument(self, value: Any) -> None:
        """Push an argument both to typed stacks and the ordered domain stack."""
        self.value_stack.append(value)
        self.push_to_appropriate_stack(value)

    def set_result(self, value: Any, *, halt: bool = False) -> None:
        self.result = value
        self.result_is_set = True
        if halt:
            self.halted = True

    def record_error(self, code: str = "error", detail: Optional[str] = None) -> None:
        """Record a semantic error without throwing out of GP evaluation."""
        self.error_stack.append("error")
        self.diagnostics.append(code if detail is None else f"{code}: {detail}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "integer_stack": self.integer_stack.copy(),
            "boolean_stack": self.boolean_stack.copy(),
            "string_stack": self.string_stack.copy(),
            "float_stack": self.float_stack.copy(),
            "object_stack": copy.deepcopy(self.object_stack),
            "value_stack": copy.deepcopy(self.value_stack),
            "exec_stack": copy.deepcopy(self.exec_stack),
            "error_stack": self.error_stack.copy(),
            "diagnostics": self.diagnostics.copy(),
            "heap": copy.deepcopy(self.heap),
            "next_ref_id": self.next_ref_id,
            "ref_stack": self.ref_stack.copy(),
            "active_ref": self.active_ref,
            "result": self.result,
            "result_is_set": self.result_is_set,
            "step_count": self.step_count,
            "max_steps": self.max_steps,
            "noop_count": self.noop_count,
            "instruction_error_count": self.instruction_error_count,
            "halted": self.halted,
            "current_method_name": self.current_method_name,
            "current_args": copy.deepcopy(self.current_args),
            "current_arg_types": self.current_arg_types.copy(),
        }

    @staticmethod
    def _normalise_object_type(obj_type: Optional[str], data: Any) -> str:
        raw = (obj_type or "").lower()
        if "map" in raw or isinstance(data, dict):
            return "map"
        if "set" in raw or isinstance(data, set):
            return "set"
        if "list" in raw or "arraylist" in raw or isinstance(data, (list, tuple)):
            return "list"
        return raw or type(data).__name__.lower()

    def alloc(
        self,
        data: Any,
        obj_type: str = "list",
        *,
        ref_id: Optional[int] = None,
        push_ref: bool = True,
        fields: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Allocate an abstract heap object and return its integer reference id."""
        if ref_id is None:
            ref_id = self.next_ref_id
            while ref_id in self.heap:
                ref_id += 1
        elif ref_id < 0:
            raise ValueError("ref_id must be non-negative")

        self.heap[ref_id] = {
            "data": data,
            "type": self._normalise_object_type(obj_type, data),
            "fields": dict(fields or {}),
        }
        self.next_ref_id = max(self.next_ref_id, ref_id + 1)
        if self.active_ref is None:
            self.active_ref = ref_id
        if push_ref:
            self.ref_stack.append(ref_id)
        return ref_id

    def get(self, ref: int) -> Optional[Dict[str, Any]]:
        return self.heap.get(ref)

    def get_data(self, ref: Optional[int] = None) -> Any:
        target = self.active_ref if ref is None else ref
        entry = self.heap.get(target) if target is not None else None
        return None if entry is None else entry.get("data")

    def set_active_ref(self, ref_id: int) -> None:
        if ref_id not in self.heap:
            raise KeyError(f"Unknown heap reference: {ref_id}")
        self.active_ref = ref_id

    def _ensure_active_entry(self, default_type: str = "list") -> Dict[str, Any]:
        if self.active_ref is None or self.active_ref not in self.heap:
            default_data: Any
            if default_type == "map":
                default_data = {}
            elif default_type == "set":
                default_data = set()
            else:
                default_data = []
            ref_id = self.alloc(default_data, default_type, push_ref=False)
            self.active_ref = ref_id
        return self.heap[self.active_ref]

    @property
    def data_structure_stack(self) -> Any:
        """Legacy alias for the active heap object's backing data."""
        return self._ensure_active_entry("list")["data"]

    @data_structure_stack.setter
    def data_structure_stack(self, value: Any) -> None:
        entry = self._ensure_active_entry("list")
        entry["data"] = value
        entry["type"] = self._normalise_object_type(entry.get("type"), value)

    @property
    def map_storage(self) -> Dict[Any, Any]:
        """Legacy alias for the active map object's backing dictionary."""
        entry = self._ensure_active_entry("map")
        if not isinstance(entry["data"], dict):
            raise TypeError("The active heap object is not map-backed")
        return entry["data"]

    @map_storage.setter
    def map_storage(self, value: Dict[Any, Any]) -> None:
        if not isinstance(value, dict):
            raise TypeError("map_storage must be a dict")
        entry = self._ensure_active_entry("map")
        entry["data"] = value
        entry["type"] = "map"

    @property
    def set_storage(self) -> set[Any]:
        entry = self._ensure_active_entry("set")
        if not isinstance(entry["data"], set):
            raise TypeError("The active heap object is not set-backed")
        return entry["data"]

    @set_storage.setter
    def set_storage(self, value: set[Any]) -> None:
        if not isinstance(value, set):
            raise TypeError("set_storage must be a set")
        entry = self._ensure_active_entry("set")
        entry["data"] = value
        entry["type"] = "set"


@dataclass
class ObjectSummary:
    """Compact observable summary used by fitness/state-comparison code."""

    size: int = 0
    keys: frozenset[Any] = field(default_factory=frozenset)
    field_hashes: Dict[str, Any] = field(default_factory=dict)
    obj_type: str = "generic"

    def __init__(
        self,
        size: int = 0,
        keys: Optional[Iterable[Any]] = None,
        field_hashes: Optional[Dict[str, Any]] = None,
        obj_type: str = "generic",
    ) -> None:
        self.size = int(size)
        self.keys = frozenset(keys or [])
        self.field_hashes = dict(field_hashes or {})
        self.obj_type = obj_type


class PushProgram:
    """A Push program represented by instructions and nested code blocks."""

    def __init__(self, code: Optional[List[Union[PushInstruction, List[Any]]]]):
        self.code: List[Any] = list(code or [])

    def execute(self, state: PushState) -> PushState:
        """Execute with bounded steps and Push-style failure tolerance.

        Missing operands remain no-ops inside individual instructions. Unexpected
        Python exceptions are recorded for diagnostics but do not abort evaluation.
        """
        if self.code:
            state.exec_stack.extend(reversed(self.code))

        while (
            state.exec_stack
            and state.step_count < state.max_steps
            and not state.halted
        ):
            instruction = state.exec_stack.pop()
            try:
                if isinstance(instruction, PushInstruction):
                    instruction.execute(state)
                elif isinstance(instruction, (list, tuple)):
                    state.exec_stack.extend(reversed(instruction))
                else:
                    # Push literals are valid atoms in Push programs.
                    state.push_to_appropriate_stack(instruction)
            except Exception as exc:  # GP individuals must remain evaluable.
                state.instruction_error_count += 1
                state.diagnostics.append(
                    f"INSTRUCTION_EXCEPTION[{instruction!r}]: "
                    f"{type(exc).__name__}: {exc}"
                )
            finally:
                state.step_count += 1

        if state.exec_stack and state.step_count >= state.max_steps:
            state.record_error("STEP_LIMIT_EXCEEDED")

        return state


class PushGPGenome:
    """ genome with better complexity calculation"""
    
    def __init__(self):
        self.methods: Dict[str, PushProgram] = {}
        self.fitness = float('inf')
        self.accuracy = 0.0
        self.method_accuracies: Dict[str, float] = {}
        self.complexity_penalty = 0.0
        self._behavioral_signature: Optional[tuple] = None
        self.case_errors: List[float] = []
    
    def add_method(self, method_name: str, program: PushProgram) -> None:
        """Add or replace a method program and invalidate cached behaviour."""
        self.methods[method_name] = program
        self.invalidate_signature()
    
    def get_complexity_penalty(self) -> float:
        """Calculate complexity penalty"""
        total_complexity = 0
        for program in self.methods.values():
            total_complexity += self._count_instructions(program.code)
        return total_complexity
    
    def _count_instructions(self, code: Iterable[Any]) -> int:
        """Recursively count atoms while treating each nested block structurally."""
        count = 0
        for item in code:
            if isinstance(item, (list, tuple)):
                count += self._count_instructions(item)
            else:
                count += 1
        return count
    
    def copy(self):
        """Deep copy genome"""
        new_genome = PushGPGenome()
        for method_name, program in self.methods.items():
            new_program = PushProgram(copy.deepcopy(program.code))
            new_genome.methods[method_name] = new_program
        new_genome.fitness = self.fitness
        new_genome.accuracy = self.accuracy
        new_genome.method_accuracies = self.method_accuracies.copy()
        new_genome.complexity_penalty = self.complexity_penalty
        new_genome._behavioral_signature = copy.deepcopy(self._behavioral_signature)
        new_genome.case_errors = self.case_errors.copy()
        return new_genome

    def invalidate_signature(self):
        """Call after any mutation or crossover."""
        self._behavioral_signature = None



def _as_instruction_dict(instructions: Iterable[PushInstruction]) -> Dict[str, PushInstruction]:
    """Build the name lookup used by existing mutation/evolution code."""
    return {instruction.name: instruction for instruction in instructions}


def create_pushgp_instruction_set(profile: str = "primitives_full") -> Dict[str, PushInstruction]:
    """Create an instruction set while preserving the two original profiles.

    Existing profile contents remain intentionally stable for compatibility with
    mutation, serialization, SMT, and code-generation code that may whitelist their
    instruction names. The new ``java_ds_full``/``java_ds_minimal`` profiles expose
    the additional call, result, map, set, and heap-oriented instructions.
    """
    profile = (profile or "primitives_full").strip().lower()

    original_ds_minimal: List[PushInstruction] = [
        INT_ADD(), INT_SUB(), INT_EQ(), INT_LT(),
        INT_CONST(-1), INT_CONST(0), INT_CONST(1),
        BOOL_AND(), BOOL_OR(), BOOL_NOT(),
        BOOL_CONST(True), BOOL_CONST(False),
        DUP_ANY(), SWAP_ANY(), POP_ANY(), ITE(),
        DS_SIZE(), DS_CLEAR(), DS_GET_INDEX(), DS_SET_INDEX(),
        DS_INSERT_AT_INDEX(), DS_REMOVE_INDEX(),
        DS_INDEX_OF(), DS_LAST_INDEX_OF(),
    ]

    original_primitives: List[PushInstruction] = [
        INT_ADD(), INT_SUB(), INT_MUL(), INT_DIV(),
        INT_EQ(), INT_LT(), INT_NEG(), INT_ABS(), ITE_INT(),
        INT_COMPARE_RANGE(),
    ]
    original_primitives.extend(INT_CONST(value) for value in range(-4, 7))
    original_primitives.extend([
        FLOAT_ADD(), FLOAT_SUB(), FLOAT_MUL(), FLOAT_DIV(),
        FLOAT_NEG(), FLOAT_ABS(), FLOAT_FLOOR(), FLOAT_COS(),
        FLOAT_LT(), FLOAT_EQ(), ITE_FLOAT(), FLOAT_TO_STR(), STR_TO_FLOAT(),
        FLOAT_CONST(0.0), FLOAT_CONST(1.0), FLOAT_CONST(-1.0),
        BOOL_AND(), BOOL_OR(), BOOL_NOT(), BOOL_XOR(),
        BOOL_CONST(True), BOOL_CONST(False),
        STR_CONCAT(), STR_EQ(), STR_LEN(), STR_CONTAINS(),
        STR_INDEX_OF(), STR_SUBSTRING(), STR_REPLACE(), STR_REPLACE_ALL(),
        STR_TO_INT(), INT_TO_STR(), ASCII_TO_STR(), STR_TO_ASCII(), STR_ITE(),
        STR_CONST(""), STR_CONST(" "),
        ERC_INT(), ERC_FLOAT(),
        DUP_ANY(), SWAP_ANY(), POP_ANY(),
    ])

    if profile == "ds_smt_minimal":
        return _as_instruction_dict(original_ds_minimal)
    if profile not in {
        "java_ds_full",
        "java_ds_minimal",
        "ds_full",
        "collections_full",
    }:
        return _as_instruction_dict(original_primitives)

    call_and_result: List[PushInstruction] = [
        VALUE_FROM_ANY(), ARG_COUNT(),
        ARG_PUSH(0), ARG_PUSH(1), ARG_PUSH(2), ARG_PUSH(3),
        ACTIVE_REF(), NULL_CONST(),
        RESULT_FROM_ANY(), RESULT_NULL(), RESULT_ERROR(),
        EXEC_IF(),
    ]
    domain_operations: List[PushInstruction] = [
        DS_SIZE(), DS_IS_EMPTY(), DS_CLEAR(),
        DS_GET_INDEX(), DS_SET_INDEX(), DS_INSERT_AT_INDEX(), DS_APPEND(),
        DS_REMOVE_INDEX(), DS_PEEK_LAST(), DS_POP_LAST(),
        DS_LAST_INDEX(), DS_FIRST_INDEX(), DS_INDEX_OF(), DS_LAST_INDEX_OF(),
        DS_CONTAINS(),
        MAP_SIZE(), MAP_CLEAR(), MAP_PUT(), MAP_GET(), MAP_REMOVE(),
        MAP_CONTAINS_KEY(),
        SET_SIZE(), SET_CLEAR(), SET_ADD(), SET_REMOVE(), SET_CONTAINS(),
    ]

    if profile == "java_ds_minimal":
        enhanced_minimal = original_ds_minimal + call_and_result + [
            DS_IS_EMPTY(), DS_APPEND(), DS_PEEK_LAST(), DS_POP_LAST(),
            DS_LAST_INDEX(), DS_FIRST_INDEX(), DS_CONTAINS(),
            MAP_SIZE(), MAP_CLEAR(), MAP_PUT(), MAP_GET(), MAP_REMOVE(),
            MAP_CONTAINS_KEY(),
            SET_SIZE(), SET_CLEAR(), SET_ADD(), SET_REMOVE(), SET_CONTAINS(),
        ]
        return _as_instruction_dict(enhanced_minimal)

    extra_primitives: List[PushInstruction] = [
        INT_MOD(), INT_GT(), BOOL_TO_INT(), ITE_BOOL(),
        FLOAT_GT(), FLOAT_IS_NAN(), FLOAT_IS_INF(), FLOAT_IS_FINITE(),
        STR_CHAR_AT(), STR_STARTS_WITH(), STR_TO_LOWER(), STR_TO_UPPER(),
        STR_TRIM(), EXEC_DO_TIMES(),
    ]
    return _as_instruction_dict(
        original_primitives + extra_primitives + call_and_result + domain_operations
    )

def create__pushgp_instruction_set(profile: str = "primitives_full") -> Dict[str, PushInstruction]:
    """Backward-compatible alias retaining the original double underscore."""
    return create_pushgp_instruction_set(profile)


class PushGPInterpreter:
    """Push interpreter and sequence-level Java-library model evaluator."""

    INTEGER_TYPES = {
        "int", "java.lang.integer", "byte", "java.lang.byte", "short",
        "java.lang.short", "long", "java.lang.long", "i", "b", "s", "j",
    }
    FLOAT_TYPES = {
        "float", "java.lang.float", "double", "java.lang.double", "f", "d",
    }
    BOOLEAN_TYPES = {"boolean", "java.lang.boolean", "bool", "z"}
    STRING_TYPES = {"java.lang.string", "string", "str", "charsequence"}
    CHAR_TYPES = {"char", "java.lang.character", "c"}

    def __init__(self, profile: str = "primitives_full", max_steps: int = 150):
        if max_steps <= 0:
            raise ValueError("max_steps must be greater than zero")
        self.profile = profile
        self.max_steps = max_steps
        self.instruction_set = create_pushgp_instruction_set(profile)
        self.instruction_list = list(self.instruction_set.values())

    @staticmethod
    def _normalise_type_name(type_name: Optional[str]) -> str:
        if type_name is None:
            return ""
        value = str(type_name).strip().lower().replace("/", ".")
        if value.startswith("l") and value.endswith(";"):
            value = value[1:-1]
        return value

    @staticmethod
    def _coerce_boolean(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalised = value.strip().lower()
            if normalised in {"true", "1", "yes"}:
                return True
            if normalised in {"false", "0", "no", ""}:
                return False
            raise ValueError(f"Cannot parse boolean value {value!r}")
        return bool(value)

    def _coerce_argument(self, state: PushState, arg: Any, type_name: str) -> Any:
        """Convert JSON-loaded Java values into the abstract runtime representation."""
        t = self._normalise_type_name(type_name)

        if isinstance(arg, HeapReference):
            return arg
        if isinstance(arg, dict) and str(arg.get("kind", "")).lower() == "reference":
            ref_id = arg.get("id", arg.get("ref_id"))
            if ref_id is not None:
                return HeapReference(int(ref_id))
        if arg is None:
            return None

        try:
            if t in self.INTEGER_TYPES:
                return int(arg)
            if t in self.FLOAT_TYPES:
                return float(arg)
            if t in self.BOOLEAN_TYPES:
                return self._coerce_boolean(arg)
            if t in self.CHAR_TYPES:
                if isinstance(arg, str):
                    return arg[:1]
                return chr(int(arg))
            if t in self.STRING_TYPES:
                return str(arg)

            if "map" in t or isinstance(arg, dict):
                ref_id = state.alloc(copy.deepcopy(arg), "map", push_ref=False)
                return HeapReference(ref_id)
            if "set" in t or isinstance(arg, set):
                ref_id = state.alloc(copy.deepcopy(arg), "set", push_ref=False)
                return HeapReference(ref_id)
            if "list" in t or "arraylist" in t or isinstance(arg, (list, tuple)):
                ref_id = state.alloc(list(copy.deepcopy(arg)), "list", push_ref=False)
                return HeapReference(ref_id)
        except (TypeError, ValueError, OverflowError) as exc:
            state.record_error("ARGUMENT_COERCION_FAILED", str(exc))
            return arg

        return arg

    def push_args_to_stacks(
        self,
        state: PushState,
        args: List[Any],
        types: Optional[List[str]] = None,
    ) -> None:
        """Push every argument; shorter type metadata no longer drops trailing args."""
        args = list(args or [])
        types = list(types or [])
        resolved_args: List[Any] = []

        for index, arg in enumerate(args):
            type_name = types[index] if index < len(types) else ""
            resolved = self._coerce_argument(state, arg, type_name)
            resolved_args.append(resolved)
            state.push_argument(resolved)

        state.current_args = resolved_args
        state.current_arg_types = types

    @staticmethod
    def _freeze_value(value: Any) -> Any:
        """Create a deterministic, equality-friendly snapshot of nested values."""
        if isinstance(value, HeapReference):
            return ("ref", value.ref_id)
        if isinstance(value, dict):
            return tuple(
                sorted(
                    ((repr(key), PushGPInterpreter._freeze_value(item)) for key, item in value.items()),
                    key=lambda pair: pair[0],
                )
            )
        if isinstance(value, (list, tuple)):
            return tuple(PushGPInterpreter._freeze_value(item) for item in value)
        if isinstance(value, set):
            return tuple(sorted((PushGPInterpreter._freeze_value(item) for item in value), key=repr))
        try:
            hash(value)
            return value
        except TypeError:
            return repr(value)

    def to_summary(self, obj: Any) -> ObjectSummary:
        """Convert an abstract heap entry or value into an observable summary."""
        obj_type: Optional[str] = None
        fields: Dict[str, Any] = {}
        if isinstance(obj, dict) and "data" in obj and "type" in obj:
            obj_type = str(obj.get("type") or "unknown")
            fields = dict(obj.get("fields") or {})
            obj = obj.get("data")

        if isinstance(obj, list):
            return ObjectSummary(
                size=len(obj),
                field_hashes={"elements": self._freeze_value(obj), **self._freeze_fields(fields)},
                obj_type=obj_type or "list",
            )
        if isinstance(obj, dict):
            return ObjectSummary(
                size=len(obj),
                keys=obj.keys(),
                field_hashes={"entries": self._freeze_value(obj), **self._freeze_fields(fields)},
                obj_type=obj_type or "map",
            )
        if isinstance(obj, set):
            return ObjectSummary(
                size=len(obj),
                field_hashes={"elements": self._freeze_value(obj), **self._freeze_fields(fields)},
                obj_type=obj_type or "set",
            )
        if obj is None:
            return ObjectSummary(size=0, field_hashes=self._freeze_fields(fields), obj_type=obj_type or "null")
        if isinstance(obj, (int, float, bool, str)):
            return ObjectSummary(
                size=1,
                field_hashes={"value": self._freeze_value(obj), **self._freeze_fields(fields)},
                obj_type=obj_type or type(obj).__name__,
            )
        return ObjectSummary(
            size=0,
            field_hashes={"value": self._freeze_value(obj), **self._freeze_fields(fields)},
            obj_type=obj_type or type(obj).__name__,
        )

    def _freeze_fields(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        return {f"field:{key}": self._freeze_value(value) for key, value in fields.items()}

    @staticmethod
    def _safe_list_attribute(example: Any, name: str) -> List[Any]:
        value = getattr(example, name, None)
        return list(value or [])

    @staticmethod
    def _input_prefix_preserved(initial: List[Any], after: List[Any]) -> bool:
        return not initial or (len(after) >= len(initial) and after[:len(initial)] == initial)

    def execute_sequence(
        self,
        genome: PushGPGenome,
        example: TrainingExample,
    ) -> tuple[List[Any], List[bool], Optional[Dict[str, Any]]]:
        """Execute a method sequence while preserving only its abstract heap."""
        state = PushState(max_steps=self.max_steps)
        step_results: List[Any] = []
        used_inputs: List[bool] = []

        initial_state = getattr(example, "initial_state", None) or {}
        default_type = str(getattr(example, "data_structure_type", "list") or "list")

        for supplied_ref, raw_data in initial_state.items():
            try:
                ref_id = int(supplied_ref)
            except (TypeError, ValueError):
                ref_id = None

            if isinstance(raw_data, dict) and "data" in raw_data and "type" in raw_data:
                data = copy.deepcopy(raw_data.get("data"))
                obj_type = str(raw_data.get("type") or default_type)
                fields = copy.deepcopy(raw_data.get("fields") or {})
            else:
                data = copy.deepcopy(raw_data)
                fields = None
                if isinstance(data, dict):
                    obj_type = "map"
                elif isinstance(data, set):
                    obj_type = "set"
                elif isinstance(data, (list, tuple)):
                    obj_type = "list"
                    data = list(data)
                else:
                    obj_type = default_type

            state.alloc(
                data,
                obj_type,
                ref_id=ref_id,
                push_ref=False,
                fields=fields,
            )

        if not state.heap:
            normalised_default = default_type.lower()
            if "map" in normalised_default:
                state.alloc({}, "map", ref_id=0, push_ref=False)
            elif "set" in normalised_default:
                state.alloc(set(), "set", ref_id=0, push_ref=False)
            else:
                state.alloc([], "list", ref_id=0, push_ref=False)

        default_receiver = 0 if 0 in state.heap else min(state.heap)
        sequence = self._safe_list_attribute(example, "sequence")
        input_args = self._safe_list_attribute(example, "input_args")
        input_types = self._safe_list_attribute(example, "type_inputs")
        output_types = self._safe_list_attribute(example, "type_outputs")
        receiver_refs = self._safe_list_attribute(example, "receiver_refs")

        for index, method_name in enumerate(sequence):
            args = input_args[index] if index < len(input_args) else []
            arg_types = input_types[index] if index < len(input_types) else []
            expected_type = output_types[index] if index < len(output_types) else None
            receiver_ref = receiver_refs[index] if index < len(receiver_refs) else default_receiver
            try:
                receiver_ref = int(receiver_ref)
            except (TypeError, ValueError):
                receiver_ref = default_receiver
            if receiver_ref not in state.heap:
                state.record_error("INVALID_RECEIVER_REFERENCE", str(receiver_ref))
                receiver_ref = default_receiver

            state.begin_call(
                method_name=str(method_name),
                args=args,
                arg_types=arg_types,
                receiver_ref=receiver_ref,
            )
            self.push_args_to_stacks(state, args, arg_types)

            initial_stacks = [copy.deepcopy(stack) for stack in state.value_stacks()]
            initial_domain_values = copy.deepcopy(state.value_stack)
            initial_arg_refs = state.ref_stack[1:].copy()

            program = genome.methods.get(str(method_name))
            if program is not None:
                program.execute(state)
            else:
                state.diagnostics.append(f"MISSING_METHOD_PROGRAM: {method_name}")

            step_results.append(self._extract_result_from_state(state, expected_type))

            typed_preserved = all(
                self._input_prefix_preserved(before, after)
                for before, after in zip(initial_stacks, state.value_stacks())
            )
            domain_preserved = self._input_prefix_preserved(initial_domain_values, state.value_stack)
            refs_preserved = self._input_prefix_preserved(initial_arg_refs, state.ref_stack[1:])
            had_inputs = bool(initial_domain_values or initial_arg_refs)
            inputs_preserved = typed_preserved and domain_preserved and refs_preserved
            used_inputs.append(True if not had_inputs else not inputs_preserved)

        final_obj = state.get(default_receiver)
        return step_results, used_inputs, final_obj

    def _extract_result_from_state(
        self,
        state: PushState,
        expected_type: Optional[str],
    ) -> Any:
        """Extract a candidate result without conflating missing output and null."""
        if state.result_is_set:
            return state.result

        key = self._normalise_type_name(expected_type)
        if not key:
            return None
        if key in {"void", "v", "java.lang.void"}:
            return None
        if key in {"error", "exception", "throw", "thrown"}:
            return "error" if state.error_stack else MISSING_RESULT
        if key in {"null", "none"}:
            return None if state.object_stack and state.object_stack[-1] is None else MISSING_RESULT

        type_map: Dict[str, List[Any]] = {}
        for name in self.INTEGER_TYPES:
            type_map[name] = state.integer_stack
        for name in self.FLOAT_TYPES:
            type_map[name] = state.float_stack
        for name in self.BOOLEAN_TYPES:
            type_map[name] = state.boolean_stack
        for name in self.STRING_TYPES | self.CHAR_TYPES:
            type_map[name] = state.string_stack

        stack = type_map.get(key)
        if stack:
            return stack[-1]

        if key in {
            "object", "java.lang.object", "reference", "ref",
            "list", "java.util.list", "java.util.arraylist",
            "map", "java.util.map", "java.util.hashmap",
            "set", "java.util.set", "java.util.hashset",
        }:
            if state.object_stack:
                return state.object_stack[-1]
            if len(state.ref_stack) > 1:
                return HeapReference(state.ref_stack[-1])
            for candidate_stack in (
                state.string_stack,
                state.integer_stack,
                state.boolean_stack,
                state.float_stack,
            ):
                if candidate_stack:
                    return candidate_stack[-1]

        return MISSING_RESULT

    def random_program(self, max_depth: int = 2, max_length: int = 5) -> List[Any]:
        """Generate a bounded random program with a strong linear-program bias."""
        if not self.instruction_list:
            return []
        max_length = max(1, int(max_length))
        if max_depth <= 0 or random.random() < 0.9:
            return [
                self._get_random_instruction()
                for _ in range(random.randint(1, max_length))
            ]

        program = [
            self._get_random_instruction()
            for _ in range(random.randint(1, min(3, max_length)))
        ]
        program.append(self.random_program(max_depth - 1, min(3, max_length)))
        return program

    def _get_random_instruction(self) -> PushInstruction:
        """Return an instruction, refreshing ephemeral random constants."""
        if not self.instruction_list:
            raise RuntimeError("The selected instruction profile is empty")
        instruction = random.choice(self.instruction_list)
        if isinstance(instruction, (ERC_INT, ERC_FLOAT)):
            return instruction.__class__()
        return instruction

    def _smart_program(self, *names: str) -> Optional[List[PushInstruction]]:
        if all(name in self.instruction_set for name in names):
            return [self.instruction_set[name] for name in names]
        return None

    def create_smart_initial_program(self, method_name: str) -> List[Any]:
        """Create conservative seed programs without assuming a specific profile."""
        method = (method_name or "").lower()
        base = method.split("#", 1)[0]

        if base == "add":
            smart = self._smart_program("DS.APPEND", "BOOL.CONST.True")
            if smart is None:
                smart = self._smart_program(
                    "DS.SIZE", "DS.INSERT.AT.INDEX", "BOOL.CONST.True"
                )
            if smart is not None:
                return smart

        if base == "push":
            smart = self._smart_program("DUP.ANY", "DS.APPEND")
            if smart is None:
                smart = self._smart_program(
                    "DUP.ANY", "DS.SIZE", "DS.INSERT.AT.INDEX"
                )
            if smart is not None:
                return smart

        if base == "pop":
            smart = self._smart_program("DS.POP.LAST")
            if smart is None:
                smart = self._smart_program(
                    "DS.SIZE", "INT.CONST.1", "INT.SUB", "DS.REMOVE.INDEX"
                )
            if smart is not None:
                return smart

        if base == "peek":
            smart = self._smart_program("DS.PEEK.LAST")
            if smart is None:
                smart = self._smart_program(
                    "DS.SIZE", "INT.CONST.1", "INT.SUB", "DS.GET.INDEX"
                )
            if smart is not None:
                return smart

        candidates: Dict[str, tuple[str, ...]] = {
            "empty": ("DS.SIZE", "INT.CONST.0", "INT.EQ"),
            "isempty": ("DS.SIZE", "INT.CONST.0", "INT.EQ"),
            "size": ("DS.SIZE",),
            "clear": ("DS.CLEAR",),
            "get": ("DS.GET.INDEX",),
            "contains": ("DS.CONTAINS",),
        }
        names = candidates.get(base)
        if names:
            smart = self._smart_program(*names)
            if smart is not None:
                return smart
        return self.random_program(max_depth=2, max_length=6)


class PushInstruction:
    """Base class for  Push instructions"""
    
    def __init__(self, name: str):
        self.name = name
    
    def execute(self, state: PushState):
        """Execute instruction on state"""
        raise NotImplementedError
    
    def __repr__(self):
        return self.name
    
    def __eq__(self, other):
        return isinstance(other, PushInstruction) and self.name == other.name
    
    def __hash__(self):
        return hash(self.name)

#  Core Push Instructions
#Integer Instructions
class INT_CONST(PushInstruction):
    def __init__(self, value: int):
        super().__init__(f"INT.CONST.{value}")
        self.value = value

    def execute(self, state: PushState):
        state.integer_stack.append(self.value)


class INT_ADD(PushInstruction):
    def __init__(self):
        super().__init__("INT.ADD")

    def execute(self, state: PushState):
        if len(state.integer_stack) >= 2:
            b = state.integer_stack.pop()
            a = state.integer_stack.pop()
            state.integer_stack.append(a + b)


class INT_SUB(PushInstruction):
    def __init__(self):
        super().__init__("INT.SUB")

    def execute(self, state: PushState):
        if len(state.integer_stack) >= 2:
            b = state.integer_stack.pop()
            a = state.integer_stack.pop()
            state.integer_stack.append(a - b)


class INT_MUL(PushInstruction):
    def __init__(self):
        super().__init__("INT.MUL")

    def execute(self, state: PushState):
        if len(state.integer_stack) >= 2:
            b = state.integer_stack.pop()
            a = state.integer_stack.pop()
            state.integer_stack.append(a * b)


class INT_DIV(PushInstruction):
    def __init__(self):
        super().__init__("INT.DIV")

    def execute(self, state: PushState):
        if len(state.integer_stack) >= 2:
            b = state.integer_stack.pop()
            a = state.integer_stack.pop()
            if b == 0:
                state.record_error("ARITHMETIC_DIVIDE_BY_ZERO")
                return
            # Java integer division truncates toward zero; Python // floors.
            quotient = abs(a) // abs(b)
            state.integer_stack.append(-quotient if (a < 0) ^ (b < 0) else quotient)
        else:
            state.noop_count += 1


class INT_MOD(PushInstruction):
    def __init__(self):
        super().__init__("INT.MOD")

    def execute(self, state: PushState):
        if len(state.integer_stack) >= 2:
            b = state.integer_stack.pop()
            a = state.integer_stack.pop()
            if b == 0:
                state.record_error("ARITHMETIC_DIVIDE_BY_ZERO")
                return
            quotient = abs(a) // abs(b)
            quotient = -quotient if (a < 0) ^ (b < 0) else quotient
            state.integer_stack.append(a - quotient * b)
        else:
            state.noop_count += 1


class INT_NEG(PushInstruction):
    def __init__(self):
        super().__init__("INT.NEG")

    def execute(self, state: PushState):
        if state.integer_stack:
            state.integer_stack.append(-state.integer_stack.pop())


class INT_LT(PushInstruction):
    def __init__(self):
        super().__init__("INT.LT")

    def execute(self, state: PushState):
        if len(state.integer_stack) >= 2:
            b = state.integer_stack.pop()
            a = state.integer_stack.pop()
            state.boolean_stack.append(a < b)


class INT_GT(PushInstruction):
    def __init__(self):
        super().__init__("INT.GT")

    def execute(self, state: PushState):
        if len(state.integer_stack) >= 2:
            b = state.integer_stack.pop()
            a = state.integer_stack.pop()
            state.boolean_stack.append(a > b)


class INT_EQ(PushInstruction):
    def __init__(self):
        super().__init__("INT.EQ")

    def execute(self, state: PushState):
        if len(state.integer_stack) >= 2:
            b = state.integer_stack.pop()
            a = state.integer_stack.pop()
            state.boolean_stack.append(a == b)

class INT_ABS(PushInstruction):
    def __init__(self):
        super().__init__("INT.ABS")

    def execute(self, state: PushState):
        if state.integer_stack:
            _int=state.integer_stack.pop()
            state.integer_stack.append(abs(_int))



class INT_COMPARE_RANGE(PushInstruction):
    def __init__(self):
        super().__init__("INT.COMPARE_RANGE")

    def execute(self, state: PushState):
        if len(state.integer_stack) >= 3:
            upper = state.integer_stack.pop()
            lower = state.integer_stack.pop()
            value = state.integer_stack.pop()
            state.boolean_stack.append(lower <= value <= upper)

class ITE_INT(PushInstruction):
    def __init__(self):
        super().__init__("INT.ITE")

    def execute(self, state: PushState):
        if state.boolean_stack and len(state.integer_stack) >= 2:
            false_val = state.integer_stack.pop()
            true_val = state.integer_stack.pop()
            cond = state.boolean_stack.pop()
            state.integer_stack.append(true_val if cond else false_val)



# Float instructions
class FLOAT_CONST(PushInstruction):
    def __init__(self, value: float):
        super().__init__(f"FLOAT.CONST.{value}")
        self.value = value

    def execute(self, state: PushState):
        state.float_stack.append(self.value)


class FLOAT_ADD(PushInstruction):
    def __init__(self):
        super().__init__("FLOAT.ADD")

    def execute(self, state: PushState):
        if len(state.float_stack) >= 2:
            b = state.float_stack.pop()
            a = state.float_stack.pop()
            state.float_stack.append(a + b)


class FLOAT_SUB(PushInstruction):
    def __init__(self):
        super().__init__("FLOAT.SUB")

    def execute(self, state: PushState):
        if len(state.float_stack) >= 2:
            b = state.float_stack.pop()
            a = state.float_stack.pop()
            state.float_stack.append(a - b)


class FLOAT_MUL(PushInstruction):
    def __init__(self):
        super().__init__("FLOAT.MUL")

    def execute(self, state: PushState):
        if len(state.float_stack) >= 2:
            b = state.float_stack.pop()
            a = state.float_stack.pop()
            state.float_stack.append(a * b)


class FLOAT_DIV(PushInstruction):
    def __init__(self):
        super().__init__("FLOAT.DIV")

    def execute(self, state: PushState):
        if len(state.float_stack) >= 2:
            b = state.float_stack.pop()
            a = state.float_stack.pop()
            if b != 0.0:
                state.float_stack.append(a / b)


class FLOAT_NEG(PushInstruction):
    def __init__(self):
        super().__init__("FLOAT.NEG")

    def execute(self, state: PushState):
        if state.float_stack:
            state.float_stack.append(-state.float_stack.pop())


class FLOAT_ABS(PushInstruction):
    def __init__(self):
        super().__init__("FLOAT.ABS")

    def execute(self, state: PushState):
        if state.float_stack:
            state.float_stack.append(abs(state.float_stack.pop()))


class FLOAT_FLOOR(PushInstruction):
    def __init__(self):
        super().__init__("FLOAT.FLOOR")

    def execute(self, state: PushState):
        if state.float_stack:
            state.float_stack.append(float(math.floor(state.float_stack.pop())))
        else:
            state.noop_count += 1


class FLOAT_COS(PushInstruction):
    def __init__(self):
        super().__init__("FLOAT.COS")

    def execute(self, state: PushState):
        if state.float_stack:
            state.float_stack.append(math.cos(state.float_stack.pop()))


class FLOAT_LT(PushInstruction):
    def __init__(self):
        super().__init__("FLOAT.LT")

    def execute(self, state: PushState):
        if len(state.float_stack) >= 2:
            b = state.float_stack.pop()
            a = state.float_stack.pop()
            state.boolean_stack.append(a < b)


class FLOAT_GT(PushInstruction):
    def __init__(self):
        super().__init__("FLOAT.GT")

    def execute(self, state: PushState):
        if len(state.float_stack) >= 2:
            b = state.float_stack.pop()
            a = state.float_stack.pop()
            state.boolean_stack.append(a > b)


class FLOAT_EQ(PushInstruction):
    def __init__(self):
        super().__init__("FLOAT.EQ")

    def execute(self, state: PushState):
        if len(state.float_stack) >= 2:
            b = state.float_stack.pop()
            a = state.float_stack.pop()
            state.boolean_stack.append(a == b)


class FLOAT_IS_NAN(PushInstruction):
    def __init__(self):
        super().__init__("FLOAT.IS_NAN")

    def execute(self, state: PushState):
        if state.float_stack:
            state.boolean_stack.append(math.isnan(state.float_stack.pop()))


class FLOAT_IS_INF(PushInstruction):
    def __init__(self):
        super().__init__("FLOAT.IS_INF")

    def execute(self, state: PushState):
        if state.float_stack:
            state.boolean_stack.append(math.isinf(state.float_stack.pop()))


class FLOAT_IS_FINITE(PushInstruction):
    def __init__(self):
        super().__init__("FLOAT.IS_FINITE")

    def execute(self, state: PushState):
        if state.float_stack:
            state.boolean_stack.append(math.isfinite(state.float_stack.pop()))


class FLOAT_TO_STR(PushInstruction):
    def __init__(self):
        super().__init__("FLOAT.TO.STR")

    def execute(self, state: PushState):
        if state.float_stack:
            value = state.float_stack.pop()
            state.string_stack.append(str(value))


class STR_TO_FLOAT(PushInstruction):
    def __init__(self):
        super().__init__("STR.TO.FLOAT")

    def execute(self, state: PushState):
        if state.string_stack:
            s = state.string_stack.pop()
            try:
                state.float_stack.append(float(s))
            except (TypeError, ValueError, OverflowError) as exc:
                state.record_error("STRING_TO_FLOAT_FAILED", str(exc))
        else:
            state.noop_count += 1

class ITE_FLOAT(PushInstruction):
    def __init__(self):
        super().__init__("FLOAT.ITE")

    def execute(self, state: PushState):
        if state.boolean_stack and len(state.float_stack) >= 2:
            false_val = state.float_stack.pop()
            true_val = state.float_stack.pop()
            cond = state.boolean_stack.pop()
            state.float_stack.append(true_val if cond else false_val)

#ERCs
class ERC_INT(PushInstruction):
    def __init__(self, value: Optional[int] = None):
        if value is None:
            value = int(random.uniform(-10, 256))
        super().__init__(f"ERC.INT.{value}")
        self.value = value

    def execute(self, state: PushState):
        state.integer_stack.append(self.value)
        
class ERC_FLOAT(PushInstruction):
    def __init__(self, value: Optional[float] = None):
        if value is None:
            if random.random() < 0.5:
                value = float(random.uniform(-256, 256))
            else:
                value = float(random.uniform(-1, 1))
        super().__init__(f"ERC.FLOAT.{value:.2f}")
        self.value = value

    def execute(self, state: PushState):
        state.float_stack.append(self.value)

#Boolean Instructions
class BOOL_CONST(PushInstruction):
    def __init__(self, value: bool):
        super().__init__(f"BOOL.CONST.{value}")
        self.value = value

    def execute(self, state: PushState):
        state.boolean_stack.append(self.value)


class BOOL_AND(PushInstruction):
    def __init__(self):
        super().__init__("BOOL.AND")

    def execute(self, state: PushState):
        if len(state.boolean_stack) >= 2:
            b = state.boolean_stack.pop()
            a = state.boolean_stack.pop()
            state.boolean_stack.append(a and b)


class BOOL_OR(PushInstruction):
    def __init__(self):
        super().__init__("BOOL.OR")

    def execute(self, state: PushState):
        if len(state.boolean_stack) >= 2:
            b = state.boolean_stack.pop()
            a = state.boolean_stack.pop()
            state.boolean_stack.append(a or b)


class BOOL_XOR(PushInstruction):
    def __init__(self):
        super().__init__("BOOL.XOR")

    def execute(self, state: PushState):
        if len(state.boolean_stack) >= 2:
            b = state.boolean_stack.pop()
            a = state.boolean_stack.pop()
            state.boolean_stack.append(a ^ b)


class BOOL_NOT(PushInstruction):
    def __init__(self):
        super().__init__("BOOL.NOT")

    def execute(self, state: PushState):
        if state.boolean_stack:
            state.boolean_stack.append(not state.boolean_stack.pop())


class BOOL_TO_INT(PushInstruction):
    def __init__(self):
        super().__init__("BOOL.TO.INT")

    def execute(self, state: PushState):
        if state.boolean_stack:
            state.integer_stack.append(1 if state.boolean_stack.pop() else 0)


class ITE_BOOL(PushInstruction):
    def __init__(self):
        super().__init__("BOOL.ITE")

    def execute(self, state: PushState):
        if len(state.boolean_stack) >= 3:
            false_val = state.boolean_stack.pop()
            true_val = state.boolean_stack.pop()
            cond = state.boolean_stack.pop()
            state.boolean_stack.append(true_val if cond else false_val)
        else:
            state.noop_count += 1

#BIT 
class BIT_AND(PushInstruction):
    def __init__(self):
        super().__init__("BIT.AND")

    def execute(self, state: PushState):
        if len(state.integer_stack) >= 2:
            b = state.integer_stack.pop()
            a = state.integer_stack.pop()
            state.integer_stack.append(a & b)


class BIT_OR(PushInstruction):
    def __init__(self):
        super().__init__("BIT.OR")

    def execute(self, state: PushState):
        if len(state.integer_stack) >= 2:
            b = state.integer_stack.pop()
            a = state.integer_stack.pop()
            state.integer_stack.append(a | b)


class BIT_XOR(PushInstruction):
    def __init__(self):
        super().__init__("BIT.XOR")

    def execute(self, state: PushState):
        if len(state.integer_stack) >= 2:
            b = state.integer_stack.pop()
            a = state.integer_stack.pop()
            state.integer_stack.append(a ^ b)


class BIT_NOT(PushInstruction):
    def __init__(self):
        super().__init__("BIT.NOT")

    def execute(self, state: PushState):
        if state.integer_stack:
            a = state.integer_stack.pop()
            state.integer_stack.append(~a)


class BIT_SHL(PushInstruction):
    def __init__(self):
        super().__init__("BIT.SHL")

    def execute(self, state: PushState):
        if len(state.integer_stack) >= 2:
            shift = state.integer_stack.pop()
            value = state.integer_stack.pop()
            state.integer_stack.append(value << shift)


class BIT_SHR(PushInstruction):
    def __init__(self):
        super().__init__("BIT.SHR")

    def execute(self, state: PushState):
        if len(state.integer_stack) >= 2:
            shift = state.integer_stack.pop()
            value = state.integer_stack.pop()
            state.integer_stack.append(value >> shift)


#String Instructions

# String Instructions (renamed to match your desired naming)
class STR_CONCAT(PushInstruction):
    def __init__(self):
        super().__init__("STR_CONCAT")

    def execute(self, state: PushState):
        if len(state.string_stack) >= 2:
            b = state.string_stack.pop()
            a = state.string_stack.pop()
            state.string_stack.append(a + b)


class STR_EQ(PushInstruction):
    def __init__(self):
        super().__init__("STR_EQ")

    def execute(self, state: PushState):
        if len(state.string_stack) >= 2:
            b = state.string_stack.pop()
            a = state.string_stack.pop()
            state.boolean_stack.append(a == b)


class STR_LEN(PushInstruction):
    def __init__(self):
        super().__init__("STR_LEN")

    def execute(self, state: PushState):
        if state.string_stack:
            state.integer_stack.append(len(state.string_stack.pop()))


class STR_CHAR_AT(PushInstruction):
    def __init__(self):
        super().__init__("STR_CHAR_AT")

    def execute(self, state: PushState):
        if state.string_stack and state.integer_stack:
            index = state.integer_stack.pop()
            s = state.string_stack.pop()
            if 0 <= index < len(s):
                state.string_stack.append(s[index])


class STR_STARTS_WITH(PushInstruction):
    def __init__(self):
        super().__init__("STR_STARTS_WITH")

    def execute(self, state: PushState):
        if len(state.string_stack) >= 2:
            prefix = state.string_stack.pop()
            s = state.string_stack.pop()
            state.boolean_stack.append(s.startswith(prefix))


class STR_CONTAINS(PushInstruction):
    def __init__(self):
        super().__init__("STR_CONTAINS")

    def execute(self, state: PushState):
        if len(state.string_stack) >= 2:
            sub = state.string_stack.pop()
            s = state.string_stack.pop()
            state.boolean_stack.append(sub in s)


class STR_INDEX_OF(PushInstruction):
    def __init__(self):
        super().__init__("STR_INDEX_OF")

    def execute(self, state: PushState):
        if len(state.string_stack) >= 2 and state.integer_stack:
            start = state.integer_stack.pop()
            sub = state.string_stack.pop()
            s = state.string_stack.pop()
            state.integer_stack.append(s.find(sub, max(0, start)))


class STR_SUBSTRING(PushInstruction):
    def __init__(self):
        super().__init__("STR_SUBSTRING")

    def execute(self, state: PushState):
        if state.string_stack and len(state.integer_stack) >= 2:
            end = state.integer_stack.pop()
            start = state.integer_stack.pop()
            s = state.string_stack.pop()
            state.string_stack.append(s[start:end] if 0 <= start <= end <= len(s) else "")


class STR_REPLACE(PushInstruction):
    def __init__(self):
        super().__init__("STR_REPLACE")

    def execute(self, state: PushState):
        if len(state.string_stack) >= 3:
            new = state.string_stack.pop()
            old = state.string_stack.pop()
            s = state.string_stack.pop()
            state.string_stack.append(s.replace(old, new))


class STR_REPLACE_ALL(PushInstruction):
    def __init__(self):
        super().__init__("STR_REPLACE_ALL")

    def execute(self, state: PushState):
        if len(state.string_stack) >= 3:
            new = state.string_stack.pop()
            old = state.string_stack.pop()
            s = state.string_stack.pop()
            state.string_stack.append(s.replace(old, new))


class STR_TO_INT(PushInstruction):
    def __init__(self):
        super().__init__("STR_TO_INT")

    def execute(self, state: PushState):
        if state.string_stack:
            s = state.string_stack.pop()
            try:
                state.integer_stack.append(int(s))
            except (TypeError, ValueError, OverflowError) as exc:
                state.record_error("STRING_TO_INT_FAILED", str(exc))
        else:
            state.noop_count += 1


class INT_TO_STR(PushInstruction):
    def __init__(self):
        super().__init__("INT_TO_STR")

    def execute(self, state: PushState):
        if state.integer_stack:
            state.string_stack.append(str(state.integer_stack.pop()))


class ASCII_TO_STR(PushInstruction):
    def __init__(self):
        super().__init__("ASCII_TO_STR")

    def execute(self, state: PushState):
        if state.integer_stack:
            code = state.integer_stack.pop()
            try:
                state.string_stack.append(chr(max(0, int(code)) % 1114112))
            except (TypeError, ValueError, OverflowError) as exc:
                state.record_error("ASCII_TO_STRING_FAILED", str(exc))
        else:
            state.noop_count += 1


class STR_TO_ASCII(PushInstruction):
    def __init__(self):
        super().__init__("STR_TO_ASCII")

    def execute(self, state: PushState):
        if state.string_stack:
            s = state.string_stack.pop()
            state.integer_stack.append(ord(s[0]) if s else -1)


class STR_TO_LOWER(PushInstruction):
    def __init__(self):
        super().__init__("STR_TO_LOWER")

    def execute(self, state: PushState):
        if state.string_stack:
            state.string_stack.append(state.string_stack.pop().lower())


class STR_TO_UPPER(PushInstruction):
    def __init__(self):
        super().__init__("STR_TO_UPPER")

    def execute(self, state: PushState):
        if state.string_stack:
            state.string_stack.append(state.string_stack.pop().upper())


class STR_TRIM(PushInstruction):
    def __init__(self):
        super().__init__("STR_TRIM")

    def execute(self, state: PushState):
        if state.string_stack:
            state.string_stack.append(state.string_stack.pop().strip())


class STR_ITE(PushInstruction):
    def __init__(self):
        super().__init__("STR_ITE")

    def execute(self, state: PushState):
        if state.boolean_stack and len(state.string_stack) >= 2:
            false_val = state.string_stack.pop()
            true_val = state.string_stack.pop()
            cond = state.boolean_stack.pop()
            state.string_stack.append(true_val if cond else false_val)

class STR_CONST(PushInstruction):
    def __init__(self, value: str):
        super().__init__(f"STR.CONST.{value}")
        self.value = value

    def execute(self, state: PushState):
        state.string_stack.append(self.value)

# Execution control and generic utility instructions
class EXEC_IF(PushInstruction):
    def __init__(self):
        super().__init__("EXEC.IF")

    def execute(self, state: PushState):
        # Program layout: condition, EXEC.IF, true-block, false-block.
        if state.boolean_stack and len(state.exec_stack) >= 2:
            condition = state.boolean_stack.pop()
            true_branch = state.exec_stack.pop()
            false_branch = state.exec_stack.pop()
            state.exec_stack.append(true_branch if condition else false_branch)
        else:
            state.noop_count += 1


class EXEC_DO_TIMES(PushInstruction):
    def __init__(self):
        super().__init__("EXEC.DO_TIMES")

    def execute(self, state: PushState):
        if state.integer_stack and state.exec_stack:
            count = max(0, min(state.integer_stack.pop(), 50))
            count = min(count, max(0, state.max_steps - state.step_count))
            block = state.exec_stack.pop()
            for _ in range(count):
                state.exec_stack.append(block)
        else:
            state.noop_count += 1


class DUP_ANY(PushInstruction):
    def __init__(self):
        super().__init__("DUP.ANY")

    def execute(self, state: PushState):
        for stack in state.value_stacks():
            if stack:
                stack.append(copy.deepcopy(stack[-1]))
                return
        if len(state.ref_stack) > 1:
            state.ref_stack.append(state.ref_stack[-1])
            return
        state.noop_count += 1


class SWAP_ANY(PushInstruction):
    def __init__(self):
        super().__init__("SWAP.ANY")

    def execute(self, state: PushState):
        for stack in state.value_stacks():
            if len(stack) >= 2:
                stack[-1], stack[-2] = stack[-2], stack[-1]
                return
        if len(state.ref_stack) > 2:
            state.ref_stack[-1], state.ref_stack[-2] = state.ref_stack[-2], state.ref_stack[-1]
            return
        state.noop_count += 1


class POP_ANY(PushInstruction):
    def __init__(self):
        super().__init__("POP.ANY")

    def execute(self, state: PushState):
        found, _ = state.try_pop_from_any_stack()
        if not found:
            state.noop_count += 1


class VALUE_FROM_ANY(PushInstruction):
    """Move a typed value to the ordered domain-value stack."""

    def __init__(self):
        super().__init__("VALUE.FROM.ANY")

    def execute(self, state: PushState):
        found, value = state.try_pop_from_any_stack()
        if found:
            state.value_stack.append(value)
        else:
            state.noop_count += 1


class ARG_COUNT(PushInstruction):
    def __init__(self):
        super().__init__("ARG.COUNT")

    def execute(self, state: PushState):
        state.integer_stack.append(len(state.current_args))


class ARG_PUSH(PushInstruction):
    def __init__(self, index: int):
        self.index = int(index)
        super().__init__(f"ARG.{self.index}")

    def execute(self, state: PushState):
        if 0 <= self.index < len(state.current_args):
            state.push_argument(copy.deepcopy(state.current_args[self.index]))
        else:
            state.noop_count += 1


class ACTIVE_REF(PushInstruction):
    def __init__(self):
        super().__init__("REF.ACTIVE")

    def execute(self, state: PushState):
        if state.active_ref is not None:
            state.ref_stack.append(state.active_ref)
        else:
            state.noop_count += 1


class NULL_CONST(PushInstruction):
    def __init__(self):
        super().__init__("NULL.CONST")

    def execute(self, state: PushState):
        state.object_stack.append(None)


class RESULT_FROM_ANY(PushInstruction):
    def __init__(self):
        super().__init__("RESULT.FROM.ANY")

    def execute(self, state: PushState):
        found, value = state.try_pop_from_any_stack()
        if found:
            state.set_result(value, halt=True)
        else:
            state.noop_count += 1


class RESULT_NULL(PushInstruction):
    def __init__(self):
        super().__init__("RESULT.NULL")

    def execute(self, state: PushState):
        state.set_result(None, halt=True)


class RESULT_ERROR(PushInstruction):
    def __init__(self):
        super().__init__("RESULT.ERROR")

    def execute(self, state: PushState):
        state.record_error("MODELLED_EXCEPTION")
        state.set_result("error", halt=True)


class ITE(PushInstruction):
    def __init__(self):
        super().__init__("ITE")

    def execute(self, state: PushState):
        if state.boolean_stack and len(state.exec_stack) >= 2:
            condition = state.boolean_stack.pop()
            true_value = state.exec_stack.pop()
            false_value = state.exec_stack.pop()
            state.exec_stack.append(true_value if condition else false_value)
        else:
            state.noop_count += 1


# Data-structure instructions backed by PushState.heap

def _active_data(state: PushState, allowed_types: tuple[type, ...], operation: str) -> Any:
    data = state.get_data()
    if not isinstance(data, allowed_types):
        state.record_error(
            "INVALID_HEAP_OBJECT",
            f"{operation} expected {allowed_types}, got {type(data).__name__}",
        )
        return MISSING_RESULT
    return data


def _pop_integer_operand(state: PushState) -> tuple[bool, Optional[int]]:
    """Consume an int argument consistently from ordered and typed stacks."""
    if (
        state.value_stack
        and isinstance(state.value_stack[-1], int)
        and not isinstance(state.value_stack[-1], bool)
        and state.integer_stack
        and state.integer_stack[-1] == state.value_stack[-1]
    ):
        value = state.value_stack.pop()
        state.integer_stack.pop()
        return True, int(value)
    if state.integer_stack:
        return True, int(state.integer_stack.pop())
    return False, None


def _unwrap_reference(value: Any) -> Any:
    return value.ref_id if isinstance(value, HeapReference) else value


class DS_SIZE(PushInstruction):
    def __init__(self):
        super().__init__("DS.SIZE")

    def execute(self, state: PushState):
        data = _active_data(state, (list, tuple, set, dict), self.name)
        if data is not MISSING_RESULT:
            state.integer_stack.append(len(data))


class DS_IS_EMPTY(PushInstruction):
    def __init__(self):
        super().__init__("DS.IS_EMPTY")

    def execute(self, state: PushState):
        data = _active_data(state, (list, tuple, set, dict), self.name)
        if data is not MISSING_RESULT:
            state.boolean_stack.append(len(data) == 0)


class DS_CLEAR(PushInstruction):
    def __init__(self):
        super().__init__("DS.CLEAR")

    def execute(self, state: PushState):
        data = _active_data(state, (list, set, dict), self.name)
        if data is not MISSING_RESULT:
            data.clear()


class DS_GET_INDEX(PushInstruction):
    def __init__(self):
        super().__init__("DS.GET.INDEX")

    def execute(self, state: PushState):
        found, index = _pop_integer_operand(state)
        if not found:
            state.noop_count += 1
            return
        data = _active_data(state, (list, tuple), self.name)
        if data is MISSING_RESULT:
            return
        if 0 <= index < len(data):
            state.push_to_appropriate_stack(data[index])
        else:
            state.record_error("INDEX_OUT_OF_BOUNDS", str(index))


class DS_SET_INDEX(PushInstruction):
    def __init__(self):
        super().__init__("DS.SET.INDEX")

    def execute(self, state: PushState):
        found_value, value = state.try_pop_domain_value()
        found_index, index = _pop_integer_operand(state)
        if not (found_value and found_index):
            state.noop_count += 1
            return
        data = _active_data(state, (list,), self.name)
        if data is MISSING_RESULT:
            return
        if 0 <= index < len(data):
            previous = data[index]
            data[index] = value
            state.push_to_appropriate_stack(previous)
        else:
            state.record_error("INDEX_OUT_OF_BOUNDS", str(index))


class DS_INSERT_AT_INDEX(PushInstruction):
    def __init__(self):
        super().__init__("DS.INSERT.AT.INDEX")

    def execute(self, state: PushState):
        found_value, value = state.try_pop_domain_value()
        found_index, index = _pop_integer_operand(state)
        if not (found_value and found_index):
            state.noop_count += 1
            return
        data = _active_data(state, (list,), self.name)
        if data is MISSING_RESULT:
            return
        if 0 <= index <= len(data):
            data.insert(index, value)
        else:
            state.record_error("INDEX_OUT_OF_BOUNDS", str(index))


class DS_APPEND(PushInstruction):
    def __init__(self):
        super().__init__("DS.APPEND")

    def execute(self, state: PushState):
        found, value = state.try_pop_domain_value()
        if not found:
            state.noop_count += 1
            return
        data = _active_data(state, (list,), self.name)
        if data is not MISSING_RESULT:
            data.append(value)


class DS_REMOVE_INDEX(PushInstruction):
    def __init__(self):
        super().__init__("DS.REMOVE.INDEX")

    def execute(self, state: PushState):
        found, index = _pop_integer_operand(state)
        if not found:
            state.noop_count += 1
            return
        data = _active_data(state, (list,), self.name)
        if data is MISSING_RESULT:
            return
        if 0 <= index < len(data):
            state.push_to_appropriate_stack(data.pop(index))
        else:
            state.record_error("INDEX_OUT_OF_BOUNDS", str(index))


class DS_PEEK_LAST(PushInstruction):
    def __init__(self):
        super().__init__("DS.PEEK.LAST")

    def execute(self, state: PushState):
        data = _active_data(state, (list, tuple), self.name)
        if data is MISSING_RESULT:
            return
        if data:
            state.push_to_appropriate_stack(data[-1])
        else:
            state.record_error("EMPTY_DATA_STRUCTURE")


class DS_POP_LAST(PushInstruction):
    def __init__(self):
        super().__init__("DS.POP.LAST")

    def execute(self, state: PushState):
        data = _active_data(state, (list,), self.name)
        if data is MISSING_RESULT:
            return
        if data:
            state.push_to_appropriate_stack(data.pop())
        else:
            state.record_error("EMPTY_DATA_STRUCTURE")


class DS_LAST_INDEX(PushInstruction):
    def __init__(self):
        super().__init__("DS.LAST.INDEX")

    def execute(self, state: PushState):
        data = _active_data(state, (list, tuple), self.name)
        if data is not MISSING_RESULT:
            state.integer_stack.append(len(data) - 1)


class DS_FIRST_INDEX(PushInstruction):
    def __init__(self):
        super().__init__("DS.FIRST.INDEX")

    def execute(self, state: PushState):
        data = _active_data(state, (list, tuple), self.name)
        if data is not MISSING_RESULT:
            state.integer_stack.append(0 if data else -1)


class DS_INDEX_OF(PushInstruction):
    def __init__(self):
        super().__init__("DS.INDEX_OF")

    def execute(self, state: PushState):
        found, value = state.try_pop_domain_value()
        if not found:
            state.noop_count += 1
            return
        data = _active_data(state, (list, tuple), self.name)
        if data is MISSING_RESULT:
            return
        try:
            state.integer_stack.append(data.index(value))
        except ValueError:
            state.integer_stack.append(-1)


class DS_LAST_INDEX_OF(PushInstruction):
    def __init__(self):
        super().__init__("DS.LAST_INDEX_OF")

    def execute(self, state: PushState):
        found, value = state.try_pop_domain_value()
        if not found:
            state.noop_count += 1
            return
        data = _active_data(state, (list, tuple), self.name)
        if data is MISSING_RESULT:
            return
        for index in range(len(data) - 1, -1, -1):
            if data[index] == value:
                state.integer_stack.append(index)
                return
        state.integer_stack.append(-1)


class DS_CONTAINS(PushInstruction):
    def __init__(self):
        super().__init__("DS.CONTAINS")

    def execute(self, state: PushState):
        found, value = state.try_pop_domain_value()
        if not found:
            state.noop_count += 1
            return
        data = _active_data(state, (list, tuple, set, dict), self.name)
        if data is not MISSING_RESULT:
            state.boolean_stack.append(value in data)


# Map instructions
class MAP_SIZE(PushInstruction):
    def __init__(self):
        super().__init__("MAP.SIZE")

    def execute(self, state: PushState):
        data = _active_data(state, (dict,), self.name)
        if data is not MISSING_RESULT:
            state.integer_stack.append(len(data))


class MAP_CLEAR(PushInstruction):
    def __init__(self):
        super().__init__("MAP.CLEAR")

    def execute(self, state: PushState):
        data = _active_data(state, (dict,), self.name)
        if data is not MISSING_RESULT:
            data.clear()


class MAP_PUT(PushInstruction):
    def __init__(self):
        super().__init__("MAP.PUT")

    def execute(self, state: PushState):
        found_value, value = state.try_pop_domain_value()
        found_key, key = state.try_pop_domain_value()
        if not (found_value and found_key):
            state.noop_count += 1
            return
        data = _active_data(state, (dict,), self.name)
        if data is MISSING_RESULT:
            return
        previous = data.get(key, None)
        data[key] = value
        state.push_to_appropriate_stack(previous)


class MAP_GET(PushInstruction):
    def __init__(self):
        super().__init__("MAP.GET")

    def execute(self, state: PushState):
        found, key = state.try_pop_domain_value()
        if not found:
            state.noop_count += 1
            return
        data = _active_data(state, (dict,), self.name)
        if data is not MISSING_RESULT:
            state.push_to_appropriate_stack(data.get(key, None))


class MAP_REMOVE(PushInstruction):
    def __init__(self):
        super().__init__("MAP.REMOVE")

    def execute(self, state: PushState):
        found, key = state.try_pop_domain_value()
        if not found:
            state.noop_count += 1
            return
        data = _active_data(state, (dict,), self.name)
        if data is not MISSING_RESULT:
            state.push_to_appropriate_stack(data.pop(key, None))


class MAP_CONTAINS_KEY(PushInstruction):
    def __init__(self):
        super().__init__("MAP.CONTAINS.KEY")

    def execute(self, state: PushState):
        found, key = state.try_pop_domain_value()
        if not found:
            state.noop_count += 1
            return
        data = _active_data(state, (dict,), self.name)
        if data is not MISSING_RESULT:
            state.boolean_stack.append(key in data)


# Set instructions
class SET_SIZE(PushInstruction):
    def __init__(self):
        super().__init__("SET.SIZE")

    def execute(self, state: PushState):
        data = _active_data(state, (set,), self.name)
        if data is not MISSING_RESULT:
            state.integer_stack.append(len(data))


class SET_CLEAR(PushInstruction):
    def __init__(self):
        super().__init__("SET.CLEAR")

    def execute(self, state: PushState):
        data = _active_data(state, (set,), self.name)
        if data is not MISSING_RESULT:
            data.clear()


class SET_ADD(PushInstruction):
    def __init__(self):
        super().__init__("SET.ADD")

    def execute(self, state: PushState):
        found, value = state.try_pop_domain_value()
        if not found:
            state.noop_count += 1
            return
        data = _active_data(state, (set,), self.name)
        if data is MISSING_RESULT:
            return
        old_size = len(data)
        data.add(value)
        state.boolean_stack.append(len(data) != old_size)


class SET_REMOVE(PushInstruction):
    def __init__(self):
        super().__init__("SET.REMOVE")

    def execute(self, state: PushState):
        found, value = state.try_pop_domain_value()
        if not found:
            state.noop_count += 1
            return
        data = _active_data(state, (set,), self.name)
        if data is MISSING_RESULT:
            return
        existed = value in data
        if existed:
            data.remove(value)
        state.boolean_stack.append(existed)


class SET_CONTAINS(PushInstruction):
    def __init__(self):
        super().__init__("SET.CONTAINS")

    def execute(self, state: PushState):
        found, value = state.try_pop_domain_value()
        if not found:
            state.noop_count += 1
            return
        data = _active_data(state, (set,), self.name)
        if data is not MISSING_RESULT:
            state.boolean_stack.append(value in data)

