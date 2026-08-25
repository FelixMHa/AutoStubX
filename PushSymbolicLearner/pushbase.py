from __future__ import annotations

import copy
import math
import random
import re
from functools import lru_cache
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Union
from trainingexample import TrainingExample



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


_IMMUTABLE_VALUE_TYPES = (type(None), bool, int, float, str, bytes, HeapReference)


def _clone_value(value: Any) -> Any:
    """Copy mutable values while returning common immutable values directly."""
    if isinstance(value, _IMMUTABLE_VALUE_TYPES):
        return value
    return copy.deepcopy(value)


class _TrackedStack(list):
    """List-compatible stack carrying provenance tokens for argument copies.

    Public Push stacks remain ordinary list-like objects.  The parallel token list is
    internal metadata used only to identify the *specific* typed copy created when an
    argument is routed to both ``value_stack`` and a typed stack.  This avoids removing
    an unrelated equal-valued constant when a domain operation consumes an argument.
    """

    __slots__ = ("_tokens", "_owner")

    def __init__(self, owner: Optional["PushState"] = None) -> None:
        super().__init__()
        self._tokens: List[Optional[int]] = []
        self._owner = owner

    def append(self, value: Any, token: Optional[int] = None) -> None:  # type: ignore[override]
        super().append(value)
        self._tokens.append(token)

    def extend(self, values: Iterable[Any]) -> None:  # type: ignore[override]
        values = list(values)
        super().extend(values)
        self._tokens.extend([None] * len(values))

    def extend_with_tokens(
        self, values: Iterable[Any], tokens: Iterable[Optional[int]]
    ) -> None:
        values = list(values)
        tokens = list(tokens)
        if len(values) != len(tokens):
            raise ValueError("Tracked stack values/tokens must have equal length")
        super().extend(values)
        self._tokens.extend(tokens)

    def insert(  # type: ignore[override]
        self, index: int, value: Any, token: Optional[int] = None
    ) -> None:
        super().insert(index, value)
        self._tokens.insert(index, token)

    def pop(self, index: int = -1) -> Any:  # type: ignore[override]
        value, token = self.pop_with_token(index)
        return value

    def pop_with_token(
        self, index: int = -1, *, mark_used: bool = True
    ) -> tuple[Any, Optional[int]]:
        if not self:
            raise IndexError("pop from empty stack")
        token = self._tokens.pop(index)
        value = super().pop(index)
        if mark_used and token is not None and self._owner is not None:
            self._owner._mark_argument_token_used(token)
        return value, token

    def clear(self) -> None:  # type: ignore[override]
        super().clear()
        self._tokens.clear()

    def token_at(self, index: int = -1) -> Optional[int]:
        if not self:
            return None
        return self._tokens[index]

    def remove_token(self, token: int, *, mark_used: bool = False) -> bool:
        try:
            index = self._tokens.index(token)
        except ValueError:
            return False
        self.pop_with_token(index, mark_used=mark_used)
        return True

    def swap(self, first: int, second: int, *, mark_used: bool = True) -> None:
        if mark_used and self._owner is not None:
            for index in (first, second):
                token = self._tokens[index]
                if token is not None:
                    self._owner._mark_argument_token_used(token)
        self[first], self[second] = self[second], self[first]
        self._tokens[first], self._tokens[second] = (
            self._tokens[second],
            self._tokens[first],
        )


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

        # Core Push stacks. Typed/domain/reference stacks carry hidden provenance
        # tokens so equal-valued constants cannot be mistaken for argument copies.
        self.integer_stack: _TrackedStack = _TrackedStack(self)
        self.boolean_stack: _TrackedStack = _TrackedStack(self)
        self.string_stack: _TrackedStack = _TrackedStack(self)
        self.float_stack: _TrackedStack = _TrackedStack(self)
        self.object_stack: _TrackedStack = _TrackedStack(self)
        self.value_stack: _TrackedStack = _TrackedStack(self)
        self._value_stacks = (
            self.string_stack,
            self.integer_stack,
            self.boolean_stack,
            self.float_stack,
            self.object_stack,
        )
        self.exec_stack: List[Any] = []
        self.error_stack: List[str] = []
        self.diagnostics: List[str] = []

        # Persistent abstract heap.
        self.heap: Dict[int, Dict[str, Any]] = {}
        self.next_ref_id: int = 0
        self.ref_stack: _TrackedStack = _TrackedStack(self)
        self.active_ref: Optional[int] = None

        # Argument provenance/usage accounting.
        self._next_argument_token: int = 0
        self._argument_token_to_index: Dict[int, Optional[int]] = {}
        self._used_argument_tokens: set[int] = set()

        # Modeled Java outcome. Diagnostics are deliberately separate so an
        # interpreter failure or step limit cannot satisfy an expected exception.
        self.exception_code: Optional[str] = None
        self.execution_failed: bool = False

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
            "ref_stack",
        ):
            source = getattr(self, name)
            target = getattr(new_state, name)
            target.extend_with_tokens(
                copy.deepcopy(list(source)),
                copy.deepcopy(source._tokens),
            )

        for name in (
            "exec_stack",
            "error_stack",
            "diagnostics",
            "heap",
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
        new_state.exception_code = self.exception_code
        new_state.execution_failed = self.execution_failed
        new_state._next_argument_token = self._next_argument_token
        new_state._argument_token_to_index = copy.deepcopy(self._argument_token_to_index)
        new_state._used_argument_tokens = set(self._used_argument_tokens)
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
        self.exception_code = None
        self.execution_failed = False
        self._next_argument_token = 0
        self._argument_token_to_index.clear()
        self._used_argument_tokens.clear()
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
        return list(self._value_stacks)

    def try_pop_from_any_stack(self) -> tuple[bool, Any]:
        """Pop a legacy typed value, preserving the active receiver reference."""
        for stack in self._value_stacks:
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

    def _typed_stack_for_value(self, value: Any) -> _TrackedStack:
        if isinstance(value, HeapReference):
            return self.ref_stack
        if value is None:
            return self.object_stack
        if isinstance(value, bool):
            return self.boolean_stack
        if isinstance(value, int):
            return self.integer_stack
        if isinstance(value, float):
            return self.float_stack
        if isinstance(value, str):
            return self.string_stack
        return self.object_stack

    def _mark_argument_token_used(self, token: int) -> None:
        if token in self._argument_token_to_index:
            self._used_argument_tokens.add(token)

    def mark_argument_index_used(self, index: int) -> None:
        for token, arg_index in self._argument_token_to_index.items():
            if arg_index == index:
                self._used_argument_tokens.add(token)

    def mark_stack_item_used(self, stack: List[Any], index: int = -1) -> None:
        if isinstance(stack, _TrackedStack) and stack:
            token = stack.token_at(index)
            if token is not None:
                self._mark_argument_token_used(token)

    def any_argument_used(self) -> bool:
        return bool(self._used_argument_tokens)

    def _remove_typed_duplicate(
        self, value: Any, token: Optional[int] = None
    ) -> None:
        """Remove only the exact typed copy paired with a domain-stack entry.

        Older versions searched by value equality and could therefore delete a newly
        generated constant instead of the original argument when both had the same
        value.  Provenance tokens make the operation identity-safe.
        """
        if token is None:
            return
        self._typed_stack_for_value(value).remove_token(token, mark_used=False)

    def try_pop_domain_value(self) -> tuple[bool, Any]:
        """Pop an ordered domain value and its exact paired typed copy, if present."""
        if self.value_stack:
            value, token = self.value_stack.pop_with_token()
            self._remove_typed_duplicate(value, token)
            return True, value
        return self.try_pop_from_any_stack()

    def push_to_appropriate_stack(
        self, value: Any, *, token: Optional[int] = None
    ) -> None:
        """Push a Python/abstract-Java value to its corresponding Push stack."""
        if isinstance(value, HeapReference):
            self.ref_stack.append(value.ref_id, token=token)
        elif value is None:
            self.object_stack.append(None, token=token)
        elif isinstance(value, bool):  # bool must be tested before int
            self.boolean_stack.append(value, token=token)
        elif isinstance(value, int):
            self.integer_stack.append(value, token=token)
        elif isinstance(value, float):
            self.float_stack.append(value, token=token)
        elif isinstance(value, str):
            self.string_stack.append(value, token=token)
        else:
            self.object_stack.append(value, token=token)

    def push_domain_value(self, value: Any) -> None:
        """Push an untracked derived value to the ordered domain stack."""
        self.value_stack.append(value)

    def push_argument(self, value: Any, *, arg_index: Optional[int] = None) -> None:
        """Push an argument to both views using one provenance token."""
        token = self._next_argument_token
        self._next_argument_token += 1
        self._argument_token_to_index[token] = arg_index
        self.value_stack.append(value, token=token)
        self.push_to_appropriate_stack(value, token=token)

    def set_result(self, value: Any, *, halt: bool = False) -> None:
        self.result = value
        self.result_is_set = True
        if halt:
            self.halted = True

    def record_diagnostic(
        self,
        code: str,
        detail: Optional[str] = None,
        *,
        fatal: bool = False,
    ) -> None:
        """Record an interpreter/evaluation diagnostic, not a Java method outcome."""
        self.diagnostics.append(code if detail is None else f"{code}: {detail}")
        if fatal:
            self.execution_failed = True

    def throw_exception(self, code: str, detail: Optional[str] = None) -> None:
        """Record a modeled Java-style exceptional outcome and halt this call."""
        if self.exception_code is None:
            self.exception_code = str(code)
            # Keep the legacy marker for callers that inspect ``error_stack``.
            self.error_stack.append("error")
        self.diagnostics.append(
            f"THROWN[{code}]" if detail is None else f"THROWN[{code}]: {detail}"
        )
        self.halted = True

    def record_error(self, code: str = "error", detail: Optional[str] = None) -> None:
        """Backward-compatible alias for a modeled exceptional outcome."""
        self.throw_exception(code, detail)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "integer_stack": list(self.integer_stack),
            "boolean_stack": list(self.boolean_stack),
            "string_stack": list(self.string_stack),
            "float_stack": list(self.float_stack),
            "object_stack": copy.deepcopy(list(self.object_stack)),
            "value_stack": copy.deepcopy(list(self.value_stack)),
            "exec_stack": copy.deepcopy(self.exec_stack),
            "error_stack": self.error_stack.copy(),
            "diagnostics": self.diagnostics.copy(),
            "heap": copy.deepcopy(self.heap),
            "next_ref_id": self.next_ref_id,
            "ref_stack": list(self.ref_stack),
            "active_ref": self.active_ref,
            "result": self.result,
            "result_is_set": self.result_is_set,
            "exception_code": self.exception_code,
            "execution_failed": self.execution_failed,
            "used_argument_tokens": sorted(self._used_argument_tokens),
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
        elif ref_id in self.heap:
            raise ValueError(f"Heap reference {ref_id} is already allocated")

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
                state.record_diagnostic(
                    f"INSTRUCTION_EXCEPTION[{instruction!r}]",
                    f"{type(exc).__name__}: {exc}",
                    fatal=True,
                )
            finally:
                state.step_count += 1

        if state.exec_stack and state.step_count >= state.max_steps:
            state.record_diagnostic("STEP_LIMIT_EXCEEDED", fatal=True)
            state.halted = True

        return state


class PushGPGenome:
    """ genome with better complexity calculation"""
    
    def __init__(self):
        self.methods: Dict[str, PushProgram] = {}
        self.fitness = float('inf')
        self.data_fitness = float('inf')
        self.accuracy = 0.0
        self.method_accuracies: Dict[str, float] = {}
        self.complexity_penalty = 0.0
        self._complexity_cache: Optional[int] = None
        self._behavioral_signature: Optional[tuple] = None
        self._behavioral_signature_key: Optional[tuple] = None
        self.case_errors: List[float] = []
        self.evaluation_failures: List[str] = []
    
    def add_method(self, method_name: str, program: PushProgram) -> None:
        """Add or replace a method program and invalidate cached behaviour."""
        self.methods[method_name] = program
        self.invalidate_signature()
    
    def get_complexity_penalty(self) -> float:
        """Return cached program complexity, recomputing after invalidation."""
        if self._complexity_cache is None:
            self._complexity_cache = sum(
                self._count_instructions(program.code)
                for program in self.methods.values()
            )
        return self._complexity_cache
    
    def _count_instructions(self, code: Iterable[Any]) -> int:
        """Recursively count atoms while treating each nested block structurally."""
        count = 0
        for item in code:
            if isinstance(item, (list, tuple)):
                count += self._count_instructions(item)
            else:
                count += 1
        return count
    
    @staticmethod
    def _copy_program_code(code: Iterable[Any]) -> List[Any]:
        """Copy program structure without recursively deep-copying instructions."""
        copied: List[Any] = []
        for item in code:
            if isinstance(item, list):
                copied.append(PushGPGenome._copy_program_code(item))
            elif isinstance(item, tuple):
                copied.append(tuple(PushGPGenome._copy_program_code(item)))
            elif isinstance(item, PushInstruction):
                copied.append(copy.copy(item))
            else:
                copied.append(_clone_value(item))
        return copied

    def copy(self):
        """Copy a genome using cheap shallow copies for instruction instances."""
        new_genome = PushGPGenome()
        for method_name, program in self.methods.items():
            new_program = PushProgram(self._copy_program_code(program.code))
            new_genome.methods[method_name] = new_program
        new_genome.fitness = self.fitness
        new_genome.data_fitness = self.data_fitness
        new_genome.accuracy = self.accuracy
        new_genome.method_accuracies = self.method_accuracies.copy()
        new_genome.complexity_penalty = self.complexity_penalty
        new_genome._complexity_cache = self._complexity_cache
        new_genome._behavioral_signature = copy.deepcopy(self._behavioral_signature)
        new_genome._behavioral_signature_key = copy.deepcopy(
            self._behavioral_signature_key
        )
        new_genome.case_errors = self.case_errors.copy()
        new_genome.evaluation_failures = self.evaluation_failures.copy()
        return new_genome

    def invalidate_signature(self):
        """Invalidate cached behavior and complexity after mutation/crossover."""
        self._behavioral_signature = None
        self._behavioral_signature_key = None
        self._complexity_cache = None



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

    minimal_core: List[PushInstruction] = [
        INT_ADD(), INT_SUB(), INT_EQ(), INT_LT(),
        INT_CONST(-1), INT_CONST(0), INT_CONST(1),
        BOOL_AND(), BOOL_OR(), BOOL_NOT(),
        BOOL_CONST(True), BOOL_CONST(False),
        DUP_ANY(), SWAP_ANY(), POP_ANY(), ITE(),
    ]
    original_ds_minimal: List[PushInstruction] = minimal_core + [
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
        "java_list_minimal",
        "java_map_minimal",
        "java_set_minimal",
        "ds_full",
        "collections_full",
    }:
        return _as_instruction_dict(original_primitives)

    call_and_result: List[PushInstruction] = [
        VALUE_FROM_ANY(), ARG_COUNT(),
        ARG_PUSH(0), ARG_PUSH(1), ARG_PUSH(2), ARG_PUSH(3),
        ACTIVE_REF(), NULL_CONST(), RECEIVER_VALUE(),
        RESULT_FROM_ANY(), RESULT_NULL(), RESULT_ERROR(),
        EXEC_IF(),
    ]
    domain_operations: List[PushInstruction] = [
        DS_SIZE(), DS_IS_EMPTY(), DS_CLEAR(),
        DS_GET_INDEX(), DS_SET_INDEX(), DS_INSERT_AT_INDEX(), DS_APPEND(),
        DS_REMOVE_INDEX(), DS_PEEK_LAST(), DS_POP_LAST(),
        DS_LAST_INDEX(), DS_FIRST_INDEX(), DS_INDEX_OF(), DS_LAST_INDEX_OF(),
        DS_CONTAINS(),
        # DS.SIZE/DS.CLEAR/DS.CONTAINS already cover map/set receivers.  Keep
        # only operations with genuinely distinct map/set semantics to avoid
        # wasting GP search probability on exact duplicates.
        MAP_PUT(), MAP_GET(), MAP_REMOVE(),
        SET_ADD(), SET_REMOVE(),
    ]

    list_operations: List[PushInstruction] = [
        DS_SIZE(), DS_IS_EMPTY(), DS_CLEAR(),
        DS_GET_INDEX(), DS_SET_INDEX(), DS_INSERT_AT_INDEX(), DS_APPEND(),
        DS_REMOVE_INDEX(), DS_PEEK_LAST(), DS_POP_LAST(),
        DS_LAST_INDEX(), DS_FIRST_INDEX(), DS_INDEX_OF(), DS_LAST_INDEX_OF(),
        DS_CONTAINS(),
    ]
    map_operations: List[PushInstruction] = [
        DS_SIZE(), DS_IS_EMPTY(), DS_CLEAR(), DS_CONTAINS(),
        MAP_PUT(), MAP_GET(), MAP_REMOVE(),
    ]
    set_operations: List[PushInstruction] = [
        DS_SIZE(), DS_IS_EMPTY(), DS_CLEAR(), DS_CONTAINS(),
        SET_ADD(), SET_REMOVE(),
    ]

    if profile == "java_list_minimal":
        return _as_instruction_dict(minimal_core + call_and_result + list_operations)
    if profile == "java_map_minimal":
        return _as_instruction_dict(minimal_core + call_and_result + map_operations)
    if profile == "java_set_minimal":
        return _as_instruction_dict(minimal_core + call_and_result + set_operations)
    if profile == "java_ds_minimal":
        enhanced_minimal = original_ds_minimal + call_and_result + [
            DS_IS_EMPTY(), DS_APPEND(), DS_PEEK_LAST(), DS_POP_LAST(),
            DS_LAST_INDEX(), DS_FIRST_INDEX(), DS_CONTAINS(),
            MAP_PUT(), MAP_GET(), MAP_REMOVE(),
            SET_ADD(), SET_REMOVE(),
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
    VOID_TYPES = {"void", "v", "java.lang.void"}
    ERROR_TYPES = {"error", "exception", "throw", "thrown"}
    NULL_TYPES = {"null", "none"}
    OBJECT_TYPES = {"object", "java.lang.object"}
    REFERENCE_TYPES = {"reference", "ref"}
    COLLECTION_TYPES = {
        "list": list, "java.util.list": list, "java.util.arraylist": list,
        "map": dict, "java.util.map": dict, "java.util.hashmap": dict,
        "set": set, "java.util.set": set, "java.util.hashset": set,
    }

    def __init__(
        self,
        profile: str = "primitives_full",
        max_steps: int = 150,
        allowed_instruction_names: Optional[Iterable[str]] = None,
    ):
        if max_steps <= 0:
            raise ValueError("max_steps must be greater than zero")
        self.profile = profile
        self.max_steps = max_steps
        instruction_set = create_pushgp_instruction_set(profile)
        if allowed_instruction_names is not None:
            allowed = set(allowed_instruction_names)
            instruction_set = {
                name: instruction
                for name, instruction in instruction_set.items()
                if name in allowed
            }
            if not instruction_set:
                raise ValueError("Instruction filter removed every instruction")
        self.instruction_set = instruction_set
        self.instruction_list = list(instruction_set.values())

    @staticmethod
    def _normalise_type_name(type_name: Optional[str]) -> str:
        if type_name is None:
            return ""
        return PushGPInterpreter._normalise_type_text(str(type_name))

    @staticmethod
    @lru_cache(maxsize=128)
    def _normalise_type_text(type_name: str) -> str:
        value = type_name.strip().lower().replace("/", ".")
        if value.startswith("l") and value.endswith(";"):
            value = value[1:-1]
        return value

    @staticmethod
    def _normalise_reference_id(value: Any) -> int:
        if isinstance(value, bool):
            raise ValueError("boolean is not a valid reference id")
        if isinstance(value, int):
            return value
        text = str(value).strip()
        if len(text) > 1 and text[0].lower() in {"o", "r"} and text[1:].isdigit():
            return int(text[1:])
        return int(text)

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
                return HeapReference(self._normalise_reference_id(ref_id))
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
            state.record_diagnostic(
                "ARGUMENT_COERCION_FAILED", str(exc), fatal=True
            )
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
            state.push_argument(resolved, arg_index=index)

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

    def execute_sequence(
        self,
        genome: PushGPGenome,
        example: TrainingExample,
        *,
        return_heap: bool = False,
    ) -> Any:
        """Execute a method sequence while preserving its abstract heap.

        The default three-value return remains backward compatible.  ``return_heap``
        adds a fourth value containing a deep snapshot of the complete final heap,
        which lets the learner supervise multi-object traces without guessing which
        receiver an expected heap refers to.
        """
        state = PushState(max_steps=self.max_steps)
        step_results: List[Any] = []
        used_inputs: List[bool] = []

        initial_state = getattr(example, "initial_state", None) or {}
        default_type = str(getattr(example, "data_structure_type", "list") or "list")

        for supplied_ref, raw_data in initial_state.items():
            try:
                ref_id = self._normalise_reference_id(supplied_ref)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid initial_state reference id: {supplied_ref!r}"
                ) from exc

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
            raw_receiver_ref = (
                receiver_refs[index] if index < len(receiver_refs) else default_receiver
            )
            invalid_receiver_detail: Optional[str] = None
            try:
                receiver_ref = self._normalise_reference_id(raw_receiver_ref)
            except (TypeError, ValueError):
                receiver_ref = default_receiver
                invalid_receiver_detail = repr(raw_receiver_ref)
            if invalid_receiver_detail is None and receiver_ref not in state.heap:
                invalid_receiver_detail = str(receiver_ref)
                receiver_ref = default_receiver

            state.begin_call(
                method_name=str(method_name),
                args=args,
                arg_types=arg_types,
                receiver_ref=receiver_ref,
            )
            self.push_args_to_stacks(state, args, arg_types)

            if invalid_receiver_detail is not None:
                # Never redirect an invalid receiver into normal method semantics.
                # The active reference is only a safe placeholder for state plumbing;
                # the modeled call is already exceptional and the program will not run.
                state.throw_exception(
                    "INVALID_RECEIVER_REFERENCE", invalid_receiver_detail
                )
            else:
                program = genome.methods.get(str(method_name))
                if program is not None:
                    program.execute(state)
                else:
                    state.record_diagnostic(
                        "MISSING_METHOD_PROGRAM", str(method_name), fatal=True
                    )

            step_results.append(self._extract_result_from_state(state, expected_type))
            used_inputs.append(state.any_argument_used())

        # ``state`` is local to this evaluation and is not mutated after this point,
        # so returning its final receiver avoids an unnecessary full deepcopy.
        final_obj = state.get(default_receiver)
        if return_heap:
            return step_results, used_inputs, final_obj, copy.deepcopy(state.heap)
        return step_results, used_inputs, final_obj

    def _extract_result_from_state(
        self,
        state: PushState,
        expected_type: Optional[str],
    ) -> Any:
        """Extract a candidate result without conflating missing, null, and throw.

        A modeled exception is an outcome independent of the declared return type, so
        it takes precedence over explicit/implicit normal results.  Diagnostics such as
        step limits and Python instruction failures never appear here.
        """
        if state.exception_code is not None:
            return ("exception", state.exception_code)
        if state.execution_failed:
            return MISSING_RESULT

        if state.result_is_set:
            return state.result

        key = self._normalise_type_name(expected_type)
        if not key:
            return MISSING_RESULT
        if key in self.VOID_TYPES:
            return None
        if key in self.ERROR_TYPES:
            return MISSING_RESULT
        if key in self.NULL_TYPES:
            if state.object_stack and state.object_stack[-1] is None:
                state.mark_stack_item_used(state.object_stack)
                return None
            return MISSING_RESULT

        stack: Optional[_TrackedStack] = None
        if key in self.INTEGER_TYPES:
            stack = state.integer_stack
        elif key in self.FLOAT_TYPES:
            stack = state.float_stack
        elif key in self.BOOLEAN_TYPES:
            stack = state.boolean_stack
        elif key in self.STRING_TYPES or key in self.CHAR_TYPES:
            stack = state.string_stack

        if stack:
            state.mark_stack_item_used(stack)
            return stack[-1]

        if key in self.REFERENCE_TYPES:
            if len(state.ref_stack) > 1:
                state.mark_stack_item_used(state.ref_stack)
                return HeapReference(state.ref_stack[-1])
            if state.object_stack and isinstance(state.object_stack[-1], HeapReference):
                state.mark_stack_item_used(state.object_stack)
                return state.object_stack[-1]
            return MISSING_RESULT

        expected_python_type = self.COLLECTION_TYPES.get(key)
        if expected_python_type is not None:
            if state.object_stack and isinstance(
                state.object_stack[-1], expected_python_type
            ):
                state.mark_stack_item_used(state.object_stack)
                return state.object_stack[-1]
            if len(state.ref_stack) > 1:
                candidate_ref = state.ref_stack[-1]
                candidate_data = state.get_data(candidate_ref)
                if isinstance(candidate_data, expected_python_type):
                    state.mark_stack_item_used(state.ref_stack)
                    return HeapReference(candidate_ref)
            return MISSING_RESULT

        if key in self.OBJECT_TYPES:
            if state.object_stack:
                state.mark_stack_item_used(state.object_stack)
                return state.object_stack[-1]
            if len(state.ref_stack) > 1:
                state.mark_stack_item_used(state.ref_stack)
                return HeapReference(state.ref_stack[-1])
            # Java Object may legitimately carry boxed primitive/string values.
            for candidate_stack in (
                state.string_stack,
                state.integer_stack,
                state.boolean_stack,
                state.float_stack,
            ):
                if candidate_stack:
                    state.mark_stack_item_used(candidate_stack)
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
        return type(self) is type(other) and self.__dict__ == other.__dict__
    
    def __hash__(self):
        parameters = tuple(
            sorted((key, repr(value)) for key, value in self.__dict__.items())
        )
        return hash((type(self), parameters))

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
            state.integer_stack.append(abs(state.integer_stack.pop()))



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
            # Java floating-point division does not throw on zero.  Python does,
            # so reproduce the Java/IEEE outcome explicitly.
            if b == 0.0:
                if math.isnan(a) or a == 0.0:
                    state.float_stack.append(float("nan"))
                else:
                    sign = math.copysign(1.0, a) * math.copysign(1.0, b)
                    state.float_stack.append(math.copysign(float("inf"), sign))
            else:
                state.float_stack.append(a / b)
        else:
            state.noop_count += 1


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
            value = state.float_stack.pop()
            if math.isnan(value) or math.isinf(value):
                state.float_stack.append(value)
            else:
                state.float_stack.append(float(math.floor(value)))
        else:
            state.noop_count += 1


class FLOAT_COS(PushInstruction):
    def __init__(self):
        super().__init__("FLOAT.COS")

    def execute(self, state: PushState):
        if state.float_stack:
            value = state.float_stack.pop()
            state.float_stack.append(
                float("nan") if math.isinf(value) else math.cos(value)
            )
        else:
            state.noop_count += 1


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
        value = float(value)
        # repr(float) is round-trippable; do not collapse distinct ERCs to two
        # decimal places because names are also used for serialization.
        super().__init__(f"ERC.FLOAT.{repr(value)}")
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

# String instructions
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
            else:
                state.throw_exception("STRING_INDEX_OUT_OF_BOUNDS", str(index))
        else:
            state.noop_count += 1


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
            if 0 <= start <= end <= len(s):
                state.string_stack.append(s[start:end])
            else:
                state.throw_exception(
                    "STRING_INDEX_OUT_OF_BOUNDS", f"start={start}, end={end}"
                )
        else:
            state.noop_count += 1


class STR_REPLACE(PushInstruction):
    def __init__(self):
        super().__init__("STR_REPLACE")

    def execute(self, state: PushState):
        if len(state.string_stack) >= 3:
            new = state.string_stack.pop()
            old = state.string_stack.pop()
            s = state.string_stack.pop()
            state.string_stack.append(s.replace(old, new))


def _expand_java_regex_replacement(match: re.Match[str], replacement: str) -> str:
    """Expand the most common Java Matcher replacement syntax.

    Java uses ``$1``/``${name}`` group references and backslash quoting, unlike
    Python's replacement-string syntax.  A callback keeps those conventions from
    being reinterpreted by ``re.sub``.
    """
    output: List[str] = []
    index = 0
    while index < len(replacement):
        char = replacement[index]
        if char == "\\":
            index += 1
            if index >= len(replacement):
                raise ValueError("Trailing backslash in replacement")
            output.append(replacement[index])
            index += 1
            continue
        if char != "$":
            output.append(char)
            index += 1
            continue

        index += 1
        if index >= len(replacement):
            raise ValueError("Dangling $ in replacement")
        if replacement[index] == "{":
            end = replacement.find("}", index + 1)
            if end < 0:
                raise ValueError("Unterminated named group in replacement")
            name = replacement[index + 1 : end]
            if not name:
                raise ValueError("Empty named group in replacement")
            try:
                output.append(match.group(name) or "")
            except (IndexError, KeyError) as exc:
                raise ValueError(f"Unknown replacement group {name!r}") from exc
            index = end + 1
            continue

        if not replacement[index].isdigit():
            raise ValueError("$ must be followed by a group number or {name}")
        group_number = int(replacement[index])
        if group_number > match.re.groups:
            raise ValueError(f"Unknown replacement group {group_number}")
        end = index + 1
        # Java greedily absorbs additional digits only while the resulting group
        # number remains valid; otherwise the extra digit is literal text.
        while end < len(replacement) and replacement[end].isdigit():
            candidate = group_number * 10 + int(replacement[end])
            if candidate > match.re.groups:
                break
            group_number = candidate
            end += 1
        output.append(match.group(group_number) or "")
        index = end
    return "".join(output)


class STR_REPLACE_ALL(PushInstruction):
    def __init__(self):
        super().__init__("STR_REPLACE_ALL")

    def execute(self, state: PushState):
        if len(state.string_stack) >= 3:
            new = state.string_stack.pop()
            pattern_text = state.string_stack.pop()
            s = state.string_stack.pop()
            try:
                pattern = re.compile(pattern_text)
                state.string_stack.append(
                    pattern.sub(
                        lambda match: _expand_java_regex_replacement(match, new),
                        s,
                    )
                )
            except re.error as exc:
                state.throw_exception("PATTERN_SYNTAX", str(exc))
            except ValueError as exc:
                state.throw_exception("INVALID_REPLACEMENT", str(exc))
        else:
            state.noop_count += 1


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
        for stack in state._value_stacks:
            if stack:
                state.mark_stack_item_used(stack)
                # A duplicate is a derived value, not a second alias of the original
                # argument token.
                stack.append(_clone_value(stack[-1]))
                return
        if len(state.ref_stack) > 1:
            state.mark_stack_item_used(state.ref_stack)
            state.ref_stack.append(state.ref_stack[-1])
            return
        state.noop_count += 1


class SWAP_ANY(PushInstruction):
    def __init__(self):
        super().__init__("SWAP.ANY")

    def execute(self, state: PushState):
        for stack in state._value_stacks:
            if len(stack) >= 2:
                if isinstance(stack, _TrackedStack):
                    stack.swap(-1, -2)
                else:
                    stack[-1], stack[-2] = stack[-2], stack[-1]
                return
        if len(state.ref_stack) > 2:
            state.ref_stack.swap(-1, -2)
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
            state.push_domain_value(value)
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
            state.mark_argument_index_used(self.index)
            state.push_argument(
                _clone_value(state.current_args[self.index]),
                arg_index=self.index,
            )
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

class RECEIVER_VALUE(PushInstruction):
    def __init__(self):
        super().__init__("RECEIVER.VALUE")

    def execute(self, state: PushState):
        if state.active_ref is None:
            state.noop_count += 1
            return

        value = state.get_data(state.active_ref)

        if isinstance(value, (bool, int, float, str)) or value is None:
            state.push_to_appropriate_stack(copy.deepcopy(value))
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
        state.throw_exception("MODELLED_EXCEPTION")


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
    """Consume an integer without equality-based duplicate guessing."""
    if (
        state.value_stack
        and isinstance(state.value_stack[-1], int)
        and not isinstance(state.value_stack[-1], bool)
    ):
        value, token = state.value_stack.pop_with_token()
        state._remove_typed_duplicate(value, token)
        return True, int(value)
    if state.integer_stack:
        return True, int(state.integer_stack.pop())
    return False, None


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


# Set instructions
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
