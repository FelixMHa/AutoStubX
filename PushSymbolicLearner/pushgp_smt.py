from __future__ import annotations

"""SMT-LIB 2 exporter for learned PushGP Java-library models.

The exporter symbolically executes one :class:`pushbase.PushProgram` per method
and emits a pure SMT function with this shape::

    (pre_heap, receiver_ref, arguments...) -> StubResult

``StubResult`` contains the post heap, the outcome kind, a boxed Java value, and
an exception code.  The emitted heap supports multiple references and models
lists, maps, and sets with SMT arrays, so aliases can be represented by passing
the same receiver reference to multiple calls.

The module has no solver dependency.  It emits portable SMT-LIB 2 text and
performs a structural parenthesis/string check.  A solver such as Z3 or cvc5 can
then load the generated ``.smt2`` file.

The default mode is strict: instructions whose semantics cannot be represented
faithfully *within the selected abstractions* are rejected instead of being
silently approximated.  ``strict=False`` keeps unsupported instructions as
Push-style no-ops and records warnings in the module manifest.  Strict mode does
not by itself make SMT ``Int``/``Real``/``String`` identical to all Java numeric,
IEEE-754, or UTF-16 corner cases; those abstraction boundaries are reported as
warnings and require dedicated BitVec/FloatingPoint/UTF-16 backends for exactness.
"""

import copy
import ctypes
import ctypes.util
import hashlib
import json
import math
import re
from collections import OrderedDict
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple

import pushbase as pb


# ---------------------------------------------------------------------------
# Public errors and configuration
# ---------------------------------------------------------------------------


class SMTExportError(RuntimeError):
    """Base class for SMT export failures."""


class SignatureInferenceError(SMTExportError):
    """Raised when training traces disagree about a method signature."""


class UnsupportedInstructionError(SMTExportError):
    """Raised when strict export encounters a non-SMT-compatible instruction."""

    def __init__(self, method_name: str, instruction_name: str, detail: str = "") -> None:
        message = f"Unsupported instruction {instruction_name!r} in method {method_name!r}"
        if detail:
            message += f": {detail}"
        super().__init__(message)
        self.method_name = method_name
        self.instruction_name = instruction_name
        self.detail = detail


class SymbolicPathLimitError(SMTExportError):
    """Raised when symbolic branches exceed the configured path bound."""


@dataclass(frozen=True)
class SMTExportConfig:
    """Controls symbolic compilation and SMT-LIB rendering."""

    logic: str = "ALL"
    strict: bool = True
    max_steps: int = 256
    max_paths: int = 256
    function_prefix: str = "stub"
    emit_comments: bool = True
    include_empty_heap_helpers: bool = True
    include_check_sat: bool = False
    validate_output: bool = True

    def __post_init__(self) -> None:
        if self.max_steps <= 0:
            raise ValueError("max_steps must be positive")
        if self.max_paths <= 0:
            raise ValueError("max_paths must be positive")
        if not self.logic or any(ch.isspace() for ch in self.logic):
            raise ValueError("logic must be one SMT-LIB symbol")
        if not self.function_prefix:
            raise ValueError("function_prefix cannot be empty")


@dataclass(frozen=True)
class MethodSignature:
    """Java-facing information needed to compile one learned method.

    ``return_type`` and ``argument_types`` use the same strings as
    ``TrainingExample.type_outputs``/``type_inputs``.  ``receiver_kind`` is one
    of ``list``, ``map``, ``set``, ``object``, ``generic``, or ``none``.  Use
    ``none`` or ``is_static=True`` for static ``java.lang`` methods.  Optional
    ``receiver_value_type`` describes the scalar payload exposed by
    ``RECEIVER.VALUE``; standard boxed/String owners are inferred automatically.
    """

    method_name: str
    argument_types: Tuple[str, ...] = ()
    return_type: str = "void"
    receiver_kind: str = "list"
    owner: Optional[str] = None
    is_static: bool = False
    smt_name: Optional[str] = None
    element_type: Optional[str] = None
    key_type: Optional[str] = None
    value_type: Optional[str] = None
    receiver_value_type: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.method_name:
            raise ValueError("method_name cannot be empty")
        object.__setattr__(self, "argument_types", tuple(self.argument_types or ()))
        kind = _normalise_receiver_kind(self.receiver_kind)
        if kind not in {"list", "map", "set", "object", "generic", "none"}:
            raise ValueError(
                "receiver_kind must be one of 'list', 'map', 'set', 'object', 'generic', or 'none'"
            )
        static = bool(self.is_static or kind == "none")
        object.__setattr__(self, "receiver_kind", "none" if static else kind)
        object.__setattr__(self, "is_static", static)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "MethodSignature":
        """Create a signature from reflection/JSON-style metadata.

        Common Java-side field spellings are accepted so the exporter does not
        require a second schema-conversion pass.
        """

        if not isinstance(data, Mapping):
            raise TypeError("Method signature data must be a mapping")

        def first(*names: str, default: Any = None) -> Any:
            for name in names:
                if name in data and data[name] is not None:
                    return data[name]
            return default

        method_name = first("method_name", "methodName", "method", "name")
        if method_name is None:
            raise ValueError("Signature mapping has no method name")
        arguments = first(
            "argument_types",
            "argumentTypes",
            "parameter_types",
            "parameterTypes",
            "inputTypes",
            default=(),
        )
        if isinstance(arguments, str):
            arguments = [arguments]
        static_value = first("is_static", "isStatic", "static", default=False)
        if isinstance(static_value, str):
            static_value = static_value.strip().lower() in {"true", "1", "yes", "static"}
        owner = first("owner", "targetClass", "declaringClass", "className")
        raw_receiver_kind = first(
            "receiver_kind",
            "receiverKind",
            "data_structure_type",
            "dataStructureType",
            default=None,
        )
        receiver_kind = "none" if bool(static_value) else _normalise_receiver_kind(raw_receiver_kind)
        if receiver_kind == "generic" and not bool(static_value):
            receiver_kind = _receiver_kind_from_owner(owner) or "generic"

        return cls(
            method_name=str(method_name),
            argument_types=tuple(str(item) for item in (arguments or ())),
            return_type=str(first("return_type", "returnType", "outputType", default="void")),
            receiver_kind=receiver_kind,
            owner=owner,
            is_static=bool(static_value),
            smt_name=first("smt_name", "smtName"),
            element_type=first("element_type", "elementType"),
            key_type=first("key_type", "keyType"),
            value_type=first("value_type", "valueType"),
            receiver_value_type=first(
                "receiver_value_type", "receiverValueType", "receiverPayloadType"
            ),
        )

    def to_mapping(self) -> Dict[str, Any]:
        return {
            "methodName": self.method_name,
            "parameterTypes": list(self.argument_types),
            "returnType": self.return_type,
            "receiverKind": self.receiver_kind,
            "owner": self.owner,
            "isStatic": self.is_static,
            "smtName": self.smt_name,
            "elementType": self.element_type,
            "keyType": self.key_type,
            "valueType": self.value_type,
            "receiverValueType": self.receiver_value_type,
        }


@dataclass(frozen=True)
class CompiledSMTMethod:
    """One generated SMT method stub and its metadata."""

    signature: MethodSignature
    smt_name: str
    precondition_name: str
    text: str
    path_count: int
    warnings: Tuple[str, ...] = ()

    def manifest_entry(self) -> Dict[str, Any]:
        return {
            "method": self.signature.method_name,
            "owner": self.signature.owner,
            "smtFunction": self.smt_name,
            "preconditionFunction": self.precondition_name,
            "argumentTypes": list(self.signature.argument_types),
            "returnType": self.signature.return_type,
            "receiverKind": self.signature.receiver_kind,
            "receiverValueType": self.signature.receiver_value_type,
            "isStatic": self.signature.is_static,
            "symbolicPaths": self.path_count,
            "warnings": list(self.warnings),
        }


@dataclass
class SMTModule:
    """Rendered SMT module plus a machine-readable method manifest."""

    text: str
    methods: "OrderedDict[str, CompiledSMTMethod]" = field(default_factory=OrderedDict)
    warnings: List[str] = field(default_factory=list)

    def to_smt2(self) -> str:
        return self.text

    def write(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.text, encoding="utf-8")
        return target

    def manifest(self) -> Dict[str, Any]:
        return {
            "schemaVersion": 1,
            "format": "SMT-LIB 2",
            "methods": [method.manifest_entry() for method in self.methods.values()],
            "warnings": list(self.warnings),
        }

    def write_manifest(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.manifest(), indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
        return target


# ---------------------------------------------------------------------------
# Java type handling and signature inference
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _JavaType:
    raw: str
    category: str
    smt_sort: str
    primitive: bool = False
    nullable_constructor: Optional[str] = None
    selector: Optional[str] = None
    reference_only: bool = False


_INT_PRIMITIVES = {
    "byte", "short", "int", "long", "b", "s", "i", "j",
}
_REAL_PRIMITIVES = {"float", "double", "f", "d"}
_BOOL_PRIMITIVES = {"boolean", "bool", "z"}
_CHAR_PRIMITIVES = {"char", "c"}
_BOXED_INT = {
    "java.lang.byte", "java.lang.short", "java.lang.integer", "java.lang.long",
}
_BOXED_REAL = {"java.lang.float", "java.lang.double"}
_BOXED_BOOL = {"java.lang.boolean"}
_BOXED_CHAR = {"java.lang.character"}
_STRING_TYPES = {"java.lang.string", "string", "str", "charsequence", "java.lang.charsequence"}
_GENERIC_OBJECT_TYPES = {"object", "java.lang.object", "any", "value", "jvalue"}
_REFERENCE_TYPES = {"reference", "ref"}
_VOID_TYPES = {"void", "v", "java.lang.void", ""}
_ERROR_TYPES = {"error", "exception", "throw", "thrown"}
_NULL_TYPES = {"null", "none"}


def _normalise_java_type(raw: Optional[str]) -> str:
    if raw is None:
        return ""
    value = str(raw).strip().replace("/", ".")
    if value.startswith("L") and value.endswith(";"):
        value = value[1:-1]
    return value.lower()


def _java_type(raw: Optional[str]) -> _JavaType:
    normalised = _normalise_java_type(raw)
    display = "" if raw is None else str(raw)

    if normalised in _VOID_TYPES:
        return _JavaType(display, "void", "Void")
    if normalised in _ERROR_TYPES:
        return _JavaType(display, "error", "JValue")
    if normalised in _NULL_TYPES:
        return _JavaType(display, "null", "JValue", nullable_constructor="JNull")
    if normalised in _INT_PRIMITIVES:
        return _JavaType(display, "int", "Int", primitive=True)
    if normalised in _REAL_PRIMITIVES:
        return _JavaType(display, "real", "Real", primitive=True)
    if normalised in _BOOL_PRIMITIVES:
        return _JavaType(display, "bool", "Bool", primitive=True)
    if normalised in _CHAR_PRIMITIVES:
        return _JavaType(display, "char", "String", primitive=True)
    if normalised in _BOXED_INT:
        return _JavaType(display, "boxed_int", "JValue", nullable_constructor="JInt", selector="j-int")
    if normalised in _BOXED_REAL:
        return _JavaType(display, "boxed_real", "JValue", nullable_constructor="JReal", selector="j-real")
    if normalised in _BOXED_BOOL:
        return _JavaType(display, "boxed_bool", "JValue", nullable_constructor="JBool", selector="j-bool")
    if normalised in _BOXED_CHAR:
        return _JavaType(display, "boxed_char", "JValue", nullable_constructor="JString", selector="j-string")
    if normalised in _STRING_TYPES:
        return _JavaType(display, "string_ref", "JValue", nullable_constructor="JString", selector="j-string")
    if normalised in _GENERIC_OBJECT_TYPES:
        return _JavaType(display, "object", "JValue")
    if normalised in _REFERENCE_TYPES:
        return _JavaType(display, "reference", "JValue", nullable_constructor="JRef", selector="j-ref", reference_only=True)
    if normalised.startswith("[") or normalised.endswith("[]"):
        return _JavaType(display, "reference", "JValue", nullable_constructor="JRef", selector="j-ref", reference_only=True)
    if any(token in normalised for token in ("list", "map", "set", "collection", "iterator")):
        return _JavaType(display, "reference", "JValue", nullable_constructor="JRef", selector="j-ref", reference_only=True)
    if normalised:
        # Other Java classes are represented by heap/object references.
        return _JavaType(display, "reference", "JValue", nullable_constructor="JRef", selector="j-ref", reference_only=True)
    return _JavaType(display, "object", "JValue")


def _receiver_payload_info(signature: "MethodSignature") -> Optional[_JavaType]:
    """Return the scalar JValue payload exposed by RECEIVER.VALUE, when known."""
    raw = signature.receiver_value_type or signature.owner
    if not raw:
        return None
    info = _java_type(raw)
    if info.category in {
        "int", "boxed_int", "real", "boxed_real", "bool", "boxed_bool",
        "char", "boxed_char", "string_ref",
    }:
        return info
    return None


def _jvalue_view(info: _JavaType) -> Optional[Tuple[str, str, str]]:
    """Return (constructor, selector, Push/SMT sort) for a scalar JValue payload."""
    if info.category in {"int", "boxed_int"}:
        return ("JInt", "j-int", "Int")
    if info.category in {"real", "boxed_real"}:
        return ("JReal", "j-real", "Real")
    if info.category in {"bool", "boxed_bool"}:
        return ("JBool", "j-bool", "Bool")
    if info.category in {"char", "boxed_char", "string_ref"}:
        return ("JString", "j-string", "String")
    return None


def _infer_python_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "double"
    if isinstance(value, str):
        return "java.lang.String"
    if isinstance(value, (list, tuple)):
        return "java.util.List"
    if isinstance(value, dict):
        kind = str(value.get("kind", value.get("type", ""))).strip().lower()
        if kind in {"exception", "error", "throw", "thrown"} or "exceptionType" in value:
            return "error"
        if kind in {"null", "none"}:
            return "null"
        if kind in {"integer", "int", "long", "short", "byte"}:
            return "int"
        if kind in {"float", "double", "real", "number"}:
            return "double"
        if kind in {"boolean", "bool"}:
            return "boolean"
        if kind in {"string", "char", "character"}:
            return "java.lang.String"
        if kind in {"reference", "ref", "object-reference"}:
            return "reference"
        if kind in {"list", "array", "arraylist"}:
            return "java.util.List"
        if kind in {"set", "hashset"}:
            return "java.util.Set"
        return "java.util.Map"
    if isinstance(value, set):
        return "java.util.Set"
    if isinstance(value, pb.HeapReference):
        return "reference"
    return "java.lang.Object"


def _normalise_receiver_kind(raw: Optional[str]) -> str:
    """Normalize receiver metadata without treating missing metadata as static.

    Only an explicit ``none``/``static`` marker means a static method.  Missing or
    unknown receiver metadata is ``generic`` and may subsequently be refined from
    the declaring owner.  This is important for scalar wrapper receivers such as
    ``java.lang.Boolean``: defaulting missing metadata to ``list`` (or ``none``)
    makes every concrete K_OBJECT receiver fail the generated precondition.
    """
    value = ("" if raw is None else str(raw)).strip().lower().replace("/", ".")
    if value in {"none", "static"}:
        return "none"
    if value in {"", "generic", "heap", "unknown"}:
        return "generic"
    if value in {"primitive", "scalar"}:
        return "generic"
    if "map" in value:
        return "map"
    if "set" in value:
        return "set"
    if "list" in value or "arraylist" in value or "collection" in value:
        return "list"
    if value == "object":
        return "object"
    # Preserve explicit unknown values so MethodSignature.__post_init__ rejects
    # malformed receiver metadata instead of silently changing its meaning.
    return value


def _receiver_kind_from_owner(owner: Any) -> Optional[str]:
    if owner is None:
        return None
    value = str(owner).strip().lower().replace("/", ".")
    if not value:
        return None
    if "map" in value:
        return "map"
    if "set" in value:
        return "set"
    if "list" in value or "arraylist" in value or "collection" in value:
        return "list"
    # Known non-collection Java owners are ordinary heap objects in this model.
    return "object"


def _compatible_type(first: str, second: str, *, method_name: str, position: str) -> str:
    if not first:
        return second
    if not second:
        return first
    a = _java_type(first)
    b = _java_type(second)
    if a.category == b.category:
        return first
    # ``type_outputs`` is often outcome-oriented in the training traces: one
    # example may say ``error`` or ``null`` while another call of the same Java
    # method returns its declared value type.  Those outcomes must not create a
    # fake overload conflict.
    if a.category == "error":
        return second
    if b.category == "error":
        return first
    if a.category == "null":
        return second
    if b.category == "null":
        return first
    # Integer-width and real-width distinctions collapse in SMT.
    if {a.category, b.category} <= {"int", "boxed_int"}:
        return "java.lang.Integer" if "boxed_int" in {a.category, b.category} else "int"
    if {a.category, b.category} <= {"real", "boxed_real"}:
        return "java.lang.Double" if "boxed_real" in {a.category, b.category} else "double"
    raise SignatureInferenceError(
        f"Incompatible types for {method_name!r} at {position}: {first!r} vs {second!r}"
    )


def _method_base_name(method_name: str) -> str:
    value = method_name.split("#", 1)[0]
    value = value.rsplit(".", 1)[-1]
    value = value.split("(", 1)[0]
    return value.lower()


def _pick_value_hint(candidates: Iterable[Optional[str]]) -> Optional[str]:
    selected: Optional[str] = None
    for candidate in candidates:
        if candidate is None:
            continue
        info = _java_type(candidate)
        if info.category in {"void", "error", "null"}:
            continue
        if selected is None:
            selected = candidate
        else:
            try:
                selected = _compatible_type(selected, candidate, method_name="value-hint", position="value")
            except SignatureInferenceError:
                return "java.lang.Object"
    return selected


def _derive_collection_hints(
    method_name: str,
    argument_types: Tuple[str, ...],
    return_type: str,
    receiver_kind: str,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    base = _method_base_name(method_name)
    element: Optional[str] = None
    key: Optional[str] = None
    value: Optional[str] = None

    if receiver_kind == "list":
        candidates: List[Optional[str]] = []
        if base in {"add", "push", "contains", "indexof", "lastindexof"}:
            for arg_type in argument_types:
                if _java_type(arg_type).category != "int":
                    candidates.append(arg_type)
        if base == "remove":
            removes_by_index = bool(argument_types) and _java_type(argument_types[0]).category == "int"
            if removes_by_index:
                candidates.append(return_type)
            else:
                candidates.extend(argument_types[:1])
        if base == "set" and len(argument_types) >= 2:
            candidates.append(argument_types[1])
        if base in {"get", "set", "pop", "peek", "element", "first", "last"}:
            candidates.append(return_type)
        element = _pick_value_hint(candidates)

    elif receiver_kind == "map":
        if argument_types:
            key = _pick_value_hint([argument_types[0]])
        value_candidates: List[Optional[str]] = []
        if base in {"put", "putifabsent", "replace"} and len(argument_types) >= 2:
            value_candidates.append(argument_types[1])
        if base in {"get", "put", "remove", "replace", "getordefault"}:
            value_candidates.append(return_type)
        value = _pick_value_hint(value_candidates)

    elif receiver_kind == "set":
        if argument_types:
            element = _pick_value_hint([argument_types[0]])

    return element, key, value


def _complete_signature_hints(signature: MethodSignature) -> MethodSignature:
    element, key, value = _derive_collection_hints(
        signature.method_name,
        signature.argument_types,
        signature.return_type,
        signature.receiver_kind,
    )

    # RECEIVER.VALUE may infer its payload sort from the declaring owner even when
    # reflection metadata did not explicitly provide receiverValueType. Persist
    # that effective type into the completed signature so the manifest exposes the
    # same heap ABI to external replay/test tools.
    receiver_value_type = signature.receiver_value_type
    if receiver_value_type is None and _receiver_payload_info(signature) is not None:
        receiver_value_type = signature.owner

    return replace(
        signature,
        element_type=signature.element_type or element,
        key_type=signature.key_type or key,
        value_type=signature.value_type or value,
        receiver_value_type=receiver_value_type,
    )


def infer_method_signatures(training_data: Sequence[Any]) -> List[MethodSignature]:
    """Infer stable method signatures from the learner's training examples.

    The first-seen method order is preserved.  Conflicting arity, receiver kind,
    or incompatible types fail loudly; this avoids generating an unsound SMT
    function for two overloaded methods that happened to share one trace name.
    """

    records: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()

    for example in list(training_data or []):
        sequence = list(getattr(example, "sequence", None) or [])
        all_args = list(getattr(example, "input_args", None) or [])
        all_input_types = list(getattr(example, "type_inputs", None) or [])
        all_output_types = list(getattr(example, "type_outputs", None) or [])
        expected_outputs = list(getattr(example, "expected_outputs", None) or [])
        owner = getattr(example, "target_class", None) or getattr(example, "owner", None)
        raw_receiver_kind = getattr(example, "data_structure_type", None)
        receiver_kind = _normalise_receiver_kind(raw_receiver_kind)
        if receiver_kind == "generic":
            receiver_kind = _receiver_kind_from_owner(owner) or "generic"

        static_attr = None
        for attr_name in ("is_static", "isStatic", "static"):
            if hasattr(example, attr_name):
                static_attr = getattr(example, attr_name)
                break

        for index, raw_name in enumerate(sequence):
            method_name = str(raw_name)
            call_static = static_attr
            if isinstance(call_static, (list, tuple)):
                call_static = call_static[index] if index < len(call_static) else None
            if isinstance(call_static, str):
                call_static = call_static.strip().lower() in {"true", "1", "yes", "static"}
            if call_static is True:
                call_receiver_kind = "none"
            else:
                call_receiver_kind = receiver_kind

            args = list(all_args[index] if index < len(all_args) else [])
            supplied_types = list(
                all_input_types[index] if index < len(all_input_types) else []
            )
            arg_types: List[str] = []
            for arg_index, arg in enumerate(args):
                supplied = supplied_types[arg_index] if arg_index < len(supplied_types) else ""
                arg_types.append(str(supplied or _infer_python_type(arg)))
            # Preserve extra declared parameters even if a malformed trace omitted a value.
            if len(supplied_types) > len(arg_types):
                arg_types.extend(str(item) for item in supplied_types[len(arg_types):])

            if index < len(all_output_types):
                return_type = str(all_output_types[index] or "void")
            elif index < len(expected_outputs):
                return_type = _infer_python_type(expected_outputs[index])
            else:
                return_type = "void"

            current = records.get(method_name)
            if current is None:
                records[method_name] = {
                    "argument_types": arg_types,
                    "return_type": return_type,
                    "receiver_kind": call_receiver_kind,
                    "owner": owner,
                }
                continue

            if len(current["argument_types"]) != len(arg_types):
                raise SignatureInferenceError(
                    f"Method {method_name!r} has conflicting arities: "
                    f"{len(current['argument_types'])} vs {len(arg_types)}"
                )
            merged_args = []
            for arg_index, (old, new) in enumerate(zip(current["argument_types"], arg_types)):
                merged_args.append(
                    _compatible_type(
                        old,
                        new,
                        method_name=method_name,
                        position=f"argument {arg_index}",
                    )
                )
            current["argument_types"] = merged_args
            current["return_type"] = _compatible_type(
                current["return_type"],
                return_type,
                method_name=method_name,
                position="return value",
            )
            if current["receiver_kind"] != call_receiver_kind:
                raise SignatureInferenceError(
                    f"Method {method_name!r} is used with receiver kinds "
                    f"{current['receiver_kind']!r} and {call_receiver_kind!r}"
                )
            if current["owner"] is None:
                current["owner"] = owner
            elif owner is not None and current["owner"] != owner:
                raise SignatureInferenceError(
                    f"Method {method_name!r} is used with owners "
                    f"{current['owner']!r} and {owner!r}; method identifiers must be globally unique"
                )

    result: List[MethodSignature] = []
    for method_name, record in records.items():
        args_tuple = tuple(record["argument_types"])
        return_type = str(record["return_type"])
        kind = str(record["receiver_kind"])
        element, key, value = _derive_collection_hints(
            method_name, args_tuple, return_type, kind
        )
        result.append(
            MethodSignature(
                method_name=method_name,
                argument_types=args_tuple,
                return_type=return_type,
                receiver_kind=kind,
                owner=record["owner"],
                is_static=(kind == "none"),
                element_type=element,
                key_type=key,
                value_type=value,
            )
        )
    return result


# ---------------------------------------------------------------------------
# Small SMT term utilities
# ---------------------------------------------------------------------------


def _smt_identifier(raw: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.$-]+", "_", raw)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned:
        cleaned = "unnamed"
    if cleaned[0].isdigit():
        cleaned = "m_" + cleaned
    return cleaned


def _unique_method_name(prefix: str, signature: MethodSignature, used: set[str]) -> str:
    requested = signature.smt_name or f"{prefix}_{signature.method_name}"
    base = _smt_identifier(requested)
    if base not in used:
        used.add(base)
        return base
    digest = hashlib.sha1(
        (signature.method_name + repr(signature.argument_types) + signature.return_type).encode("utf-8")
    ).hexdigest()[:8]
    candidate = f"{base}_{digest}"
    suffix = 2
    while candidate in used:
        candidate = f"{base}_{digest}_{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


def _int_literal(value: int) -> str:
    value = int(value)
    return str(value) if value >= 0 else f"(- {abs(value)})"


def _real_literal(value: float) -> str:
    if not math.isfinite(value):
        raise SMTExportError(f"SMT Real cannot represent non-finite value {value!r}")
    if value == 0:
        return "0.0"
    text = repr(float(value))
    if "e" in text.lower():
        # Exact decimal-to-rational conversion avoids solver-specific exponent syntax.
        from decimal import Decimal
        from fractions import Fraction

        fraction = Fraction(Decimal(text))
        numerator = _int_literal(fraction.numerator)
        if fraction.denominator == 1:
            return numerator
        return f"(/ {numerator} {fraction.denominator})"
    if text.startswith("-"):
        return f"(- {text[1:]})"
    if "." not in text:
        text += ".0"
    return text


def _string_literal(value: str) -> str:
    chunks: List[str] = []
    current: List[str] = []

    def flush() -> None:
        if current:
            chunks.append('"' + "".join(current).replace('"', '""') + '"')
            current.clear()

    for char in str(value):
        code = ord(char)
        if char in {"\n", "\r", "\t"} or code < 0x20 or code == 0x7F:
            flush()
            chunks.append(f"(str.from_code {code})")
        else:
            current.append(char)
    flush()
    if not chunks:
        return '""'
    if len(chunks) == 1:
        return chunks[0]
    return f"(str.++ {' '.join(chunks)})"


def _app(operator: str, *arguments: str) -> str:
    return f"({operator}{(' ' + ' '.join(arguments)) if arguments else ''})"


def _not(term: str) -> str:
    if term == "true":
        return "false"
    if term == "false":
        return "true"
    if term.startswith("(not ") and term.endswith(")"):
        return term[5:-1]
    return f"(not {term})"


def _and(*terms: str) -> str:
    flattened = [term for term in terms if term and term != "true"]
    if any(term == "false" for term in flattened):
        return "false"
    if not flattened:
        return "true"
    unique = list(OrderedDict.fromkeys(flattened))
    if len(unique) == 1:
        return unique[0]
    return f"(and {' '.join(unique)})"


def _or(*terms: str) -> str:
    flattened = [term for term in terms if term and term != "false"]
    if any(term == "true" for term in flattened):
        return "true"
    if not flattened:
        return "false"
    unique = list(OrderedDict.fromkeys(flattened))
    if len(unique) == 1:
        return unique[0]
    return f"(or {' '.join(unique)})"


def _eq(left: str, right: str) -> str:
    if left == right:
        return "true"
    return f"(= {left} {right})"


def _ite(condition: str, true_term: str, false_term: str) -> str:
    if condition == "true":
        return true_term
    if condition == "false":
        return false_term
    if true_term == false_term:
        return true_term
    return f"(ite {condition} {true_term} {false_term})"


def _tester(constructor: str, term: str) -> str:
    return f"((_ is {constructor}) {term})"


def _parse_constant_int(term: str) -> Optional[int]:
    if re.fullmatch(r"[0-9]+", term):
        return int(term)
    match = re.fullmatch(r"\(- ([0-9]+)\)", term)
    if match:
        return -int(match.group(1))
    return None


def _const_array(sort: str, value: str) -> str:
    return f"((as const {sort}) {value})"


# ---------------------------------------------------------------------------
# Symbolic Push state
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _SVal:
    term: str
    sort: str
    token: int


@dataclass
class _SymHeap:
    kind: str
    object_value: str
    list_size: str
    list_data: str
    map_size: str
    map_present: str
    map_data: str
    set_size: str
    set_present: str

    @classmethod
    def from_pre(cls) -> "_SymHeap":
        return cls(
            kind="(heap-kind pre)",
            object_value="(heap-object-value pre)",
            list_size="(heap-list-size pre)",
            list_data="(heap-list-data pre)",
            map_size="(heap-map-size pre)",
            map_present="(heap-map-present pre)",
            map_data="(heap-map-data pre)",
            set_size="(heap-set-size pre)",
            set_present="(heap-set-present pre)",
        )

    def copy(self) -> "_SymHeap":
        return replace(self)

    def term(self) -> str:
        return (
            f"(mk-heap {self.kind} {self.object_value} {self.list_size} {self.list_data} "
            f"{self.map_size} {self.map_present} {self.map_data} "
            f"{self.set_size} {self.set_present})"
        )


@dataclass
class _SymState:
    integer_stack: List[_SVal] = field(default_factory=list)
    boolean_stack: List[_SVal] = field(default_factory=list)
    string_stack: List[_SVal] = field(default_factory=list)
    real_stack: List[_SVal] = field(default_factory=list)
    object_stack: List[_SVal] = field(default_factory=list)
    value_stack: List[_SVal] = field(default_factory=list)
    ref_stack: List[_SVal] = field(default_factory=list)
    exec_stack: List[Any] = field(default_factory=list)
    arg_domains: List[_SVal] = field(default_factory=list)
    arg_views: List[_SVal] = field(default_factory=list)
    heap: _SymHeap = field(default_factory=_SymHeap.from_pre)
    path_condition: str = "true"
    exception: str = "EX_NONE"
    result: Optional[_SVal] = None
    result_is_set: bool = False
    halted: bool = False
    step_count: int = 0

    def clone(self) -> "_SymState":
        return _SymState(
            integer_stack=self.integer_stack.copy(),
            boolean_stack=self.boolean_stack.copy(),
            string_stack=self.string_stack.copy(),
            real_stack=self.real_stack.copy(),
            object_stack=self.object_stack.copy(),
            value_stack=self.value_stack.copy(),
            ref_stack=self.ref_stack.copy(),
            exec_stack=self.exec_stack.copy(),
            arg_domains=self.arg_domains.copy(),
            arg_views=self.arg_views.copy(),
            heap=self.heap.copy(),
            path_condition=self.path_condition,
            exception=self.exception,
            result=self.result,
            result_is_set=self.result_is_set,
            halted=self.halted,
            step_count=self.step_count,
        )

    def typed_stacks(self) -> List[List[_SVal]]:
        # Matches PushState.value_stacks() order.
        return [
            self.string_stack,
            self.integer_stack,
            self.boolean_stack,
            self.real_stack,
            self.object_stack,
        ]


# ---------------------------------------------------------------------------
# Symbolic compiler
# ---------------------------------------------------------------------------


class _MethodCompiler:
    def __init__(
        self,
        signature: MethodSignature,
        smt_name: str,
        config: SMTExportConfig,
    ) -> None:
        self.signature = signature
        self.smt_name = smt_name
        self.config = config
        self.warnings: List[str] = []
        self._next_token = 1
        self.receiver = None if signature.is_static else _SVal("receiver", "Ref", 0)
        self.argument_infos = [_java_type(item) for item in signature.argument_types]
        self.return_info = _java_type(signature.return_type)
        self.element_info = _java_type(signature.element_type or "java.lang.Object")
        self.key_info = _java_type(signature.key_type or "java.lang.Object")
        self.value_info = _java_type(signature.value_type or signature.return_type or "java.lang.Object")
        self.receiver_value_info = _receiver_payload_info(signature)

        all_infos = self.argument_infos + [
            self.return_info,
            self.element_info,
            self.key_info,
            self.value_info,
        ]
        if self.receiver_value_info is not None:
            all_infos.append(self.receiver_value_info)
        if any(info.category in {"real", "boxed_real"} for info in all_infos):
            self._warn(
                f"{self.signature.method_name}: Java float/double values are modeled as mathematical SMT Real"
            )
        if any(info.category in {"string_ref", "boxed_char", "char"} for info in all_infos):
            self._warn(
                f"{self.signature.method_name}: Java UTF-16 strings are modeled with the SMT String theory"
            )

    def _fresh(self, term: str, sort: str, token: Optional[int] = None) -> _SVal:
        if token is None:
            token = self._next_token
            self._next_token += 1
        return _SVal(term, sort, token)

    def _warn(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)

    def _unsupported(self, instruction_name: str, detail: str = "") -> None:
        if self.config.strict:
            raise UnsupportedInstructionError(
                self.signature.method_name, instruction_name, detail
            )
        message = f"{self.signature.method_name}: {instruction_name} treated as a no-op"
        if detail:
            message += f" ({detail})"
        self._warn(message)

    @staticmethod
    def _push_view(state: _SymState, value: _SVal) -> None:
        if value.sort == "Int":
            state.integer_stack.append(value)
        elif value.sort == "Bool":
            state.boolean_stack.append(value)
        elif value.sort == "String":
            state.string_stack.append(value)
        elif value.sort == "Real":
            state.real_stack.append(value)
        elif value.sort == "Ref":
            state.ref_stack.append(value)
        elif value.sort == "JValue":
            state.object_stack.append(value)
        else:
            raise SMTExportError(f"Unknown symbolic stack sort: {value.sort}")

    @staticmethod
    def _box(value: _SVal) -> str:
        if value.sort == "JValue":
            return value.term
        if value.sort == "Int":
            return f"(JInt {value.term})"
        if value.sort == "Bool":
            return f"(JBool {value.term})"
        if value.sort == "Real":
            return f"(JReal {value.term})"
        if value.sort == "String":
            return f"(JString {value.term})"
        if value.sort == "Ref":
            return f"(JRef {value.term})"
        raise SMTExportError(f"Cannot box symbolic sort {value.sort!r}")

    def _remove_typed_token(self, state: _SymState, token: int) -> None:
        for stack in state.typed_stacks():
            for index in range(len(stack) - 1, -1, -1):
                if stack[index].token == token:
                    stack.pop(index)
                    return
        for index in range(len(state.ref_stack) - 1, -1, -1):
            # Instance methods keep the receiver at ref_stack[0]. Static methods do
            # not have that sentinel, so index 0 may be an ordinary argument copy.
            if (
                (self.signature.is_static or index > 0)
                and state.ref_stack[index].token == token
            ):
                state.ref_stack.pop(index)
                return

    def _pop_any(self, state: _SymState) -> Optional[_SVal]:
        for stack in state.typed_stacks():
            if stack:
                return stack.pop()
        if len(state.ref_stack) > (0 if self.signature.is_static else 1):
            return state.ref_stack.pop()
        return None

    def _pop_domain(self, state: _SymState) -> Optional[_SVal]:
        if state.value_stack:
            value = state.value_stack.pop()
            self._remove_typed_token(state, value.token)
            return value
        return self._pop_any(state)

    @staticmethod
    def _record_exception(state: _SymState, exception: str) -> None:
        if state.exception == "EX_NONE":
            state.exception = exception
        # Concrete PushState.throw_exception() terminates the current method call.
        # Symbolic execution must do the same or instructions after a throw can
        # mutate the post-heap and silently change the learned program's semantics.
        state.halted = True

    def _add_condition(self, state: _SymState, condition: str) -> Optional[_SymState]:
        combined = _and(state.path_condition, condition)
        if combined == "false":
            return None
        state.path_condition = combined
        return state

    def _split(self, state: _SymState, condition: str) -> Tuple[Optional[_SymState], Optional[_SymState]]:
        if condition == "true":
            return state, None
        if condition == "false":
            return None, state
        true_state = state.clone()
        false_state = state.clone()
        return (
            self._add_condition(true_state, condition),
            self._add_condition(false_state, _not(condition)),
        )

    def _check_path_bound(self, states: Sequence[_SymState]) -> None:
        if len(states) > self.config.max_paths:
            raise SymbolicPathLimitError(
                f"Method {self.signature.method_name!r} exceeded "
                f"max_paths={self.config.max_paths}"
            )

    def _input_precondition(self, term: str, info: _JavaType) -> str:
        if info.category == "char":
            return _eq(f"(str.len {term})", "1")
        if info.smt_sort != "JValue":
            return "true"
        if info.category == "object":
            return "true"
        if info.category == "null":
            return _tester("JNull", term)
        constructor = info.nullable_constructor
        if constructor:
            return _or(_tester("JNull", term), _tester(constructor, term))
        return "true"

    def _view_variants(
        self,
        jvalue_term: str,
        info: _JavaType,
        *,
        for_input: bool,
    ) -> List[Tuple[str, str, str]]:
        """Return ``(condition, sort, term)`` variants for a boxed Java value."""

        if info.category == "object":
            return [
                (_tester("JNull", jvalue_term), "JValue", jvalue_term),
                (_tester("JInt", jvalue_term), "Int", f"(j-int {jvalue_term})"),
                (_tester("JBool", jvalue_term), "Bool", f"(j-bool {jvalue_term})"),
                (_tester("JReal", jvalue_term), "Real", f"(j-real {jvalue_term})"),
                (_tester("JString", jvalue_term), "String", f"(j-string {jvalue_term})"),
                (_tester("JRef", jvalue_term), "Ref", f"(j-ref {jvalue_term})"),
            ]

        if info.category == "null":
            return [(_tester("JNull", jvalue_term), "JValue", jvalue_term)]

        constructor = info.nullable_constructor
        selector = info.selector
        if constructor and selector:
            target_sort = {
                "JInt": "Int",
                "JBool": "Bool",
                "JReal": "Real",
                "JString": "String",
                "JRef": "Ref",
            }[constructor]
            variants = [
                (_tester("JNull", jvalue_term), "JValue", jvalue_term),
                (_tester(constructor, jvalue_term), target_sort, f"({selector} {jvalue_term})"),
            ]
            if not for_input:
                variants.append(
                    (
                        _not(_or(_tester("JNull", jvalue_term), _tester(constructor, jvalue_term))),
                        "JValue",
                        jvalue_term,
                    )
                )
            return variants

        # Primitive hints describe boxed heap elements.
        primitive_constructor = {
            "int": ("JInt", "Int", "j-int"),
            "real": ("JReal", "Real", "j-real"),
            "bool": ("JBool", "Bool", "j-bool"),
            "char": ("JString", "String", "j-string"),
        }.get(info.category)
        if primitive_constructor:
            constructor, target_sort, selector = primitive_constructor
            variants = [
                (_tester(constructor, jvalue_term), target_sort, f"({selector} {jvalue_term})"),
            ]
            if not for_input:
                variants.extend(
                    [
                        (_tester("JNull", jvalue_term), "JValue", jvalue_term),
                        (
                            _not(_or(_tester("JNull", jvalue_term), _tester(constructor, jvalue_term))),
                            "JValue",
                            jvalue_term,
                        ),
                    ]
                )
            return variants

        return [("true", "JValue", jvalue_term)]

    def _push_boxed_value(
        self,
        state: _SymState,
        jvalue_term: str,
        info: _JavaType,
        *,
        include_domain: bool,
        existing_token: Optional[int] = None,
        for_input: bool = False,
    ) -> List[_SymState]:
        variants = self._view_variants(jvalue_term, info, for_input=for_input)
        result: List[_SymState] = []
        token = existing_token if existing_token is not None else self._next_token
        if existing_token is None:
            self._next_token += 1

        for condition, sort, view_term in variants:
            branch = state.clone() if len(variants) > 1 else state
            branch = self._add_condition(branch, condition)
            if branch is None:
                continue
            domain = self._fresh(jvalue_term, "JValue", token=token)
            view = self._fresh(view_term, sort, token=token)
            if include_domain:
                branch.value_stack.append(domain)
            self._push_view(branch, view)
            result.append(branch)
        self._check_path_bound(result)
        return result

    def _initial_states(self) -> List[_SymState]:
        state = _SymState()
        if self.receiver is not None:
            state.ref_stack.append(self.receiver)
        states = [state]

        for index, info in enumerate(self.argument_infos):
            term = f"arg{index}"
            next_states: List[_SymState] = []
            for current in states:
                if info.smt_sort != "JValue":
                    token = self._next_token
                    self._next_token += 1
                    domain = self._fresh(term, info.smt_sort, token=token)
                    view = self._fresh(term, info.smt_sort, token=token)
                    current.value_stack.append(domain)
                    self._push_view(current, view)
                    current.arg_domains.append(domain)
                    current.arg_views.append(view)
                    next_states.append(current)
                    continue

                variants = self._view_variants(term, info, for_input=True)
                token = self._next_token
                self._next_token += 1
                for condition, sort, view_term in variants:
                    branch = current.clone() if len(variants) > 1 else current
                    branch = self._add_condition(branch, condition)
                    if branch is None:
                        continue
                    # Concrete pushbase stores the runtime Python/abstract-Java value
                    # in value_stack, not the declared boxed type.  Thus a non-null
                    # Integer argument is an Int in both value_stack and integer_stack,
                    # while null remains a JValue/JNull.  Keeping that distinction is
                    # essential for _pop_integer/_pop_domain operand precedence.
                    domain = self._fresh(view_term, sort, token=token)
                    view = self._fresh(view_term, sort, token=token)
                    branch.value_stack.append(domain)
                    self._push_view(branch, view)
                    branch.arg_domains.append(domain)
                    branch.arg_views.append(view)
                    next_states.append(branch)
            states = next_states
            self._check_path_bound(states)
        return states

    def _push_jvalue_result(
        self,
        state: _SymState,
        term: str,
        info: _JavaType,
    ) -> List[_SymState]:
        return self._push_boxed_value(
            state,
            term,
            info,
            include_domain=False,
            for_input=False,
        )

    def _require_declared_kinds(
        self,
        state: _SymState,
        allowed_kinds: Iterable[str],
        instruction_name: str,
    ) -> bool:
        """Model concrete ``_active_data`` receiver validation.

        Important: callers must invoke this at the same point where the concrete
        instruction calls ``_active_data``.  Operand-taking Push instructions first
        try to pop their operands and are a no-op on underflow; only after successful
        operand acquisition do they validate the active receiver.  Performing this
        check earlier changes a concrete no-op into an SMT exception.
        """

        allowed = frozenset(str(kind) for kind in allowed_kinds)
        if self.signature.is_static or self.receiver is None:
            self._record_exception(state, "EX_INVALID_RECEIVER")
            return False
        declared = self.signature.receiver_kind
        if declared in allowed:
            return True
        if declared == "generic":
            self._unsupported(
                instruction_name,
                "generic receivers require symbolic object-kind dispatch",
            )
            return False
        self._record_exception(state, "EX_INVALID_RECEIVER")
        return False

    def _require_declared_kind(
        self,
        state: _SymState,
        required_kind: str,
        instruction_name: str,
    ) -> bool:
        return self._require_declared_kinds(
            state, (required_kind,), instruction_name
        )

    def _receiver_term(self) -> str:
        if self.receiver is None:
            raise SMTExportError(
                f"Method {self.signature.method_name!r} uses a heap instruction but is static"
            )
        return self.receiver.term

    def _receiver_kind_term(self, state: _SymState) -> str:
        return f"(select {state.heap.kind} {self._receiver_term()})"

    def _size_term(self, state: _SymState, kind: Optional[str] = None) -> str:
        receiver = self._receiver_term()
        actual = kind or self.signature.receiver_kind
        if actual == "list":
            return f"(select {state.heap.list_size} {receiver})"
        if actual == "map":
            return f"(select {state.heap.map_size} {receiver})"
        if actual == "set":
            return f"(select {state.heap.set_size} {receiver})"
        kind_term = self._receiver_kind_term(state)
        return _ite(
            _eq(kind_term, "K_LIST"),
            f"(select {state.heap.list_size} {receiver})",
            _ite(
                _eq(kind_term, "K_MAP"),
                f"(select {state.heap.map_size} {receiver})",
                f"(select {state.heap.set_size} {receiver})",
            ),
        )

    def _list_array(self, state: _SymState) -> str:
        return f"(select {state.heap.list_data} {self._receiver_term()})"

    def _map_present_array(self, state: _SymState) -> str:
        return f"(select {state.heap.map_present} {self._receiver_term()})"

    def _map_data_array(self, state: _SymState) -> str:
        return f"(select {state.heap.map_data} {self._receiver_term()})"

    def _set_present_array(self, state: _SymState) -> str:
        return f"(select {state.heap.set_present} {self._receiver_term()})"

    def _pop_integer(self, state: _SymState) -> Optional[_SVal]:
        # Mirrors pushbase._pop_integer_operand's ordered-stack handling.
        if state.value_stack and state.value_stack[-1].sort == "Int":
            domain = state.value_stack.pop()
            # The concrete runtime removes the exact typed duplicate by provenance
            # token even when a newer integer constant sits above it on the stack.
            self._remove_typed_token(state, domain.token)
            return domain
        if state.integer_stack:
            return state.integer_stack.pop()
        return None

    def _binary(
        self,
        state: _SymState,
        stack: List[_SVal],
        output_sort: str,
        operator: str,
    ) -> List[_SymState]:
        if len(stack) < 2:
            return [state]
        right = stack.pop()
        left = stack.pop()
        value = self._fresh(f"({operator} {left.term} {right.term})", output_sort)
        self._push_view(state, value)
        return [state]

    def _literal_atom(self, state: _SymState, atom: Any) -> List[_SymState]:
        if atom is None:
            state.object_stack.append(self._fresh("JNull", "JValue"))
        elif isinstance(atom, bool):
            state.boolean_stack.append(self._fresh("true" if atom else "false", "Bool"))
        elif isinstance(atom, int):
            state.integer_stack.append(self._fresh(_int_literal(atom), "Int"))
        elif isinstance(atom, float):
            state.real_stack.append(self._fresh(_real_literal(atom), "Real"))
        elif isinstance(atom, str):
            state.string_stack.append(self._fresh(_string_literal(atom), "String"))
        else:
            self._unsupported(type(atom).__name__, "non-primitive Push literal")
        return [state]

    def _execute_instruction(self, state: _SymState, instruction: Any) -> List[_SymState]:
        name = str(getattr(instruction, "name", instruction))

        # Constants and ERCs.
        if name.startswith("INT.CONST.") or name.startswith("ERC.INT."):
            value = int(getattr(instruction, "value"))
            state.integer_stack.append(self._fresh(_int_literal(value), "Int"))
            return [state]
        if name.startswith("FLOAT.CONST.") or name.startswith("ERC.FLOAT."):
            value = float(getattr(instruction, "value"))
            state.real_stack.append(self._fresh(_real_literal(value), "Real"))
            return [state]
        if name.startswith("BOOL.CONST."):
            value = bool(getattr(instruction, "value"))
            state.boolean_stack.append(self._fresh("true" if value else "false", "Bool"))
            return [state]
        if name.startswith("STR.CONST."):
            value = str(getattr(instruction, "value"))
            state.string_stack.append(self._fresh(_string_literal(value), "String"))
            return [state]

        # Integer instructions.
        if name == "INT.ADD":
            return self._binary(state, state.integer_stack, "Int", "+")
        if name == "INT.SUB":
            return self._binary(state, state.integer_stack, "Int", "-")
        if name == "INT.MUL":
            return self._binary(state, state.integer_stack, "Int", "*")
        if name in {"INT.DIV", "INT.MOD"}:
            if len(state.integer_stack) < 2:
                return [state]
            divisor = state.integer_stack.pop()
            dividend = state.integer_stack.pop()
            valid, invalid = self._split(state, _not(_eq(divisor.term, "0")))
            result: List[_SymState] = []
            if valid is not None:
                helper = "java-div" if name == "INT.DIV" else "java-rem"
                valid.integer_stack.append(
                    self._fresh(f"({helper} {dividend.term} {divisor.term})", "Int")
                )
                result.append(valid)
            if invalid is not None:
                self._record_exception(invalid, "EX_ARITHMETIC")
                result.append(invalid)
            return result
        if name == "INT.NEG":
            if state.integer_stack:
                value = state.integer_stack.pop()
                state.integer_stack.append(self._fresh(f"(- {value.term})", "Int"))
            return [state]
        if name == "INT.ABS":
            if state.integer_stack:
                value = state.integer_stack.pop()
                state.integer_stack.append(self._fresh(f"(java-abs {value.term})", "Int"))
            return [state]
        if name in {"INT.LT", "INT.GT", "INT.EQ"}:
            if len(state.integer_stack) >= 2:
                right = state.integer_stack.pop()
                left = state.integer_stack.pop()
                operator = {"INT.LT": "<", "INT.GT": ">", "INT.EQ": "="}[name]
                state.boolean_stack.append(
                    self._fresh(f"({operator} {left.term} {right.term})", "Bool")
                )
            return [state]
        if name == "INT.COMPARE_RANGE":
            if len(state.integer_stack) >= 3:
                upper = state.integer_stack.pop()
                lower = state.integer_stack.pop()
                value = state.integer_stack.pop()
                state.boolean_stack.append(
                    self._fresh(
                        _and(
                            f"(<= {lower.term} {value.term})",
                            f"(<= {value.term} {upper.term})",
                        ),
                        "Bool",
                    )
                )
            return [state]
        if name == "INT.ITE":
            if state.boolean_stack and len(state.integer_stack) >= 2:
                false_value = state.integer_stack.pop()
                true_value = state.integer_stack.pop()
                condition = state.boolean_stack.pop()
                state.integer_stack.append(
                    self._fresh(_ite(condition.term, true_value.term, false_value.term), "Int")
                )
            return [state]

        # Real-valued float abstraction.
        if name == "FLOAT.ADD":
            return self._binary(state, state.real_stack, "Real", "+")
        if name == "FLOAT.SUB":
            return self._binary(state, state.real_stack, "Real", "-")
        if name == "FLOAT.MUL":
            return self._binary(state, state.real_stack, "Real", "*")
        if name == "FLOAT.DIV":
            # Concrete pushbase follows Java/IEEE-754 and produces NaN/Inf for a
            # zero divisor. SMT Real has neither value, so there is no faithful
            # translation in this backend. In permissive mode this becomes the
            # documented unsupported-instruction no-op rather than a third semantics.
            self._unsupported(
                name,
                "Java/IEEE-754 division by zero requires a FloatingPoint backend",
            )
            return [state]
        if name == "FLOAT.NEG":
            if state.real_stack:
                value = state.real_stack.pop()
                state.real_stack.append(self._fresh(f"(- {value.term})", "Real"))
            return [state]
        if name == "FLOAT.ABS":
            if state.real_stack:
                value = state.real_stack.pop()
                state.real_stack.append(
                    self._fresh(_ite(f"(< {value.term} 0.0)", f"(- {value.term})", value.term), "Real")
                )
            return [state]
        if name == "FLOAT.FLOOR":
            if state.real_stack:
                value = state.real_stack.pop()
                state.real_stack.append(self._fresh(f"(to_real (to_int {value.term}))", "Real"))
            return [state]
        if name in {"FLOAT.LT", "FLOAT.GT", "FLOAT.EQ"}:
            if len(state.real_stack) >= 2:
                right = state.real_stack.pop()
                left = state.real_stack.pop()
                operator = {"FLOAT.LT": "<", "FLOAT.GT": ">", "FLOAT.EQ": "="}[name]
                state.boolean_stack.append(
                    self._fresh(f"({operator} {left.term} {right.term})", "Bool")
                )
            return [state]
        if name == "FLOAT.ITE":
            if state.boolean_stack and len(state.real_stack) >= 2:
                false_value = state.real_stack.pop()
                true_value = state.real_stack.pop()
                condition = state.boolean_stack.pop()
                state.real_stack.append(
                    self._fresh(_ite(condition.term, true_value.term, false_value.term), "Real")
                )
            return [state]
        if name in {"FLOAT.IS_NAN", "FLOAT.IS_INF", "FLOAT.IS_FINITE"}:
            self._unsupported(
                name,
                "SMT Real has no IEEE NaN or infinity values; use a FloatingPoint backend",
            )
            return [state]
        if name in {"FLOAT.COS", "FLOAT.TO.STR", "STR.TO.FLOAT"}:
            self._unsupported(name, "not exactly representable in the selected SMT theory")
            return [state]

        # Boolean instructions.
        if name in {"BOOL.AND", "BOOL.OR", "BOOL.XOR"}:
            if len(state.boolean_stack) >= 2:
                right = state.boolean_stack.pop()
                left = state.boolean_stack.pop()
                if name == "BOOL.AND":
                    term = _and(left.term, right.term)
                elif name == "BOOL.OR":
                    term = _or(left.term, right.term)
                else:
                    term = f"(xor {left.term} {right.term})"
                state.boolean_stack.append(self._fresh(term, "Bool"))
            return [state]
        if name == "BOOL.NOT":
            if state.boolean_stack:
                value = state.boolean_stack.pop()
                state.boolean_stack.append(self._fresh(_not(value.term), "Bool"))
            return [state]
        if name == "BOOL.TO.INT":
            if state.boolean_stack:
                value = state.boolean_stack.pop()
                state.integer_stack.append(self._fresh(_ite(value.term, "1", "0"), "Int"))
            return [state]
        if name == "BOOL.ITE":
            if len(state.boolean_stack) >= 3:
                false_value = state.boolean_stack.pop()
                true_value = state.boolean_stack.pop()
                condition = state.boolean_stack.pop()
                state.boolean_stack.append(
                    self._fresh(_ite(condition.term, true_value.term, false_value.term), "Bool")
                )
            return [state]

        # Bit operations use unbounded Int in pushbase and do not have portable
        # equivalent semantics without changing the method signature to BitVec.
        if name.startswith("BIT."):
            self._unsupported(name, "requires an explicit Java bit-width/BitVec encoding")
            return [state]

        # String instructions.
        if name in {"STR_CONCAT", "STR_EQ"}:
            if len(state.string_stack) >= 2:
                right = state.string_stack.pop()
                left = state.string_stack.pop()
                if name == "STR_CONCAT":
                    state.string_stack.append(
                        self._fresh(f"(str.++ {left.term} {right.term})", "String")
                    )
                else:
                    state.boolean_stack.append(
                        self._fresh(_eq(left.term, right.term), "Bool")
                    )
            return [state]
        if name == "STR_LEN":
            if state.string_stack:
                value = state.string_stack.pop()
                state.integer_stack.append(self._fresh(f"(str.len {value.term})", "Int"))
            return [state]
        if name == "STR_CHAR_AT":
            if state.string_stack and state.integer_stack:
                index = state.integer_stack.pop()
                string = state.string_stack.pop()
                valid_condition = _and(
                    f"(<= 0 {index.term})",
                    f"(< {index.term} (str.len {string.term}))",
                )
                valid, invalid = self._split(state, valid_condition)
                result: List[_SymState] = []
                if valid is not None:
                    valid.string_stack.append(
                        self._fresh(f"(str.at {string.term} {index.term})", "String")
                    )
                    result.append(valid)
                if invalid is not None:
                    self._record_exception(invalid, "EX_INDEX_OUT_OF_BOUNDS")
                    result.append(invalid)
                return result
            return [state]
        if name == "STR_STARTS_WITH":
            if len(state.string_stack) >= 2:
                prefix = state.string_stack.pop()
                string = state.string_stack.pop()
                state.boolean_stack.append(
                    self._fresh(f"(str.prefixof {prefix.term} {string.term})", "Bool")
                )
            return [state]
        if name == "STR_CONTAINS":
            if len(state.string_stack) >= 2:
                substring = state.string_stack.pop()
                string = state.string_stack.pop()
                state.boolean_stack.append(
                    self._fresh(f"(str.contains {string.term} {substring.term})", "Bool")
                )
            return [state]
        if name == "STR_INDEX_OF":
            if len(state.string_stack) >= 2 and state.integer_stack:
                start = state.integer_stack.pop()
                substring = state.string_stack.pop()
                string = state.string_stack.pop()
                normalised_start = _ite(f"(< {start.term} 0)", "0", start.term)
                state.integer_stack.append(
                    self._fresh(
                        f"(str.indexof {string.term} {substring.term} {normalised_start})",
                        "Int",
                    )
                )
            return [state]
        if name == "STR_SUBSTRING":
            if state.string_stack and len(state.integer_stack) >= 2:
                end = state.integer_stack.pop()
                start = state.integer_stack.pop()
                string = state.string_stack.pop()
                valid_condition = _and(
                    f"(<= 0 {start.term})",
                    f"(<= {start.term} {end.term})",
                    f"(<= {end.term} (str.len {string.term}))",
                )
                valid, invalid = self._split(state, valid_condition)
                result: List[_SymState] = []
                if valid is not None:
                    valid.string_stack.append(
                        self._fresh(
                            f"(str.substr {string.term} {start.term} (- {end.term} {start.term}))",
                            "String",
                        )
                    )
                    result.append(valid)
                if invalid is not None:
                    self._record_exception(invalid, "EX_INDEX_OUT_OF_BOUNDS")
                    result.append(invalid)
                return result
            return [state]
        if name == "STR_REPLACE":
            if len(state.string_stack) >= 3:
                new = state.string_stack.pop()
                old = state.string_stack.pop()
                string = state.string_stack.pop()
                # pushbase and Java String.replace both replace every literal occurrence.
                operator = "str.replace_all"
                state.string_stack.append(
                    self._fresh(f"({operator} {string.term} {old.term} {new.term})", "String")
                )
            return [state]
        if name == "STR_REPLACE_ALL":
            # pushbase implements regex matching plus Java-style replacement-group
            # expansion. SMT-LIB's string replace operators are literal, not regex.
            self._unsupported(
                name,
                "pushbase STR_REPLACE_ALL is regex-based and cannot be represented by str.replace_all",
            )
            return [state]
        if name == "STR_TO_ASCII":
            if state.string_stack:
                string = state.string_stack.pop()
                state.integer_stack.append(
                    self._fresh(
                        _ite(
                            _eq(f"(str.len {string.term})", "0"),
                            _int_literal(-1),
                            f"(str.to_code (str.at {string.term} 0))",
                        ),
                        "Int",
                    )
                )
            return [state]
        if name in {
            "STR_TO_INT", "INT_TO_STR", "ASCII_TO_STR",
            "STR_TO_LOWER", "STR_TO_UPPER", "STR_TRIM",
        }:
            self._unsupported(name, "Java conversion/case semantics are solver-specific")
            return [state]
        if name == "STR_ITE":
            if state.boolean_stack and len(state.string_stack) >= 2:
                false_value = state.string_stack.pop()
                true_value = state.string_stack.pop()
                condition = state.boolean_stack.pop()
                state.string_stack.append(
                    self._fresh(_ite(condition.term, true_value.term, false_value.term), "String")
                )
            return [state]

        # Generic utilities and call context.
        if name == "DUP.ANY":
            for stack in state.typed_stacks():
                if stack:
                    top = stack[-1]
                    stack.append(self._fresh(top.term, top.sort))
                    return [state]
            if len(state.ref_stack) > (0 if self.signature.is_static else 1):
                top = state.ref_stack[-1]
                state.ref_stack.append(self._fresh(top.term, "Ref"))
            return [state]
        if name == "SWAP.ANY":
            for stack in state.typed_stacks():
                if len(stack) >= 2:
                    stack[-1], stack[-2] = stack[-2], stack[-1]
                    return [state]
            minimum = 0 if self.signature.is_static else 1
            if len(state.ref_stack) >= minimum + 2:
                state.ref_stack[-1], state.ref_stack[-2] = state.ref_stack[-2], state.ref_stack[-1]
            return [state]
        if name == "POP.ANY":
            self._pop_any(state)
            return [state]
        if name == "VALUE.FROM.ANY":
            value = self._pop_any(state)
            if value is not None:
                state.value_stack.append(value)
            return [state]
        if name == "ARG.COUNT":
            state.integer_stack.append(
                self._fresh(_int_literal(len(self.argument_infos)), "Int")
            )
            return [state]
        if name.startswith("ARG."):
            try:
                index = int(getattr(instruction, "index", name.split(".", 1)[1]))
            except (TypeError, ValueError):
                self._unsupported(name, "invalid argument index")
                return [state]
            if 0 <= index < len(state.arg_domains):
                token = self._next_token
                self._next_token += 1
                domain_source = state.arg_domains[index]
                view_source = state.arg_views[index]
                domain = self._fresh(domain_source.term, domain_source.sort, token=token)
                view = self._fresh(view_source.term, view_source.sort, token=token)
                state.value_stack.append(domain)
                self._push_view(state, view)
            return [state]
        if name == "RECEIVER.VALUE":
            if self.receiver is None:
                self._unsupported(name, "requires an instance receiver")
                return [state]
            info = self.receiver_value_info
            view = None if info is None else _jvalue_view(info)
            if view is None:
                self._unsupported(
                    name,
                    "receiver scalar payload is unknown; provide owner or receiverValueType",
                )
                return [state]
            _constructor, selector, target_sort = view
            payload = f"(select {state.heap.object_value} {self.receiver.term})"
            # Match concrete RECEIVER.VALUE: typed stack only, not value_stack.
            self._push_view(state, self._fresh(f"({selector} {payload})", target_sort))
            return [state]
        if name == "REF.ACTIVE":
            if self.receiver is not None:
                state.ref_stack.append(self._fresh(self.receiver.term, "Ref"))
            return [state]
        if name == "NULL.CONST":
            state.object_stack.append(self._fresh("JNull", "JValue"))
            return [state]
        if name == "RESULT.FROM.ANY":
            value = self._pop_any(state)
            if value is not None:
                state.result = value
                state.result_is_set = True
                state.halted = True
            return [state]
        if name == "RESULT.NULL":
            state.result = self._fresh("JNull", "JValue")
            state.result_is_set = True
            state.halted = True
            return [state]
        if name == "RESULT.ERROR":
            self._record_exception(state, "EX_MODELLED")
            state.result = self._fresh("JNull", "JValue")
            state.result_is_set = True
            state.halted = True
            return [state]
        if name in {"EXEC.IF", "ITE"}:
            if state.boolean_stack and len(state.exec_stack) >= 2:
                condition = state.boolean_stack.pop()
                true_branch = state.exec_stack.pop()
                false_branch = state.exec_stack.pop()
                true_state, false_state = self._split(state, condition.term)
                result: List[_SymState] = []
                if true_state is not None:
                    true_state.exec_stack.append(true_branch)
                    result.append(true_state)
                if false_state is not None:
                    false_state.exec_stack.append(false_branch)
                    result.append(false_state)
                return result
            return [state]
        if name == "EXEC.DO_TIMES":
            if state.integer_stack and state.exec_stack:
                count = state.integer_stack.pop()
                literal_count = _parse_constant_int(count.term)
                if literal_count is None:
                    self._unsupported(name, "symbolic loop count")
                    return [state]
                block = state.exec_stack.pop()
                repetitions = max(0, min(literal_count, 50))
                for _ in range(repetitions):
                    state.exec_stack.append(copy.deepcopy(block))
            return [state]

        # List/data-structure operations.  Receiver validation intentionally occurs
        # at the same point as concrete pushbase._active_data().  In particular,
        # operand-taking instructions first pop/check their operands; underflow is a
        # Push no-op and must not become EX_INVALID_RECEIVER merely because the active
        # receiver has another kind.
        shared_collection_kinds = ("list", "map", "set")

        if name == "DS.SIZE":
            if not self._require_declared_kinds(
                state, shared_collection_kinds, name
            ):
                return [state]
            state.integer_stack.append(self._fresh(self._size_term(state), "Int"))
            return [state]
        if name == "DS.IS_EMPTY":
            if not self._require_declared_kinds(
                state, shared_collection_kinds, name
            ):
                return [state]
            state.boolean_stack.append(
                self._fresh(_eq(self._size_term(state), "0"), "Bool")
            )
            return [state]
        if name == "DS.CLEAR":
            if not self._require_declared_kinds(
                state, shared_collection_kinds, name
            ):
                return [state]
            receiver = self._receiver_term()
            kind = self.signature.receiver_kind
            if kind == "list":
                state.heap.list_size = f"(store {state.heap.list_size} {receiver} 0)"
            elif kind == "map":
                state.heap.map_size = f"(store {state.heap.map_size} {receiver} 0)"
                empty_present = _const_array("(Array JValue Bool)", "false")
                state.heap.map_present = (
                    f"(store {state.heap.map_present} {receiver} {empty_present})"
                )
            elif kind == "set":
                state.heap.set_size = f"(store {state.heap.set_size} {receiver} 0)"
                empty_present = _const_array("(Array JValue Bool)", "false")
                state.heap.set_present = (
                    f"(store {state.heap.set_present} {receiver} {empty_present})"
                )
            return [state]
        if name == "DS.GET.INDEX":
            index = self._pop_integer(state)
            if index is None:
                return [state]
            if not self._require_declared_kind(state, "list", name):
                return [state]
            size = self._size_term(state, "list")
            valid_condition = _and(f"(<= 0 {index.term})", f"(< {index.term} {size})")
            valid, invalid = self._split(state, valid_condition)
            result: List[_SymState] = []
            if valid is not None:
                value = f"(select {self._list_array(valid)} {index.term})"
                result.extend(self._push_jvalue_result(valid, value, self.element_info))
            if invalid is not None:
                self._record_exception(invalid, "EX_INDEX_OUT_OF_BOUNDS")
                result.append(invalid)
            return result
        if name == "DS.SET.INDEX":
            value = self._pop_domain(state)
            index = self._pop_integer(state)
            if value is None or index is None:
                return [state]
            if not self._require_declared_kind(state, "list", name):
                return [state]
            size = self._size_term(state, "list")
            valid_condition = _and(f"(<= 0 {index.term})", f"(< {index.term} {size})")
            valid, invalid = self._split(state, valid_condition)
            result: List[_SymState] = []
            if valid is not None:
                receiver = self._receiver_term()
                old_array = self._list_array(valid)
                previous = f"(select {old_array} {index.term})"
                new_array = f"(store {old_array} {index.term} {self._box(value)})"
                valid.heap.list_data = (
                    f"(store {valid.heap.list_data} {receiver} {new_array})"
                )
                result.extend(self._push_jvalue_result(valid, previous, self.element_info))
            if invalid is not None:
                self._record_exception(invalid, "EX_INDEX_OUT_OF_BOUNDS")
                result.append(invalid)
            return result
        if name == "DS.INSERT.AT.INDEX":
            value = self._pop_domain(state)
            index = self._pop_integer(state)
            if value is None or index is None:
                return [state]
            if not self._require_declared_kind(state, "list", name):
                return [state]
            size = self._size_term(state, "list")
            valid_condition = _and(f"(<= 0 {index.term})", f"(<= {index.term} {size})")
            valid, invalid = self._split(state, valid_condition)
            result: List[_SymState] = []
            if valid is not None:
                receiver = self._receiver_term()
                old_array = self._list_array(valid)
                new_array = (
                    f"(list-insert {old_array} {size} {index.term} {self._box(value)})"
                )
                valid.heap.list_data = (
                    f"(store {valid.heap.list_data} {receiver} {new_array})"
                )
                valid.heap.list_size = (
                    f"(store {valid.heap.list_size} {receiver} (+ {size} 1))"
                )
                result.append(valid)
            if invalid is not None:
                self._record_exception(invalid, "EX_INDEX_OUT_OF_BOUNDS")
                result.append(invalid)
            return result
        if name == "DS.APPEND":
            value = self._pop_domain(state)
            if value is None:
                return [state]
            if not self._require_declared_kind(state, "list", name):
                return [state]
            receiver = self._receiver_term()
            size = self._size_term(state, "list")
            old_array = self._list_array(state)
            new_array = f"(store {old_array} {size} {self._box(value)})"
            state.heap.list_data = f"(store {state.heap.list_data} {receiver} {new_array})"
            state.heap.list_size = f"(store {state.heap.list_size} {receiver} (+ {size} 1))"
            return [state]
        if name == "DS.REMOVE.INDEX":
            index = self._pop_integer(state)
            if index is None:
                return [state]
            if not self._require_declared_kind(state, "list", name):
                return [state]
            size = self._size_term(state, "list")
            valid_condition = _and(f"(<= 0 {index.term})", f"(< {index.term} {size})")
            valid, invalid = self._split(state, valid_condition)
            result: List[_SymState] = []
            if valid is not None:
                receiver = self._receiver_term()
                old_array = self._list_array(valid)
                previous = f"(select {old_array} {index.term})"
                new_array = f"(list-remove {old_array} {size} {index.term})"
                valid.heap.list_data = (
                    f"(store {valid.heap.list_data} {receiver} {new_array})"
                )
                valid.heap.list_size = (
                    f"(store {valid.heap.list_size} {receiver} (- {size} 1))"
                )
                result.extend(self._push_jvalue_result(valid, previous, self.element_info))
            if invalid is not None:
                self._record_exception(invalid, "EX_INDEX_OUT_OF_BOUNDS")
                result.append(invalid)
            return result
        if name in {"DS.PEEK.LAST", "DS.POP.LAST"}:
            if not self._require_declared_kind(state, "list", name):
                return [state]
            size = self._size_term(state, "list")
            nonempty, empty = self._split(state, f"(> {size} 0)")
            result: List[_SymState] = []
            if nonempty is not None:
                receiver = self._receiver_term()
                index_term = f"(- {size} 1)"
                old_array = self._list_array(nonempty)
                value = f"(select {old_array} {index_term})"
                if name == "DS.POP.LAST":
                    nonempty.heap.list_size = (
                        f"(store {nonempty.heap.list_size} {receiver} {index_term})"
                    )
                result.extend(self._push_jvalue_result(nonempty, value, self.element_info))
            if empty is not None:
                self._record_exception(empty, "EX_EMPTY_DATA_STRUCTURE")
                result.append(empty)
            return result
        if name == "DS.LAST.INDEX":
            if not self._require_declared_kind(state, "list", name):
                return [state]
            size = self._size_term(state, "list")
            state.integer_stack.append(self._fresh(f"(- {size} 1)", "Int"))
            return [state]
        if name == "DS.FIRST.INDEX":
            if not self._require_declared_kind(state, "list", name):
                return [state]
            size = self._size_term(state, "list")
            state.integer_stack.append(
                self._fresh(_ite(_eq(size, "0"), _int_literal(-1), "0"), "Int")
            )
            return [state]
        if name in {"DS.INDEX_OF", "DS.LAST_INDEX_OF"}:
            value = self._pop_domain(state)
            if value is None:
                return [state]
            if not self._require_declared_kind(state, "list", name):
                return [state]
            helper = "list-index-of" if name == "DS.INDEX_OF" else "list-last-index-of"
            state.integer_stack.append(
                self._fresh(
                    f"({helper} {self._list_array(state)} {self._size_term(state, 'list')} {self._box(value)})",
                    "Int",
                )
            )
            return [state]
        if name == "DS.CONTAINS":
            value = self._pop_domain(state)
            if value is None:
                return [state]
            if not self._require_declared_kinds(
                state, shared_collection_kinds, name
            ):
                return [state]
            boxed = self._box(value)
            kind = self.signature.receiver_kind
            if kind == "list":
                term = (
                    f"(list-contains {self._list_array(state)} "
                    f"{self._size_term(state, 'list')} {boxed})"
                )
            elif kind == "map":
                term = f"(select {self._map_present_array(state)} {boxed})"
            else:  # set
                term = f"(select {self._set_present_array(state)} {boxed})"
            state.boolean_stack.append(self._fresh(term, "Bool"))
            return [state]

        # Map operations.  Concrete MAP.PUT/GET/REMOVE first consume operands and
        # only then validate that the active object is map-backed.
        if name == "MAP.SIZE":
            if not self._require_declared_kind(state, "map", name):
                return [state]
            state.integer_stack.append(self._fresh(self._size_term(state, "map"), "Int"))
            return [state]
        if name == "MAP.CLEAR":
            if not self._require_declared_kind(state, "map", name):
                return [state]
            receiver = self._receiver_term()
            state.heap.map_size = f"(store {state.heap.map_size} {receiver} 0)"
            empty_present = _const_array("(Array JValue Bool)", "false")
            state.heap.map_present = f"(store {state.heap.map_present} {receiver} {empty_present})"
            return [state]
        if name == "MAP.PUT":
            value = self._pop_domain(state)
            key = self._pop_domain(state)
            if value is None or key is None:
                return [state]
            if not self._require_declared_kind(state, "map", name):
                return [state]
            receiver = self._receiver_term()
            boxed_key = self._box(key)
            boxed_value = self._box(value)
            present_array = self._map_present_array(state)
            data_array = self._map_data_array(state)
            present = f"(select {present_array} {boxed_key})"
            previous = _ite(present, f"(select {data_array} {boxed_key})", "JNull")
            old_size = self._size_term(state, "map")
            new_present = f"(store {present_array} {boxed_key} true)"
            new_data = f"(store {data_array} {boxed_key} {boxed_value})"
            state.heap.map_present = f"(store {state.heap.map_present} {receiver} {new_present})"
            state.heap.map_data = f"(store {state.heap.map_data} {receiver} {new_data})"
            state.heap.map_size = (
                f"(store {state.heap.map_size} {receiver} "
                f"{_ite(present, old_size, f'(+ {old_size} 1)')})"
            )
            return self._push_jvalue_result(state, previous, self.value_info)
        if name == "MAP.GET":
            key = self._pop_domain(state)
            if key is None:
                return [state]
            if not self._require_declared_kind(state, "map", name):
                return [state]
            boxed_key = self._box(key)
            present_array = self._map_present_array(state)
            data_array = self._map_data_array(state)
            present = f"(select {present_array} {boxed_key})"
            value = _ite(present, f"(select {data_array} {boxed_key})", "JNull")
            return self._push_jvalue_result(state, value, self.value_info)
        if name == "MAP.REMOVE":
            key = self._pop_domain(state)
            if key is None:
                return [state]
            if not self._require_declared_kind(state, "map", name):
                return [state]
            receiver = self._receiver_term()
            boxed_key = self._box(key)
            present_array = self._map_present_array(state)
            data_array = self._map_data_array(state)
            present = f"(select {present_array} {boxed_key})"
            value = _ite(present, f"(select {data_array} {boxed_key})", "JNull")
            old_size = self._size_term(state, "map")
            new_present = f"(store {present_array} {boxed_key} false)"
            state.heap.map_present = f"(store {state.heap.map_present} {receiver} {new_present})"
            state.heap.map_size = (
                f"(store {state.heap.map_size} {receiver} "
                f"{_ite(present, f'(- {old_size} 1)', old_size)})"
            )
            return self._push_jvalue_result(state, value, self.value_info)
        if name == "MAP.CONTAINS.KEY":
            key = self._pop_domain(state)
            if key is None:
                return [state]
            if not self._require_declared_kind(state, "map", name):
                return [state]
            state.boolean_stack.append(
                self._fresh(
                    f"(select {self._map_present_array(state)} {self._box(key)})",
                    "Bool",
                )
            )
            return [state]

        # Set operations.  As in concrete pushbase, operand-taking operations are a
        # no-op on underflow before receiver validation is attempted.
        if name == "SET.SIZE":
            if not self._require_declared_kind(state, "set", name):
                return [state]
            state.integer_stack.append(self._fresh(self._size_term(state, "set"), "Int"))
            return [state]
        if name == "SET.CLEAR":
            if not self._require_declared_kind(state, "set", name):
                return [state]
            receiver = self._receiver_term()
            state.heap.set_size = f"(store {state.heap.set_size} {receiver} 0)"
            empty_present = _const_array("(Array JValue Bool)", "false")
            state.heap.set_present = f"(store {state.heap.set_present} {receiver} {empty_present})"
            return [state]
        if name in {"SET.ADD", "SET.REMOVE", "SET.CONTAINS"}:
            value = self._pop_domain(state)
            if value is None:
                return [state]
            if not self._require_declared_kind(state, "set", name):
                return [state]
            receiver = self._receiver_term()
            boxed = self._box(value)
            present_array = self._set_present_array(state)
            present = f"(select {present_array} {boxed})"
            if name == "SET.CONTAINS":
                state.boolean_stack.append(self._fresh(present, "Bool"))
                return [state]
            old_size = self._size_term(state, "set")
            desired = "true" if name == "SET.ADD" else "false"
            new_present = f"(store {present_array} {boxed} {desired})"
            state.heap.set_present = f"(store {state.heap.set_present} {receiver} {new_present})"
            if name == "SET.ADD":
                new_size = _ite(present, old_size, f"(+ {old_size} 1)")
                result_bool = _not(present)
            else:
                new_size = _ite(present, f"(- {old_size} 1)", old_size)
                result_bool = present
            state.heap.set_size = f"(store {state.heap.set_size} {receiver} {new_size})"
            state.boolean_stack.append(self._fresh(result_bool, "Bool"))
            return [state]

        self._unsupported(name)
        return [state]

    def _run(self, program: pb.PushProgram) -> List[_SymState]:
        active = self._initial_states()
        for state in active:
            state.exec_stack.extend(reversed(list(program.code or [])))
        finished: List[_SymState] = []

        while active:
            state = active.pop()
            branched = False
            while state.exec_stack and not state.halted and state.step_count < self.config.max_steps:
                atom = state.exec_stack.pop()
                state.step_count += 1
                if isinstance(atom, (list, tuple)):
                    state.exec_stack.extend(reversed(list(atom)))
                    continue
                if isinstance(atom, pb.PushInstruction):
                    branches = self._execute_instruction(state, atom)
                else:
                    branches = self._literal_atom(state, atom)

                branches = [branch for branch in branches if branch.path_condition != "false"]
                self._check_path_bound(branches)
                if len(branches) == 1 and branches[0] is state:
                    continue
                active.extend(branches)
                self._check_path_bound(active + finished)
                branched = True
                break

            if branched:
                continue
            if state.exec_stack and state.step_count >= self.config.max_steps:
                self._record_exception(state, "EX_STEP_LIMIT")
            finished.append(state)
            self._check_path_bound(finished + active)

        return finished

    def _extract_value(self, state: _SymState) -> Optional[_SVal]:
        if state.result_is_set:
            return state.result
        info = self.return_info
        if info.category == "void":
            return self._fresh("JNull", "JValue")
        if info.category == "error":
            return None

        # Mirror PushGPInterpreter._extract_result_from_state.  In particular,
        # implicit result extraction must not turn an unrelated JNull/object-stack
        # value into a normal primitive/boxed/string result. Null for those return
        # types is only observable when a program explicitly executes RESULT.NULL.
        if info.category in {"int", "boxed_int"} and state.integer_stack:
            return state.integer_stack[-1]
        if info.category in {"real", "boxed_real"} and state.real_stack:
            return state.real_stack[-1]
        if info.category in {"bool", "boxed_bool"} and state.boolean_stack:
            return state.boolean_stack[-1]
        if info.category in {"char", "boxed_char", "string_ref"} and state.string_stack:
            return state.string_stack[-1]

        minimum_refs = 0 if self.signature.is_static else 1
        if info.category == "reference" and len(state.ref_stack) > minimum_refs:
            return state.ref_stack[-1]

        if info.category == "null":
            if state.object_stack and state.object_stack[-1].term == "JNull":
                return state.object_stack[-1]
            return None

        # java.lang.Object accepts object, reference, or boxed primitive/string
        # values. Keep the concrete runtime's priority order.
        if info.category == "object":
            if state.object_stack:
                return state.object_stack[-1]
            if len(state.ref_stack) > minimum_refs:
                return state.ref_stack[-1]
            for stack in (
                state.string_stack,
                state.integer_stack,
                state.boolean_stack,
                state.real_stack,
            ):
                if stack:
                    return stack[-1]
        return None

    def _result_term(self, state: _SymState) -> str:
        heap_term = state.heap.term()
        if state.exception != "EX_NONE":
            return f"(mk-result {heap_term} OUT_THROWN JNull {state.exception})"
        if self.return_info.category == "error":
            return f"(mk-result {heap_term} OUT_MISSING JNull EX_NONE)"
        value = self._extract_value(state)
        if value is None:
            return f"(mk-result {heap_term} OUT_MISSING JNull EX_NONE)"
        return f"(mk-result {heap_term} OUT_NORMAL {self._box(value)} EX_NONE)"

    def _merge_path_results(self, states: Sequence[_SymState]) -> str:
        grouped: "OrderedDict[str, List[str]]" = OrderedDict()
        for state in states:
            grouped.setdefault(self._result_term(state), []).append(state.path_condition)

        fallback = "(mk-result pre OUT_MISSING JNull EX_INTERNAL)"
        body = fallback
        for result_term, conditions in reversed(list(grouped.items())):
            condition = _or(*conditions)
            body = _ite(condition, result_term, body)
        return body

    def _parameter_declarations(self) -> List[Tuple[str, str]]:
        declarations = [("pre", "Heap")]
        if not self.signature.is_static:
            declarations.append(("receiver", "Int"))
        for index, info in enumerate(self.argument_infos):
            declarations.append((f"arg{index}", info.smt_sort))
        return declarations

    def _receiver_precondition(self) -> str:
        if self.signature.is_static:
            return "true"
        receiver = "receiver"
        kind = self.signature.receiver_kind
        expected_kind = {
            "list": "K_LIST",
            "map": "K_MAP",
            "set": "K_SET",
            "object": "K_OBJECT",
        }.get(kind)
        terms = [f"(<= 0 {receiver})"]
        if expected_kind is not None:
            terms.append(_eq(f"(select (heap-kind pre) {receiver})", expected_kind))
        if kind in {"list", "map", "set"}:
            size_selector = {
                "list": "heap-list-size",
                "map": "heap-map-size",
                "set": "heap-set-size",
            }[kind]
            terms.append(f"(<= 0 (select ({size_selector} pre) {receiver}))")
        if self.receiver_value_info is not None:
            view = _jvalue_view(self.receiver_value_info)
            if view is not None:
                constructor, _selector, _sort = view
                payload = f"(select (heap-object-value pre) {receiver})"
                terms.append(_tester(constructor, payload))
        return _and(*terms)

    def _argument_precondition(self) -> str:
        return _and(
            *[
                self._input_precondition(f"arg{index}", info)
                for index, info in enumerate(self.argument_infos)
            ]
        )

    def compile(
        self,
        program: pb.PushProgram,
        *,
        force_missing: bool = False,
    ) -> CompiledSMTMethod:
        states = [] if force_missing else self._run(program)
        path_body = (
            "(mk-result pre OUT_MISSING JNull EX_NONE)"
            if force_missing
            else self._merge_path_results(states)
        )
        receiver_pre = self._receiver_precondition()
        argument_pre = self._argument_precondition()
        overall_pre = _and(receiver_pre, argument_pre)
        precondition_name = f"{self.smt_name}_pre"

        invalid_argument = "(mk-result pre OUT_THROWN JNull EX_INVALID_ARGUMENT)"
        invalid_receiver = "(mk-result pre OUT_THROWN JNull EX_INVALID_RECEIVER)"
        guarded_body = _ite(
            receiver_pre,
            _ite(argument_pre, path_body, invalid_argument),
            invalid_receiver,
        )
        parameters = " ".join(
            f"({name} {sort})" for name, sort in self._parameter_declarations()
        )

        comment_lines: List[str] = []
        if self.config.emit_comments:
            owner = f"{self.signature.owner}." if self.signature.owner else ""
            comment_lines.extend(
                [
                    f"; Java/trace method: {owner}{self.signature.method_name}",
                    f"; Receiver kind: {self.signature.receiver_kind}",
                    f"; Argument types: {list(self.signature.argument_types)!r}",
                    f"; Return type: {self.signature.return_type}",
                    f"; Symbolic paths: {len(states)}",
                ]
            )
            comment_lines.extend(f"; WARNING: {warning}" for warning in self.warnings)

        text = "\n".join(
            comment_lines
            + [
                f"(define-fun {precondition_name} ({parameters}) Bool",
                f"  {overall_pre})",
                f"(define-fun {self.smt_name} ({parameters}) StubResult",
                f"  {guarded_body})",
            ]
        )
        return CompiledSMTMethod(
            signature=self.signature,
            smt_name=self.smt_name,
            precondition_name=precondition_name,
            text=text,
            path_count=len(states),
            warnings=tuple(self.warnings),
        )


# ---------------------------------------------------------------------------
# SMT prelude and public compilation API
# ---------------------------------------------------------------------------


def _smt_prelude(config: SMTExportConfig) -> str:
    empty_jvalue_array = _const_array("(Array Int JValue)", "JNull")
    empty_object_values = _const_array("(Array Int JValue)", "JNull")
    empty_list_outer = _const_array("(Array Int (Array Int JValue))", empty_jvalue_array)
    empty_map_present_inner = _const_array("(Array JValue Bool)", "false")
    empty_map_present_outer = _const_array(
        "(Array Int (Array JValue Bool))", empty_map_present_inner
    )
    empty_map_data_inner = _const_array("(Array JValue JValue)", "JNull")
    empty_map_data_outer = _const_array(
        "(Array Int (Array JValue JValue))", empty_map_data_inner
    )
    empty_set_inner = _const_array("(Array JValue Bool)", "false")
    empty_set_outer = _const_array("(Array Int (Array JValue Bool))", empty_set_inner)

    lines = [
        f"(set-logic {config.logic})",
        "(set-option :produce-models true)",
        "",
        "; Boxed Java values used by receiver payloads and collection/map contents.",
        "(declare-datatypes () ((JValue",
        "  (JNull)",
        "  (JInt (j-int Int))",
        "  (JBool (j-bool Bool))",
        "  (JReal (j-real Real))",
        "  (JString (j-string String))",
        "  (JRef (j-ref Int)))))",
        "",
        "(declare-datatypes () ((ObjectKind (K_NONE) (K_LIST) (K_MAP) (K_SET) (K_OBJECT))))",
        "(declare-datatypes () ((OutcomeKind (OUT_NORMAL) (OUT_THROWN) (OUT_MISSING))))",
        "(declare-datatypes () ((ExceptionKind",
        "  (EX_NONE)",
        "  (EX_INVALID_RECEIVER)",
        "  (EX_INVALID_ARGUMENT)",
        "  (EX_INDEX_OUT_OF_BOUNDS)",
        "  (EX_EMPTY_DATA_STRUCTURE)",
        "  (EX_ARITHMETIC)",
        "  (EX_MODELLED)",
        "  (EX_STEP_LIMIT)",
        "  (EX_INTERNAL))))",
        "",
        "; One symbolic heap supports multiple object references and aliasing.",
        "(declare-datatypes () ((Heap",
        "  (mk-heap",
        "    (heap-kind (Array Int ObjectKind))",
        "    (heap-object-value (Array Int JValue))",
        "    (heap-list-size (Array Int Int))",
        "    (heap-list-data (Array Int (Array Int JValue)))",
        "    (heap-map-size (Array Int Int))",
        "    (heap-map-present (Array Int (Array JValue Bool)))",
        "    (heap-map-data (Array Int (Array JValue JValue)))",
        "    (heap-set-size (Array Int Int))",
        "    (heap-set-present (Array Int (Array JValue Bool)))))))",
        "",
        "(declare-datatypes () ((StubResult",
        "  (mk-result",
        "    (result-heap Heap)",
        "    (result-outcome OutcomeKind)",
        "    (result-value JValue)",
        "    (result-exception ExceptionKind)))))",
        "",
        "; Java integer arithmetic helpers (division truncates toward zero).",
        "(define-fun java-abs ((value Int)) Int (ite (< value 0) (- value) value))",
        "(define-fun java-div ((left Int) (right Int)) Int",
        "  (let ((quotient (div (java-abs left) (java-abs right))))",
        "    (ite (= (< left 0) (< right 0)) quotient (- quotient))))",
        "(define-fun java-rem ((left Int) (right Int)) Int",
        "  (- left (* right (java-div left right))))",
        "",
        "; Executable list-array transformations and searches.",
        ";",
        "; These helpers deliberately avoid global forall axioms.  list-insert and",
        "; list-remove are array-valued lambda expressions, so selecting an element",
        "; reduces directly to an ite/select term.  indexOf/lastIndexOf use recursive",
        "; searches that unfold only when a query actually calls them.  This keeps",
        "; unrelated stubs (size/isEmpty/get/etc.) in a quantifier-free solver context.",
        "(define-fun list-insert",
        "  ((data (Array Int JValue)) (size Int) (index Int) (value JValue))",
        "  (Array Int JValue)",
        "  (lambda ((position Int))",
        "    (ite (and (<= 0 position) (< position (+ size 1)))",
        "         (ite (< position index)",
        "              (select data position)",
        "              (ite (= position index) value (select data (- position 1))))",
        "         (select data position))))",
        "",
        "(define-fun list-remove",
        "  ((data (Array Int JValue)) (size Int) (index Int))",
        "  (Array Int JValue)",
        "  (lambda ((position Int))",
        "    (ite (and (<= 0 position) (< position (- size 1)))",
        "         (ite (< position index)",
        "              (select data position)",
        "              (select data (+ position 1)))",
        "         (select data position))))",
        "",
        "; Exact first-match search.  For concrete sizes this unfolds to a finite",
        "; chain of select/equality tests; symbolic unbounded sizes retain recursion",
        "; only in queries that actually use indexOf/contains/remove-by-value.",
        "(define-fun-rec list-index-of-from",
        "  ((data (Array Int JValue)) (size Int) (value JValue) (position Int)) Int",
        "  (ite (>= position size)",
        "       (- 1)",
        "       (ite (= (select data position) value)",
        "            position",
        "            (list-index-of-from data size value (+ position 1)))))",
        "",
        "(define-fun list-index-of",
        "  ((data (Array Int JValue)) (size Int) (value JValue)) Int",
        "  (ite (<= size 0)",
        "       (- 1)",
        "       (list-index-of-from data size value 0)))",
        "",
        "; Exact last-match search, scanning from size-1 toward zero.",
        "(define-fun-rec list-last-index-of-from",
        "  ((data (Array Int JValue)) (value JValue) (position Int)) Int",
        "  (ite (< position 0)",
        "       (- 1)",
        "       (ite (= (select data position) value)",
        "            position",
        "            (list-last-index-of-from data value (- position 1)))))",
        "",
        "(define-fun list-last-index-of",
        "  ((data (Array Int JValue)) (size Int) (value JValue)) Int",
        "  (ite (<= size 0)",
        "       (- 1)",
        "       (list-last-index-of-from data value (- size 1))))",
        "",
        "(define-fun list-contains ((data (Array Int JValue)) (size Int) (value JValue)) Bool",
        "  (<= 0 (list-index-of data size value)))",
    ]

    if config.include_empty_heap_helpers:
        lines.extend(
            [
                "",
                "; Constructors useful when asserting or composing generated stubs.",
                "(define-fun empty-heap () Heap",
                "  (mk-heap",
                f"    {_const_array('(Array Int ObjectKind)', 'K_NONE')}",
                f"    {empty_object_values}",
                f"    {_const_array('(Array Int Int)', '0')}",
                f"    {empty_list_outer}",
                f"    {_const_array('(Array Int Int)', '0')}",
                f"    {empty_map_present_outer}",
                f"    {empty_map_data_outer}",
                f"    {_const_array('(Array Int Int)', '0')}",
                f"    {empty_set_outer}))",
                "",
                "(define-fun heap-new-object ((heap Heap) (reference Int) (value JValue)) Heap",
                "  (mk-heap",
                "    (store (heap-kind heap) reference K_OBJECT)",
                "    (store (heap-object-value heap) reference value)",
                "    (heap-list-size heap)",
                "    (heap-list-data heap)",
                "    (heap-map-size heap)",
                "    (heap-map-present heap)",
                "    (heap-map-data heap)",
                "    (heap-set-size heap)",
                "    (heap-set-present heap)))",
                "",
                "(define-fun heap-new-list ((heap Heap) (reference Int)) Heap",
                "  (mk-heap",
                "    (store (heap-kind heap) reference K_LIST)",
                "    (heap-object-value heap)",
                "    (store (heap-list-size heap) reference 0)",
                f"    (store (heap-list-data heap) reference {empty_jvalue_array})",
                "    (heap-map-size heap)",
                "    (heap-map-present heap)",
                "    (heap-map-data heap)",
                "    (heap-set-size heap)",
                "    (heap-set-present heap)))",
                "",
                "(define-fun heap-new-map ((heap Heap) (reference Int)) Heap",
                "  (mk-heap",
                "    (store (heap-kind heap) reference K_MAP)",
                "    (heap-object-value heap)",
                "    (heap-list-size heap)",
                "    (heap-list-data heap)",
                "    (store (heap-map-size heap) reference 0)",
                f"    (store (heap-map-present heap) reference {empty_map_present_inner})",
                f"    (store (heap-map-data heap) reference {empty_map_data_inner})",
                "    (heap-set-size heap)",
                "    (heap-set-present heap)))",
                "",
                "(define-fun heap-new-set ((heap Heap) (reference Int)) Heap",
                "  (mk-heap",
                "    (store (heap-kind heap) reference K_SET)",
                "    (heap-object-value heap)",
                "    (heap-list-size heap)",
                "    (heap-list-data heap)",
                "    (heap-map-size heap)",
                "    (heap-map-present heap)",
                "    (heap-map-data heap)",
                "    (store (heap-set-size heap) reference 0)",
                f"    (store (heap-set-present heap) reference {empty_set_inner})))",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def load_method_signatures(
    source: str | Path | Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> List[MethodSignature]:
    """Load explicit method signatures from JSON-compatible data or a file.

    Accepted top-level JSON forms are a list of method mappings or an object with
    a ``methods``/``signatures`` array.
    """

    if isinstance(source, (str, Path)):
        raw: Any = json.loads(Path(source).read_text(encoding="utf-8"))
    else:
        raw = source
    if isinstance(raw, Mapping):
        if "methods" in raw:
            raw = raw["methods"]
        elif "signatures" in raw:
            raw = raw["signatures"]
        else:
            raw = [raw]
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes, bytearray)):
        raise TypeError("Signature JSON must contain a method object or method array")
    return [MethodSignature.from_mapping(item) for item in raw]


def compile_method_to_smt(
    program: pb.PushProgram,
    signature: MethodSignature,
    *,
    config: Optional[SMTExportConfig] = None,
) -> CompiledSMTMethod:
    """Compile one Push program without rendering the shared SMT prelude."""

    config = config or SMTExportConfig()
    signature = _complete_signature_hints(signature)
    smt_name = _unique_method_name(config.function_prefix, signature, set())
    return _MethodCompiler(signature, smt_name, config).compile(program)


def compile_genome_to_smt(
    genome: pb.PushGPGenome,
    training_data: Optional[Sequence[Any]] = None,
    *,
    signatures: Optional[Iterable[MethodSignature]] = None,
    config: Optional[SMTExportConfig] = None,
) -> SMTModule:
    """Compile a learned genome into one self-contained SMT-LIB 2 module.

    Supply either ``training_data`` for automatic signature inference or explicit
    ``MethodSignature`` objects.  Explicit signatures are preferable when Java
    reflection already gives you exact declared types and static/instance status.
    """

    if genome is None:
        raise ValueError("genome cannot be None")
    config = config or SMTExportConfig()
    if signatures is None:
        if training_data is None:
            raise ValueError("training_data or signatures must be supplied")
        resolved_signatures = infer_method_signatures(list(training_data))
    else:
        resolved_signatures = list(signatures)
        if training_data is not None:
            raise ValueError("Supply either training_data or signatures, not both")
    if not resolved_signatures:
        raise ValueError("No method signatures were supplied or inferred")

    sections = [_smt_prelude(config)]
    methods: "OrderedDict[str, CompiledSMTMethod]" = OrderedDict()
    module_warnings: List[str] = []
    used_names: set[str] = set()
    seen_method_ids: set[str] = set()

    for signature in resolved_signatures:
        signature = _complete_signature_hints(signature)
        if signature.method_name in seen_method_ids:
            raise SignatureInferenceError(
                f"Duplicate method identifier {signature.method_name!r}; "
                "method identifiers must be globally unique (include owner/descriptor for overloads)"
            )
        seen_method_ids.add(signature.method_name)
        program = genome.methods.get(signature.method_name)
        force_missing = program is None
        if force_missing:
            program = pb.PushProgram([])
            module_warnings.append(
                f"No learned program for {signature.method_name!r}; emitted OUT_MISSING stub"
            )
        smt_name = _unique_method_name(config.function_prefix, signature, used_names)
        compiler = _MethodCompiler(signature, smt_name, config)
        compiled = compiler.compile(program, force_missing=force_missing)
        methods[signature.method_name] = compiled
        module_warnings.extend(compiled.warnings)
        sections.append(compiled.text + "\n")

    if config.include_check_sat:
        sections.append("(check-sat)\n")

    text = "\n".join(section.rstrip() for section in sections if section).rstrip() + "\n"
    if config.validate_output:
        validate_smt2_structure(text)
    return SMTModule(text=text, methods=methods, warnings=module_warnings)


def export_genome_to_smt(
    genome: pb.PushGPGenome,
    output_path: str | Path,
    training_data: Optional[Sequence[Any]] = None,
    *,
    signatures: Optional[Iterable[MethodSignature]] = None,
    config: Optional[SMTExportConfig] = None,
    manifest_path: Optional[str | Path] = None,
) -> SMTModule:
    """Compile and write a genome, optionally writing a JSON manifest beside it."""

    module = compile_genome_to_smt(
        genome,
        training_data,
        signatures=signatures,
        config=config,
    )
    module.write(output_path)
    if manifest_path is not None:
        module.write_manifest(manifest_path)
    return module


def validate_smt2_structure(text: str) -> None:
    """Perform a dependency-free structural SMT-LIB check.

    This is intentionally not a solver/type checker.  It catches unbalanced
    parentheses, unterminated strings, and unexpected closing delimiters before a
    generated file is passed to Z3/cvc5.
    """

    depth = 0
    index = 0
    length = len(text)
    in_string = False
    in_comment = False

    while index < length:
        char = text[index]
        if in_comment:
            if char == "\n":
                in_comment = False
            index += 1
            continue
        if in_string:
            if char == '"':
                # SMT-LIB escapes a quote inside a string as two quotes.
                if index + 1 < length and text[index + 1] == '"':
                    index += 2
                    continue
                in_string = False
            index += 1
            continue
        if char == ";":
            in_comment = True
        elif char == '"':
            in_string = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                raise SMTExportError(f"Unexpected ')' at character {index}")
        index += 1

    if in_string:
        raise SMTExportError("Unterminated SMT string literal")
    if depth != 0:
        raise SMTExportError(f"Unbalanced SMT parentheses: final depth {depth}")


def validate_smt2_with_z3(
    text: str,
    *,
    library_path: Optional[str] = None,
) -> None:
    """Parse/type-check generated declarations with the Z3 C API when available.

    This helper does not require the ``z3-solver`` Python package.  It loads an
    installed ``libz3`` dynamically.  A missing library raises ``RuntimeError``;
    parser/type errors raise ``SMTExportError``.
    """

    resolved = library_path or ctypes.util.find_library("z3")
    if not resolved:
        raise RuntimeError("No libz3 shared library was found")
    try:
        library = ctypes.CDLL(resolved)
    except OSError as exc:
        raise RuntimeError(f"Could not load libz3 from {resolved!r}") from exc

    library.Z3_mk_config.restype = ctypes.c_void_p
    library.Z3_mk_context.argtypes = [ctypes.c_void_p]
    library.Z3_mk_context.restype = ctypes.c_void_p
    library.Z3_del_config.argtypes = [ctypes.c_void_p]
    library.Z3_del_context.argtypes = [ctypes.c_void_p]
    error_handler_type = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int)
    captured_error_codes: List[int] = []

    def capture_error(_context: ctypes.c_void_p, error_code: int) -> None:
        captured_error_codes.append(int(error_code))

    error_handler = error_handler_type(capture_error)
    library.Z3_set_error_handler.argtypes = [ctypes.c_void_p, error_handler_type]
    library.Z3_parse_smtlib2_string.argtypes = [
        ctypes.c_void_p,
        ctypes.c_char_p,
        ctypes.c_uint,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_uint,
        ctypes.c_void_p,
        ctypes.c_void_p,
    ]
    library.Z3_parse_smtlib2_string.restype = ctypes.c_void_p
    library.Z3_get_error_code.argtypes = [ctypes.c_void_p]
    library.Z3_get_error_code.restype = ctypes.c_int
    library.Z3_get_error_msg.argtypes = [ctypes.c_void_p, ctypes.c_int]
    library.Z3_get_error_msg.restype = ctypes.c_char_p

    config = library.Z3_mk_config()
    if not config:
        raise RuntimeError("Z3_mk_config failed")
    context = library.Z3_mk_context(config)
    library.Z3_del_config(config)
    if not context:
        raise RuntimeError("Z3_mk_context failed")
    try:
        # Z3's default C error handler terminates the process on malformed input.
        # Install a callback so validation remains a normal Python exception.
        library.Z3_set_error_handler(context, error_handler)
        library.Z3_parse_smtlib2_string(
            context,
            text.encode("utf-8"),
            0,
            None,
            None,
            0,
            None,
            None,
        )
        error_code = int(library.Z3_get_error_code(context))
        if error_code == 0 and captured_error_codes:
            error_code = captured_error_codes[-1]
        if error_code != 0:
            raw_message = library.Z3_get_error_msg(context, error_code)
            message = (raw_message or b"unknown Z3 error").decode("utf-8", errors="replace")
            raise SMTExportError(f"Z3 rejected generated SMT-LIB: {message}")
    finally:
        library.Z3_del_context(context)


__all__ = [
    "CompiledSMTMethod",
    "MethodSignature",
    "SMTExportConfig",
    "SMTExportError",
    "SMTModule",
    "SignatureInferenceError",
    "SymbolicPathLimitError",
    "UnsupportedInstructionError",
    "compile_genome_to_smt",
    "compile_method_to_smt",
    "export_genome_to_smt",
    "infer_method_signatures",
    "load_method_signatures",
    "validate_smt2_structure",
    "validate_smt2_with_z3",
]
