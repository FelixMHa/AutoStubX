from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any

from rungp import loadtrainingdata


INT = {"byte", "short", "int", "long", "b", "s", "i", "j"}
REAL = {"float", "double", "f", "d"}
BOOL = {"boolean", "bool", "z"}
CHAR = {"char", "c"}
VOID = {"void", "v", "java.lang.void", ""}
ERROR = {"error", "exception", "throw", "thrown"}
BOXED_INT = {"java.lang.byte", "java.lang.short", "java.lang.integer", "java.lang.long"}
BOXED_REAL = {"java.lang.float", "java.lang.double"}
BOXED_BOOL = {"java.lang.boolean"}
BOXED_CHAR = {"java.lang.character"}
BOXED = BOXED_INT | BOXED_REAL | BOXED_BOOL | BOXED_CHAR
STRING = {"java.lang.string", "string", "str", "charsequence", "java.lang.charsequence"}
OBJECT = {"object", "java.lang.object", "any", "value", "jvalue"}


class UnsupportedConcreteValue(ValueError):
    """A concrete training value cannot be represented by this SMT model."""


def norm(t: Any) -> str:
    s = "" if t is None else str(t).strip().replace("/", ".")
    return s[1:-1].lower() if s.startswith("L") and s.endswith(";") else s.lower()


def smt_int(x: Any) -> str:
    x = int(x)
    return str(x) if x >= 0 else f"(- {-x})"


def smt_real(x: Any) -> str:
    x = float(x)
    if not math.isfinite(x):
        # pushgp_smt models Java float/double values with SMT Real. SMT Real
        # has no NaN, +Infinity or -Infinity, so there is no faithful literal
        # we can emit for these training cases. Do not silently replace the
        # value with an arbitrary finite number; mark the case unsupported.
        raise UnsupportedConcreteValue(
            f"SMT Real cannot represent IEEE non-finite value {x!r}"
        )
    text = repr(x)
    if "e" in text.lower():
        f = Fraction(Decimal(text))
        n = smt_int(f.numerator)
        return n if f.denominator == 1 else f"(/ {n} {f.denominator})"
    if text.startswith("-"):
        return f"(- {text[1:]})"
    return text if "." in text else text + ".0"


def smt_str(x: Any) -> str:
    chunks, current = [], []

    def flush() -> None:
        if current:
            chunks.append('"' + "".join(current).replace('"', '""') + '"')
            current.clear()

    for ch in str(x):
        code = ord(ch)
        # Keep generated SMT text ASCII-safe.  This avoids Windows
        # console/code-page problems (for example U+0081 cannot be
        # encoded by cp1252) and is valid SMT-LIB string construction.
        if code < 0x20 or code > 0x7E:
            flush()
            chunks.append(f"(str.from_code {code})")
        else:
            current.append(ch)
    flush()
    if not chunks:
        return '""'
    return chunks[0] if len(chunks) == 1 else "(str.++ " + " ".join(chunks) + ")"


def is_reference_type(type_name: Any) -> bool:
    t = norm(type_name)
    if not t or t in INT | REAL | BOOL | CHAR | VOID | ERROR | BOXED | STRING | OBJECT | {"null", "none"}:
        return False
    if t in {"reference", "ref"} or t.startswith("[") or t.endswith("[]"):
        return True
    if any(k in t for k in ("list", "map", "set", "collection", "iterator")):
        return True
    # pushgp_smt treats other declared Java classes as heap references.
    return True


def ref_value(x: Any) -> int | None:
    if not isinstance(x, dict):
        return None
    if str(x.get("kind", "")).lower() not in {"reference", "ref", "object-reference"}:
        return None
    for key in ("id", "ref_id", "refId"):
        if key in x:
            return int(x[key])
    return None


def jvalue(x: Any, type_hint: Any = None) -> str:
    ref = ref_value(x)
    if ref is not None:
        return f"(JRef {smt_int(ref)})"

    t = norm(type_hint)
    if x is None:
        return "JNull"
    if t in INT or t in BOXED_INT:
        return f"(JInt {smt_int(x)})"
    if t in REAL or t in BOXED_REAL:
        return f"(JReal {smt_real(x)})"
    if t in BOOL or t in BOXED_BOOL:
        if isinstance(x, str):
            value = x.strip().lower() in {"true", "1", "yes"}
        else:
            value = bool(x)
        return f"(JBool {'true' if value else 'false'})"
    if t in CHAR or t in BOXED_CHAR:
        return f"(JString {smt_str(str(x)[:1])})"
    if is_reference_type(type_hint) and isinstance(x, int):
        return f"(JRef {smt_int(x)})"
    if isinstance(x, bool):
        return f"(JBool {'true' if x else 'false'})"
    if isinstance(x, int):
        return f"(JInt {smt_int(x)})"
    if isinstance(x, float):
        return f"(JReal {smt_real(x)})"
    if isinstance(x, str):
        return f"(JString {smt_str(x)})"
    raise ValueError(f"Cannot encode as JValue: {x!r}")


def argument(x: Any, type_name: Any) -> str:
    t = norm(type_name)
    if t in INT:
        return smt_int(x)
    if t in REAL:
        return smt_real(x)
    if t in BOOL:
        return "true" if bool(x) else "false"
    if t in CHAR:
        return smt_str(str(x)[:1])
    return jvalue(x, type_name)


def unpack_object(raw: Any, default_type: str) -> tuple[str, Any]:
    if isinstance(raw, dict) and "type" in raw and "data" in raw:
        return str(raw.get("type") or default_type), raw.get("data")
    if isinstance(raw, list) or isinstance(raw, tuple):
        return "list", list(raw)
    if isinstance(raw, set):
        return "set", raw
    if isinstance(raw, dict):
        return "map", raw
    return default_type, raw


def kind(type_name: str, data: Any) -> str:
    t = norm(type_name)
    if "map" in t or isinstance(data, dict):
        return "map"
    if "set" in t or isinstance(data, set):
        return "set"
    if any(k in t for k in ("list", "collection", "arraylist", "deque", "queue", "stack")) or isinstance(data, (list, tuple)):
        return "list"
    return "object"


def add_object(heap: str, ref: int, type_name: str, data: Any) -> str:
    """Encode one concrete heap object using the current pushgp_smt Heap schema.

    Heap now contains ``heap-object-value`` immediately after ``heap-kind``.
    Collection objects preserve that array unchanged; ordinary object/boxed-value
    receivers store their concrete payload in it.
    """
    r = smt_int(ref)
    k = kind(type_name, data)
    object_values = f"(heap-object-value {heap})"

    if k == "list":
        values = list(data or [])
        arr = "((as const (Array Int JValue)) JNull)"
        for i, v in enumerate(values):
            arr = f"(store {arr} {i} {jvalue(v)})"
        return (
            f"(mk-heap "
            f"(store (heap-kind {heap}) {r} K_LIST) "
            f"{object_values} "
            f"(store (heap-list-size {heap}) {r} {len(values)}) "
            f"(store (heap-list-data {heap}) {r} {arr}) "
            f"(heap-map-size {heap}) (heap-map-present {heap}) "
            f"(heap-map-data {heap}) (heap-set-size {heap}) "
            f"(heap-set-present {heap}))"
        )

    if k == "map":
        values = dict(data or {})
        present = "((as const (Array JValue Bool)) false)"
        arr = "((as const (Array JValue JValue)) JNull)"
        for key, value in values.items():
            key_smt = jvalue(key)
            present = f"(store {present} {key_smt} true)"
            arr = f"(store {arr} {key_smt} {jvalue(value)})"
        return (
            f"(mk-heap "
            f"(store (heap-kind {heap}) {r} K_MAP) "
            f"{object_values} "
            f"(heap-list-size {heap}) (heap-list-data {heap}) "
            f"(store (heap-map-size {heap}) {r} {len(values)}) "
            f"(store (heap-map-present {heap}) {r} {present}) "
            f"(store (heap-map-data {heap}) {r} {arr}) "
            f"(heap-set-size {heap}) (heap-set-present {heap}))"
        )

    if k == "set":
        values = list(data or [])
        present = "((as const (Array JValue Bool)) false)"
        for value in values:
            present = f"(store {present} {jvalue(value)} true)"
        return (
            f"(mk-heap "
            f"(store (heap-kind {heap}) {r} K_SET) "
            f"{object_values} "
            f"(heap-list-size {heap}) (heap-list-data {heap}) "
            f"(heap-map-size {heap}) (heap-map-present {heap}) "
            f"(heap-map-data {heap}) "
            f"(store (heap-set-size {heap}) {r} {len(values)}) "
            f"(store (heap-set-present {heap}) {r} {present}))"
        )

    payload = jvalue(data, type_name)
    return (
        f"(mk-heap "
        f"(store (heap-kind {heap}) {r} K_OBJECT) "
        f"(store (heap-object-value {heap}) {r} {payload}) "
        f"(heap-list-size {heap}) (heap-list-data {heap}) "
        f"(heap-map-size {heap}) (heap-map-present {heap}) "
        f"(heap-map-data {heap}) (heap-set-size {heap}) "
        f"(heap-set-present {heap}))"
    )


def _receiver_type_hints(example: Any, methods: dict[str, dict]) -> dict[int, str]:
    """Return authoritative receiver encoding hints from the SMT manifest.

    The trace's ``data_structure_type`` is a coarse/legacy default and can be
    wrong for scalar wrapper receivers.  The generated SMT stub, however, was
    compiled from exact method metadata.  Use the same owner/receiverKind when
    reconstructing the concrete pre-heap so tester and stub share one ABI.
    """
    hints: dict[int, str] = {}
    receiver_refs = list(getattr(example, "receiver_refs", None) or [])

    for i, method_name in enumerate(list(example.sequence or [])):
        info = methods.get(method_name)
        if not info or info.get("isStatic", False):
            continue

        ref = int(receiver_refs[i] if i < len(receiver_refs) else 0)
        owner = str(info.get("owner") or info.get("declaringClass") or "").strip()
        receiver_kind = str(info.get("receiverKind") or "generic").strip().lower()
        receiver_value_type = str(info.get("receiverValueType") or "").strip()

        # Prefer the exact payload type exported by pushgp_smt. This is the same
        # metadata used to generate the RECEIVER.VALUE selector/precondition.
        # Fall back to the declaring class for older manifests.
        owner_norm = norm(owner)
        if receiver_value_type:
            hint = receiver_value_type
        elif owner_norm in BOXED | STRING:
            hint = owner
        elif receiver_kind in {"list", "map", "set"}:
            hint = receiver_kind
        elif receiver_kind == "object":
            hint = owner or "object"
        else:
            hint = owner or receiver_kind or "object"

        previous = hints.get(ref)
        if previous is None:
            hints[ref] = hint
        elif kind(previous, None) != kind(hint, None):
            raise ValueError(
                f"Receiver {ref} has incompatible manifest kinds: {previous!r} vs {hint!r}"
            )

    return hints


def initial_heap(example: Any, methods: dict[str, dict]) -> tuple[str, int]:
    state = dict(example.initial_state or {})
    if not state:
        state = {0: []}
    default_type = str(example.data_structure_type or "object")
    receiver_hints = _receiver_type_hints(example, methods)
    lines = ["(define-fun h_init_0 () Heap empty-heap)"]
    heap = "h_init_0"
    for n, (raw_ref, raw) in enumerate(state.items(), 1):
        ref = int(raw_ref)
        type_name, data = unpack_object(raw, default_type)

        # If this heap object is used as a receiver, encode it with the same
        # receiver metadata that the generated stub used for its precondition.
        # Explicit manifest information is more authoritative than the legacy
        # trace-level data_structure_type default.
        if ref in receiver_hints:
            type_name = receiver_hints[ref]

        name = f"h_init_{n}"
        lines.append(f"(define-fun {name} () Heap {add_object(heap, ref, type_name, data)})")
        heap = name
    lines.append(f"(define-fun h0 () Heap {heap})")
    return "\n".join(lines), max((int(r) for r in state), default=-1) + 1


def collection_arg(x: Any, type_name: Any) -> tuple[str, Any] | None:
    if x is None or ref_value(x) is not None:
        return None
    t = norm(type_name)
    if "map" in t or isinstance(x, dict):
        return "map", x
    if "set" in t or isinstance(x, set):
        return "set", x
    if any(k in t for k in ("list", "collection", "arraylist", "deque", "queue", "stack")) or isinstance(x, (list, tuple)):
        return "list", list(x)
    return None


def calls(example: Any, methods: dict[str, dict], next_ref: int) -> str:
    out = []
    heap = "h0"

    for i, method_name in enumerate(example.sequence):
        if method_name not in methods:
            raise KeyError(f"Method {method_name!r} is not present in the SMT manifest")

        info = methods[method_name]
        args = example.input_args[i]
        types = info.get("argumentTypes", [])

        # Collection/object arguments that exist as concrete Python collections
        # need their own heap objects. Allocate them BEFORE constructing the call
        # so the method receives the heap that actually contains those refs.
        encoded_args = []
        for j, x in enumerate(args):
            trace_types = example.type_inputs[i] if i < len(example.type_inputs) else []
            t = types[j] if j < len(types) else (trace_types[j] if j < len(trace_types) else "java.lang.Object")
            c = collection_arg(x, t)

            if c:
                arg_heap = f"h_arg_{i}_{j}"
                out.append(
                    f"(define-fun {arg_heap} () Heap "
                    f"{add_object(heap, next_ref, c[0], c[1])})"
                )
                heap = arg_heap
                encoded_args.append(f"(JRef {smt_int(next_ref)})")
                next_ref += 1
            else:
                encoded_args.append(argument(x, t))

        params = [heap]
        if not info.get("isStatic", False):
            receiver = example.receiver_refs[i] if i < len(example.receiver_refs) else 0
            params.append(smt_int(receiver))
        params.extend(encoded_args)

        out.append(
            f"(define-fun r{i} () StubResult "
            f"({info['smtFunction']} {' '.join(params)}))"
        )
        heap = f"(result-heap r{i})"

    return "\n".join(out)


def expected_error(value: Any, output_type: Any) -> bool:
    if norm(output_type) in ERROR or value == "error":
        return True
    if isinstance(value, dict):
        k = str(value.get("kind", value.get("type", ""))).lower()
        return k in ERROR or "exceptionType" in value or "exception" in value
    return False


def expected_condition(result: str, value: Any, trace_type: Any, declared_type: Any) -> str:
    if expected_error(value, trace_type):
        return f"(= (result-outcome {result}) OUT_THROWN)"
    if norm(declared_type) in VOID or norm(trace_type) in VOID:
        return f"(and (= (result-outcome {result}) OUT_NORMAL) (= (result-exception {result}) EX_NONE))"
    return f"(and (= (result-outcome {result}) OUT_NORMAL) (= (result-exception {result}) EX_NONE) (= (result-value {result}) {jvalue(value, declared_type)}))"


def run_z3(z3: str, text: str) -> str:
    p = subprocess.run(
        [z3, "-in", "-smt2"],
        input=text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        timeout=60,
    )
    if p.returncode or "(error" in p.stdout:
        Path("failed_query.smt2").write_text(text, encoding="utf-8")
        raise RuntimeError("Z3 failed; query saved to failed_query.smt2\n" + p.stdout + p.stderr)
    return p.stdout


def result_words(text: str) -> list[str]:
    return [x.strip() for x in text.splitlines() if x.strip() in {"sat", "unsat", "unknown"}]


def actual(z3: str, base: str, heap: str, call_text: str, i: int, condition: str) -> str:
    r = f"r{i}"
    q = "\n".join([
        base, heap, call_text,
        f"(assert (not {condition}))",
        "(check-sat)",
        f"(get-value ((result-outcome {r}) (result-value {r}) (result-exception {r})))",
    ])
    return run_z3(z3, q).replace("sat\n", "", 1).strip()


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare any generated PushGP SMT stubs with recorded training outputs")
    ap.add_argument("training_data")
    ap.add_argument("--smt", default="pushgp_model.smt2")
    ap.add_argument("--manifest", default="pushgp_model_manifest.json")
    ap.add_argument("--z3", default="z3")
    ap.add_argument("--max-samples", type=int, default=1_000_000)
    a = ap.parse_args()

    examples = loadtrainingdata(a.training_data, max_samples_per_file=a.max_samples)
    base = re.sub(r"(?m)^\s*\(check-sat\)\s*$", "", Path(a.smt).read_text(encoding="utf-8"))
    manifest = json.loads(Path(a.manifest).read_text(encoding="utf-8"))
    methods = {m["method"]: m for m in manifest["methods"]}

    # The shared SMT prelude contains quantified helper axioms for operations
    # such as list-index-of. Z3 is allowed to answer `unknown` to a bare
    # satisfiability query containing those quantifiers. That does NOT mean the
    # generated module is invalid, so only a definite `unsat` is fatal here.
    base_statuses = result_words(run_z3(a.z3, base + "\n(check-sat)\n"))
    if not base_statuses:
        raise RuntimeError("Z3 produced no satisfiability result for the SMT module")
    if base_statuses[0] == "unsat":
        raise RuntimeError("The generated SMT module itself is UNSAT")
    if base_statuses[0] == "unknown":
        print("Z3 base check: unknown (continuing; quantified helper axioms can cause this)")
    else:
        print("Z3 base check: sat")

    same = different = unknown = total = 0
    skipped_examples = 0
    skipped_calls = 0
    diffs = []
    skipped = []
    per_method = {}

    for eidx, ex in enumerate(examples):
        try:
            heap, next_ref = initial_heap(ex, methods)
            call_text = calls(ex, methods, next_ref)
        except UnsupportedConcreteValue as exc:
            # If a non-finite float occurs in the initial heap or in an input
            # argument, that concrete execution cannot be replayed faithfully:
            # pushgp_smt deliberately uses SMT Real, which has no IEEE
            # NaN/+Inf/-Inf. Since later calls depend on the previous heap, skip
            # this whole sequence instead of inventing an unsound replacement.
            skipped_examples += 1
            skipped_calls += len(ex.sequence)
            skipped.append({
                "example": eidx,
                "reason": str(exc),
                "sequence": list(ex.sequence),
                "input_args": ex.input_args,
                "expected_outputs": ex.expected_outputs,
            })
            continue

        # For every call ask whether a DIFFERENT result is possible.
        #   unsat   -> no disagreement is possible -> SAME
        #   sat     -> disagreement is possible    -> DIFFERENT
        #   unknown -> solver could not decide
        # No per-example bare check-sat is needed; it often returns `unknown`
        # solely because the module contains quantified helper axioms.
        q = [base, heap, call_text]
        testable_calls = []
        expected_conditions = {}
        for i, method in enumerate(ex.sequence):
            info = methods[method]
            try:
                cond = expected_condition(
                    f"r{i}",
                    ex.expected_outputs[i],
                    ex.type_outputs[i],
                    info["returnType"],
                )
            except UnsupportedConcreteValue as exc:
                # A non-finite *expected output* does not prevent execution of
                # the sequence, but that one result cannot be compared to an
                # SMT Real. Skip only this comparison.
                skipped_calls += 1
                skipped.append({
                    "example": eidx,
                    "call": i,
                    "method": method,
                    "args": ex.input_args[i],
                    "expected": ex.expected_outputs[i],
                    "reason": str(exc),
                })
                continue

            expected_conditions[i] = cond
            testable_calls.append(i)
            q.append(f"(push 1)\n(assert (not {cond}))\n(check-sat)\n(pop 1)")

        if not testable_calls:
            continue

        status = result_words(run_z3(a.z3, "\n".join(q)))
        if len(status) != len(testable_calls):
            raise RuntimeError(
                f"Example {eidx}: expected {len(testable_calls)} Z3 results, "
                f"got {len(status)}: {status!r}"
            )

        for i, s in zip(testable_calls, status):
            method = ex.sequence[i]
            m = per_method.setdefault(method, {"total": 0, "same": 0, "different": 0, "unknown": 0})
            m["total"] += 1
            total += 1
            if s == "unsat":
                same += 1; m["same"] += 1
            elif s == "unknown":
                unknown += 1; m["unknown"] += 1
            else:
                different += 1; m["different"] += 1
                diffs.append({
                    "example": eidx,
                    "call": i,
                    "method": method,
                    "args": ex.input_args[i],
                    "expected": ex.expected_outputs[i],
                    "type": ex.type_outputs[i],
                    "receiver_ref": ex.receiver_refs[i] if i < len(ex.receiver_refs) else 0,
                    "smt_result": actual(
                        a.z3, base, heap, call_text, i,
                        expected_conditions[i],
                    ),
                })

        if (eidx + 1) % 50 == 0 or eidx + 1 == len(examples):
            print(f"Processed {eidx + 1}/{len(examples)}", end="\r")

    print("\n\n=== RESULT ===")
    print(f"Examples : {len(examples)}")
    print(f"Calls    : {total}")
    print(f"Same     : {same}")
    print(f"Different: {different}")
    print(f"Unknown  : {unknown}")
    print(f"Skipped  : {skipped_calls} calls in {skipped_examples} fully skipped examples")
    print(f"Accuracy : {(same / total if total else 0):.2%}  (over representable/tested calls only)")

    print("\n=== PER METHOD ===")
    for method, m in sorted(per_method.items()):
        acc = m["same"] / m["total"] if m["total"] else 0
        print(f"{method:30} {m['same']:5}/{m['total']:<5} {acc:7.2%}  diff={m['different']} unknown={m['unknown']}")

    #if diffs:
    #    print("\n=== DIFFERENT CASES ===")
    #    for d in diffs:
    #        print(f"\nExample {d['example']}, call {d['call']}: {d['method']}")
    #        print(f"  args:     {d['args']!r}")
    #        print(f"  expected: {d['expected']!r} ({d['type']})")
    #        print(f"  SMT:      {d['smt_result']}")

    Path("smt_differences.json").write_text(
        json.dumps(diffs, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    Path("smt_skipped.json").write_text(
        json.dumps(skipped, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    print("\nSaved mismatches to smt_differences.json")
    if skipped:
        print("Saved unsupported/skipped cases to smt_skipped.json")
        print("Note: SMT Real cannot faithfully encode Java NaN or +/-Infinity.")
    return 1 if different else 0


if __name__ == "__main__":
    raise SystemExit(main())
