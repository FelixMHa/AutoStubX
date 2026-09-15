#!/usr/bin/env python3

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any


def _load_engine(path: str | Path) -> ModuleType:
    """Load the synthesis engine without importing the training stack.

    The tester imports ``loadtrainingdata`` from ``rungp`` at module import time,
    but the standalone inverse tool never uses training-data loading.  Importing
    the real ``rungp`` unnecessarily pulls in ``pushgp_smt`` and native modules
    such as ``ctypes``.  On locked-down Windows installations that can fail before
    any SMT synthesis is reached.

    Install a temporary minimal ``rungp`` shim while executing the engine module.
    If engine ``main()`` were called, the shim deliberately raises; the inverse
    API only uses the engine's SMT/JDK helper functions.
    """
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Synthesis engine script not found: {path}")

    inserted_rungp_shim = False
    if "rungp" not in sys.modules:
        rungp_shim = ModuleType("rungp")

        def _unused_loadtrainingdata(*_args: Any, **_kwargs: Any) -> Any:
            raise RuntimeError(
                "loadtrainingdata is unavailable in standalone inverse mode; "
                "run the full tester when training-data loading is required"
            )

        rungp_shim.loadtrainingdata = _unused_loadtrainingdata  # type: ignore[attr-defined]
        sys.modules["rungp"] = rungp_shim
        inserted_rungp_shim = True

    try:
        spec = importlib.util.spec_from_file_location("pushgp_inverse_engine", path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Could not import synthesis engine from {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if inserted_rungp_shim:
            sys.modules.pop("rungp", None)


def _default_engine_script() -> Path:
    here = Path(__file__).resolve().parent
    candidates = [
        here / "test_smt_jdk_synthesis.py",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    # Return the preferred name so the eventual error is clear.
    return candidates[0]


def _load_manifest(path: str | Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    methods = {str(m["method"]): m for m in manifest.get("methods", [])}
    if not methods:
        raise ValueError(f"Manifest contains no methods: {path}")
    return manifest, methods


def _resolve_method(methods: dict[str, dict[str, Any]], query: str) -> str:
    q = query.strip()
    if q in methods:
        return q

    q_lower = q.lower()
    exact_ci = [name for name in methods if name.lower() == q_lower]
    if len(exact_ci) == 1:
        return exact_ci[0]

    # Allow `contains` for `contains#obj`, `size` for `size#0`, etc.
    short = [name for name in methods if name.split("#", 1)[0].lower() == q_lower]
    if len(short) == 1:
        return short[0]

    # Also accept the generated SMT function name.
    by_smt = [
        name for name, info in methods.items()
        if str(info.get("smtFunction", "")).lower() == q_lower
    ]
    if len(by_smt) == 1:
        return by_smt[0]

    matches = sorted(set(exact_ci + short + by_smt))
    if matches:
        raise ValueError(f"Ambiguous method {query!r}; matches: {', '.join(matches)}")
    raise ValueError(
        f"Unknown method {query!r}. Available methods: {', '.join(sorted(methods))}"
    )


def _parse_json_value(text: str, label: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{label} must be a JSON value. Examples: true, false, 3, null, '\"text\"', [1,2]"
        ) from exc


def _validate_output(engine: ModuleType, info: dict[str, Any], value: Any) -> None:
    rt = engine.norm(info.get("returnType"))
    if rt in engine.BOOL and type(value) is not bool:
        raise ValueError(f"{info['method']} returns boolean; requested output must be true or false")
    if rt in engine.INT and (type(value) is bool or not isinstance(value, int)):
        raise ValueError(f"{info['method']} returns int; requested output must be an integer")
    if rt in engine.VOID and value is not None:
        raise ValueError(f"{info['method']} returns void; requested output must be null")


def _one_call_example(
    info: dict[str, Any],
    method_name: str,
    output_value: Any,
    mode: str,
    receiver_state: list[Any] | None,
    fixed_argument: Any,
) -> Any:
    declared = list(info.get("argumentTypes", []))
    is_static = bool(info.get("isStatic", False))
    owner = str(info.get("owner") or info.get("declaringClass") or "java.lang.Object")

    if mode in {"args", "joint"} and len(declared) != 1:
        raise ValueError(
            f"Current symbolic argument synthesis supports exactly one argument; "
            f"{method_name} has {len(declared)}"
        )

    if mode == "state" and declared and fixed_argument is _MISSING:
        raise ValueError(
            f"state mode keeps the method argument concrete; pass fixed_argument/--argument for {method_name}"
        )

    if mode == "args" and not is_static and receiver_state is None:
        raise ValueError(
            "args mode keeps receiver state concrete; pass receiver_state/--state. "
            "Use mode='joint' if you want the receiver state synthesized too."
        )

    if not declared:
        args: list[Any] = []
    elif mode == "state":
        args = [fixed_argument]
    else:
        # Placeholder only. The synthesis engine replaces this with synth_arg.
        args = [None]

    initial_state: dict[int, Any] = {}
    receiver_refs: list[int] = []
    if not is_static:
        receiver = 0
        receiver_refs = [receiver]
        if str(info.get("receiverKind") or "").lower() == "set":
            state = list(receiver_state or [])
        else:
            state = receiver_state if receiver_state is not None else []
        initial_state = {receiver: {"type": owner, "data": state}}

    return SimpleNamespace(
        initial_state=initial_state,
        data_structure_type=owner,
        sequence=[method_name],
        input_args=[args],
        type_inputs=[declared],
        expected_outputs=[output_value],
        type_outputs=[str(info.get("returnType") or "void")],
        receiver_refs=receiver_refs,
    )


_MISSING = object()


def find_input_for_output(
    output_value: Any,
    *,
    method: str,
    smt_path: str | Path,
    manifest_path: str | Path,
    z3_path: str = "z3",
    engine_script: str | Path | None = None,
    mode: str = "auto",
    receiver_state: list[Any] | None = None,
    fixed_argument: Any = _MISSING,
    set_slots: int = 4,
    max_results: int = 3,
    verify: bool = True,
    java: str = "java",
    javac: str = "javac",
    classpath: str = ".",
    save_path: str | Path | None = "inverse_input_solutions.json",
) -> list[dict[str, Any]]:
    """Solve `method(...) == output_value` and return concrete witnesses.

    Modes:
      * ``joint``: synthesize receiver HashSet state and one method argument.
      * ``args``: keep ``receiver_state`` concrete and synthesize the argument.
      * ``state``: keep ``fixed_argument`` concrete (if the method has an argument)
        and synthesize receiver state.
      * ``auto``: ``joint`` for one-argument methods, otherwise ``state``.

    Each returned dictionary contains at least:
      ``input`` / ``argument``      - synthesized method argument (when applicable)
      ``receiver_state`` / ``initial_set`` - required receiver state (when synthesized)
      ``wanted_output``             - the output constraint supplied by the caller

    With ``verify=True`` the witness is also executed on the real JDK and re-proved
    against the SMT model, adding ``jdk``, ``pass``, and proof fields.
    """
    if max_results < 1:
        return []
    if set_slots < 0:
        raise ValueError("set_slots must be >= 0")

    engine_path = Path(engine_script) if engine_script is not None else _default_engine_script()
    engine = _load_engine(engine_path)

    _manifest, methods = _load_manifest(manifest_path)
    method_name = _resolve_method(methods, method)
    info = methods[method_name]
    _validate_output(engine, info, output_value)

    declared = list(info.get("argumentTypes", []))
    if mode == "auto":
        mode = "joint" if len(declared) == 1 else "state"
    mode = mode.lower()
    if mode not in {"args", "state", "joint"}:
        raise ValueError("mode must be one of: auto, args, state, joint")
    if mode == "joint" and not declared:
        mode = "state"

    example = _one_call_example(
        info,
        method_name,
        output_value,
        mode,
        receiver_state,
        fixed_argument,
    )

    base = re.sub(
        r"(?m)^\s*\(check-sat\)\s*$",
        "",
        Path(smt_path).read_text(encoding="utf-8"),
    )

    # Sanity-check the model before doing inverse synthesis.
    base_status = engine.result_words(engine.run_z3(z3_path, base + "\n(check-sat)\n"))
    if not base_status:
        raise RuntimeError("Z3 returned no status for the base SMT model")
    if base_status[0] == "unsat":
        raise RuntimeError("The supplied SMT model is UNSAT before synthesis")

    candidates = engine.synthesize_cases_for_call(
        z3_path,
        base,
        example,
        methods,
        0,
        mode,
        output_value,
        [],             # finite domain is unused by symbolic engine
        max_results,
        "symbolic",
        set_slots,
    )

    if verify and candidates:
        results: list[dict[str, Any]] = []
        with engine.JdkOracle(java, javac, classpath) as oracle:
            for candidate in candidates:
                results.append(
                    engine.retest_synthesized_case(
                        oracle, z3_path, base, example, methods, 0, candidate
                    )
                )
    else:
        results = candidates

    # Friendly aliases: `input` is what callers usually want; `receiver_state`
    # makes the state dependency explicit for stateful methods like HashSet.
    normalized: list[dict[str, Any]] = []
    for result in results:
        item = dict(result)
        item["input"] = item.get("argument")
        if item.get("initial_set") is not None:
            item["receiver_state"] = item.get("initial_set")
        elif receiver_state is not None:
            item["receiver_state"] = receiver_state
        else:
            item["receiver_state"] = None
        normalized.append(item)

    if save_path is not None:
        Path(save_path).write_text(
            json.dumps(normalized, indent=2, ensure_ascii=False, default=str) + "\n",
            encoding="utf-8",
        )

    return normalized


def _print_solutions(solutions: list[dict[str, Any]]) -> None:
    if not solutions:
        print("No satisfying input/state found.")
        return
    for i, solution in enumerate(solutions, 1):
        print(f"\nSolution {i}")
        print(f"  method         : {solution.get('method', '<not verified>')}")
        print(f"  wanted output  : {solution.get('wanted_output')!r}")
        if solution.get("input") is not None or solution.get("mode") in {"args", "joint"}:
            print(f"  input          : {solution.get('input')!r}")
        if solution.get("receiver_state") is not None:
            print(f"  receiver state : {solution.get('receiver_state')!r}")
        if "jdk" in solution:
            jdk = solution.get("jdk") or {}
            print(f"  JDK output     : {jdk.get('value')!r} ({jdk.get('outcome')})")
            print(f"  verified       : {solution.get('pass')}")
            print(f"  SMT recheck    : {solution.get('smt_retest_status')}")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Set a desired method output and ask Z3 for concrete input/state witnesses."
    )
    ap.add_argument("--method", required=True, help="Manifest method, e.g. contains#obj, remove#obj, size#0")
    ap.add_argument("--output", required=True, help="Desired output as JSON: true, false, 3, null, ...")
    ap.add_argument("--smt", required=True, help="Generated SMT model")
    ap.add_argument("--manifest", required=True, help="Generated model manifest")
    ap.add_argument("--z3", default="z3", help="Path to Z3 executable")
    ap.add_argument(
        "--engine-script",
        default=None,
        help="Path to test_smt_jdk_synthesis.py / test_smt_jdk_symbolic_fast.py",
    )
    ap.add_argument(
        "--mode",
        choices=("auto", "args", "state", "joint"),
        default="auto",
        help="auto=joint for one-argument methods, state for no-argument methods",
    )
    ap.add_argument(
        "--state",
        default=None,
        help="Concrete receiver state as JSON list, required by args mode; e.g. '[1,2,\"x\"]'",
    )
    ap.add_argument(
        "--argument",
        default=None,
        help="Concrete argument as JSON, required for state mode on an argument-taking method",
    )
    ap.add_argument("--set-slots", type=int, default=4, help="Maximum synthesized HashSet size")
    ap.add_argument("--count", type=int, default=3, help="Maximum number of satisfying witnesses")
    ap.add_argument("--no-verify", action="store_true", help="Do not execute generated witnesses on the JDK")
    ap.add_argument("--java", default="java")
    ap.add_argument("--javac", default="javac")
    ap.add_argument("--classpath", default=".")
    ap.add_argument("--save", default="inverse_input_solutions.json")
    a = ap.parse_args()

    wanted = _parse_json_value(a.output, "--output")
    state = _parse_json_value(a.state, "--state") if a.state is not None else None
    if state is not None and not isinstance(state, list):
        raise ValueError("--state must be a JSON list for the current HashSet synthesizer")
    fixed_argument = (
        _parse_json_value(a.argument, "--argument")
        if a.argument is not None
        else _MISSING
    )

    solutions = find_input_for_output(
        wanted,
        method=a.method,
        smt_path=a.smt,
        manifest_path=a.manifest,
        z3_path=a.z3,
        engine_script=a.engine_script,
        mode=a.mode,
        receiver_state=state,
        fixed_argument=fixed_argument,
        set_slots=a.set_slots,
        max_results=a.count,
        verify=not a.no_verify,
        java=a.java,
        javac=a.javac,
        classpath=a.classpath,
        save_path=a.save,
    )
    _print_solutions(solutions)
    print(f"\nSaved {len(solutions)} solution(s) to {a.save}")
    return 0 if solutions else 2


if __name__ == "__main__":
    raise SystemExit(main())
