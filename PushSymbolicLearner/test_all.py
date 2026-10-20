from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path


def find_runner(search_dir: Path, explicit: str | None) -> Path:
    """Find the Python file containing the existing main() test runner."""
    if explicit:
        path = Path(explicit).resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Runner script not found: {path}")
        return path

    candidates = []
    for path in search_dir.glob("*.py"):
        if path.name == Path(__file__).name:
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if "def main()" in source and "_build_parser()" in source:
            candidates.append(path.resolve())

    if len(candidates) != 1:
        names = "\n".join(f"  {p}" for p in candidates) or "  (none found)"
        raise RuntimeError(
            "Could not uniquely identify the existing test runner.\n"
            f"Candidates:\n{names}\n"
            "Specify it explicitly with --runner path/to/your_script.py"
        )
    return candidates[0]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run SMT-vs-JDK tests for all genome artifacts."
    )
    parser.add_argument(
        "--genomes",
        type=Path,
        default=Path("genomesNewer"),
        help="Directory containing genome artifacts (default: genomesNewer)",
    )
    parser.add_argument(
        "--training",
        type=Path,
        default=Path(
            "../Training-Data-Generation/"
            "symbolic-regression-data/training"
        ),
        help="Root of the training-data directory",
    )
    parser.add_argument(
        "--runner",
        help="Path to the existing Python test script; auto-detected by default",
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Python executable used to run the test script",
    )
    parser.add_argument(
        "--logs",
        type=Path,
        default=Path("./evaluation/test_all_logs"),
        help="Directory for individual run logs",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("test_all_summary.csv"),
        help="Output CSV summary",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        help="Optional maximum training samples per file",
    )
    parser.add_argument(
        "--java",
        help="Optional Java executable/path passed to the test runner",
    )
    parser.add_argument(
        "--javac",
        help="Optional javac executable/path passed to the test runner",
    )
    parser.add_argument(
        "--classpath",
        help="Optional Java classpath passed to the test runner",
    )
    parser.add_argument(
        "--z3",
        help="Optional Z3 executable/path passed to the test runner",
    )
    parser.add_argument(
        "--synthesize",
        action="store_true",
        help="Enable synthesized round-trip tests",
    )
    parser.add_argument(
        "--extra",
        nargs=argparse.REMAINDER,
        default=[],
        help="Additional arguments passed to the existing test runner",
    )
    a = parser.parse_args()

    genomes = a.genomes.resolve()
    training = a.training.resolve()
    logs = a.logs.resolve()
    summary = a.summary.resolve()

    if not genomes.is_dir():
        parser.error(f"Genome directory does not exist: {genomes}")
    if not training.is_dir():
        parser.error(f"Training directory does not exist: {training}")

    runner = find_runner(genomes.parent, a.runner)
    logs.mkdir(parents=True, exist_ok=True)
    summary.parent.mkdir(parents=True, exist_ok=True)

    # Index training files by their exact filename. Searching recursively
    # supports training files distributed among multiple subdirectories.
    training_index: dict[str, list[Path]] = {}
    for path in training.rglob("*.json"):
        training_index.setdefault(path.name, []).append(path.resolve())

    # Only use SMT files with the expected naming convention.
    smt_files = sorted(genomes.glob("*.json_genome.smt2"))

    rows: list[dict[str, str]] = []
    if not smt_files:
        print(f"No *.json_genome.smt2 files found in {genomes}")
        return 1

    print(f"Genome directory : {genomes}")
    print(f"Training directory: {training}")
    print(f"Test runner       : {runner}")
    print(f"SMT files found   : {len(smt_files)}")
    print()

    for index, smt in enumerate(smt_files, start=1):
        # Strip only the final ".smt2" to recover the shared artifact stem.
        stem = smt.name.removesuffix(".smt2")
        manifest = genomes / f"{stem.replace('.json_genome', '.json_genome_manifest')}.json"
        genome_json = genomes / f"{stem}.json"

        # For example:
        # foo.json_genome.smt2 -> foo.json
        training_name = stem.removesuffix("_genome")
        training_name = training_name.removesuffix(".json")
        training_name += ".json"

        matches = training_index.get(training_name, [])

        method = smt.name.removesuffix(".json_genome.smt2")
        print(f"[{index}/{len(smt_files)}] {method}")

        missing = []
        if not manifest.is_file():
            missing.append(f"manifest missing: {manifest.name}")
        if not genome_json.is_file():
            missing.append(f"genome JSON missing: {genome_json.name}")
        if not matches:
            missing.append(f"training file not found: {training_name}")
        elif len(matches) > 1:
            # Ambiguous matches are skipped instead of silently testing
            # the wrong training data.
            missing.append(
                "multiple training files match:\n"
                + "\n".join(f"    {p}" for p in matches)
            )

        log_path = logs / f"{method}.log"

        row = {
            "method": method,
            "status": "",
            "return_code": "",
            "training_file": str(matches[0]) if len(matches) == 1 else "",
            "smt_file": str(smt),
            "manifest_file": str(manifest),
            "genome_file": str(genome_json),
            "log_file": str(log_path),
            "notes": "",
        }

        if missing:
            row["status"] = "SKIPPED"
            row["notes"] = " | ".join(missing)
            print(f"  SKIPPED: {row['notes']}")
            rows.append(row)
            continue

        command = [
            a.python,
            str(runner),
            str(matches[0]),
            "--smt", str(smt.resolve()),
            "--manifest", str(manifest.resolve()),
        ]

        if a.max_samples is not None:
            command.extend(["--max-samples", str(a.max_samples)])
        if a.java:
            command.extend(["--java", a.java])
        if a.javac:
            command.extend(["--javac", a.javac])
        if a.classpath:
            command.extend(["--classpath", a.classpath])
        if a.z3:
            command.extend(["--z3", a.z3])
        if a.synthesize:
            command.append("--synthesize")
        if a.extra:
            command.extend(a.extra)

        try:
            # Keep each method's complete output for later inspection.
            with log_path.open("w", encoding="utf-8") as log:
                log.write("COMMAND: " + repr(command) + "\n\n")
                log.flush()
                result = subprocess.run(
                    command,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    text=True,
                    check=False,
                )

            row["return_code"] = str(result.returncode)
            row["status"] = "PASS" if result.returncode == 0 else "FAIL"
            print(f"  {row['status']} (exit code {result.returncode})")
            print(f"  Log: {log_path}")

        except OSError as exc:
            row["status"] = "ERROR"
            row["notes"] = str(exc)
            print(f"  ERROR: {exc}")

        rows.append(row)

    fieldnames = [
        "method",
        "status",
        "return_code",
        "training_file",
        "smt_file",
        "manifest_file",
        "genome_file",
        "log_file",
        "notes",
    ]

    with summary.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    counts = {
        status: sum(r["status"] == status for r in rows)
        for status in ("PASS", "FAIL", "SKIPPED", "ERROR")
    }

    print("\n========== BATCH SUMMARY ==========")
    print(f"Total   : {len(rows)}")
    for status, count in counts.items():
        print(f"{status:8}: {count}")
    print(f"CSV     : {summary}")
    print(f"Logs    : {logs}")

    return 1 if counts["FAIL"] or counts["ERROR"] or counts["SKIPPED"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
