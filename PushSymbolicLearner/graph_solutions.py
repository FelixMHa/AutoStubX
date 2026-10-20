
import re
import csv
from pathlib import Path
from collections import Counter

import matplotlib.pyplot as plt

LOG_DIR = Path(
    r"C:\Users\felix\AutoStubX\PushSymbolicLearner\test_all_logs"
)
OUTPUT_DIR = LOG_DIR.parent / "accuracy_statistics"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Main metric: SMT vs actual JDK
SMT_AGREEMENT = re.compile(
    r"===\s*SMT\s+vs\s+ACTUAL\s+JDK\s*==="
    r"(.*?)(?=\n\s*===|\Z)",
    re.I | re.S,
)

AGREEMENT_VALUE = re.compile(
    r"\bAgreement\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*%",
    re.I,
)

TRAINING_AGREEMENT = re.compile(
    r"===\s*TRAINING\s+TRACE\s+vs\s+ACTUAL\s+JDK\s*==="
    r"(.*?)(?=\n\s*===|\Z)",
    re.I | re.S,
)

def extract_section_accuracy(text, section_pattern):
    section = section_pattern.search(text)
    if not section:
        return None

    matches = list(AGREEMENT_VALUE.finditer(section.group(1)))
    if not matches:
        return None

    return float(matches[-1].group(1))


def classify(accuracy):
    if accuracy is None:
        return "Unknown"
    if accuracy >= 99.999999:
        return "100%"
    if accuracy > 90:
        return ">90% to <100%"
    if accuracy >= 50:
        return "50% to 90%"
    return "<50%"


def detect_status(text):
    # Detect the explicit batch-runner status if it appears in the log.
    if re.search(r"\bFAIL\s*\(exit code [1-9]\d*\)", text, re.I):
        return "FAIL"
    if re.search(r"\bPASS\b", text, re.I):
        return "PASS"
    return "NOT_RECORDED"


def main():
    if not LOG_DIR.exists():
        raise SystemExit(f"Log directory not found: {LOG_DIR}")

    logs = sorted(LOG_DIR.rglob("*.log"))
    if not logs:
        raise SystemExit(f"No .log files found in: {LOG_DIR}")

    category_order = [
        "100%",
        ">90% to <100%",
        "50% to 90%",
        "<50%",
        "Unknown",
    ]

    counts = Counter()
    rows = []

    for log_path in logs:
        text = log_path.read_text(encoding="utf-8", errors="replace")

        # The main accuracy metric
        smt_accuracy = extract_section_accuracy(text, SMT_AGREEMENT)

        # Diagnostic metric kept separate
        training_accuracy = extract_section_accuracy(
            text, TRAINING_AGREEMENT
        )

        category = classify(smt_accuracy)
        status = detect_status(text)
        counts[category] += 1

        rows.append({
            "log_file": str(log_path),
            "status": status,
            "smt_vs_jdk_agreement_percent": (
                "" if smt_accuracy is None else smt_accuracy
            ),
            "accuracy_category": category,
            "training_trace_vs_jdk_percent": (
                "" if training_accuracy is None else training_accuracy
            ),
        })

    # Export details
    csv_path = OUTPUT_DIR / "accuracy_details.csv"
    with csv_path.open(
        "w", newline="", encoding="utf-8-sig"
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "log_file",
                "status",
                "smt_vs_jdk_agreement_percent",
                "accuracy_category",
                "training_trace_vs_jdk_percent",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    # Plot main SMT vs JDK agreement distribution
    values = [counts[c] for c in category_order]

    plt.figure(figsize=(10, 6))
    bars = plt.bar(category_order, values)
    plt.title(f"SMT vs Actual JDK Agreement ({len(logs)} logs)")
    plt.xlabel("Agreement category")
    plt.ylabel("Number of log files")
    plt.xticks(rotation=15, ha="right")
    plt.bar_label(bars, padding=3)
    plt.tight_layout()

    graph_path = OUTPUT_DIR / "accuracy_statistics.png"
    plt.savefig(graph_path, dpi=160)
    plt.close()

    # Summary report
    summary_path = OUTPUT_DIR / "accuracy_summary.txt"
    with summary_path.open("w", encoding="utf-8") as f:
        f.write(f"Log files scanned: {len(logs)}\n\n")
        f.write("Main metric: SMT vs ACTUAL JDK Agreement\n\n")

        for category in category_order:
            n = counts[category]
            pct = 100 * n / len(logs)
            f.write(f"{category}: {n} ({pct:.1f}%)\n")

        f.write("\nNote: training-trace agreement is diagnostic only.\n")
        f.write("Unknown means no SMT-vs-JDK Agreement line was found.\n")

    print(f"\nScanned {len(logs)} logs")
    print("Metric: SMT vs ACTUAL JDK Agreement\n")

    for category in category_order:
        print(f"{category:18} {counts[category]:5}")

    print(f"\nGraph:   {graph_path}")
    print(f"CSV:     {csv_path}")
    print(f"Summary: {summary_path}")

    if counts["Unknown"]:
        print(
            f"\nWarning: {counts['Unknown']} logs had no recognizable "
            "SMT-vs-JDK Agreement value."
        )


if __name__ == "__main__":
    main()
