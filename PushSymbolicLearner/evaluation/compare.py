import json
import os

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def normalize_summary_name(summary_name: str) -> str:
    """
    Convert summary filename with '___best_individual.json'
    into the base name used by single files.
    """
    return summary_name.replace("_best_individual.json", "")

def normalize_single_name(single_name: str) -> str:
    """
    Convert single filename with '__.json_genome.json'
    into the same base name.
    """
    return single_name.replace(".json_genome.json", "")

def compare(summary_json, single_folder):
    comparisons = []
    unmatched = []

    # Build index of single files by normalized base
    single_index = {}
    for fname in os.listdir(single_folder):
        if fname.endswith(".json"):
            base = normalize_single_name(fname)
            single_index[base] = os.path.join(single_folder, fname)

    for entry in summary_json:
        file_name = entry.get("fileName")
        formula = entry.get("formula")
        accuracy_summary = entry.get("correctCount", 0) / max(entry.get("totalEvaluated", 1), 1)
        fitness_summary = entry.get("relativeError", None)
        execution_time_summary = entry.get("generationTime", None)

        base = normalize_summary_name(os.path.basename(file_name))
        single_path = single_index.get(base)

        if not single_path:
            unmatched.append(file_name)
            continue

        single_json = load_json(single_path)

        # Extract method name from summary filename
        method_name = file_name.split("___")[0].split("_")[-1]
        methods = single_json.get("methods", {})
        method_data = methods.get(method_name, {})

        # Fallback: if method not found, use the only method present
        if not method_data and len(methods) == 1:
            method_name = next(iter(methods.keys()))
            method_data = methods[method_name]

        program = method_data.get("program")
        accuracy_single = single_json.get("accuracy")
        fitness_single = single_json.get("fitness")
        execution_time_single = single_json.get("executionTime")

        comparisons.append({
            "fileName": file_name,
            "formula": formula,
            "summary": {
                "accuracy": accuracy_summary,
                "fitness": fitness_summary,
                "executionTime": execution_time_summary
            },
            "single": {
                "accuracy": accuracy_single,
                "fitness": fitness_single,
                "executionTime": execution_time_single,
                "program": program
            }
        })

    return {"comparisons": comparisons, "unmatched": unmatched}




import json
import os

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def normalize_summary_name(summary_name: str) -> str:
    return summary_name.replace("___best_individual.json", "")

def normalize_single_name(single_name: str) -> str:
    return single_name.replace("__.json_genome.json", "")

def compare(summary_json, single_folder):
    comparisons = []
    unmatched = []

    # Build index of single files by normalized base
    single_index = {}
    for fname in os.listdir(single_folder):
        if fname.endswith(".json"):
            base = normalize_single_name(fname)
            single_index[base] = os.path.join(single_folder, fname)

    # Track totals for overall accuracy and time
    summary_correct_total = 0
    summary_eval_total = 0
    summary_time_total = 0.0

    single_acc_values = []
    single_time_total = 0.0

    for entry in summary_json:
        file_name = entry.get("fileName")
        formula = entry.get("formula")
        correct_count = entry.get("correctCount", 0)
        total_eval = entry.get("totalEvaluated", 1)
        accuracy_summary = correct_count / max(total_eval, 1)
        fitness_summary = entry.get("relativeError", None)
        execution_time_summary = entry.get("generationTime", None)

        summary_correct_total += correct_count
        summary_eval_total += total_eval
        if execution_time_summary is not None:
            summary_time_total += execution_time_summary

        base = normalize_summary_name(os.path.basename(file_name))
        single_path = single_index.get(base)

        if not single_path:
            unmatched.append(file_name)
            continue

        single_json = load_json(single_path)

        method_name = file_name.split("___")[0].split("_")[-1]
        methods = single_json.get("methods", {})
        method_data = methods.get(method_name, {})

        if not method_data and len(methods) == 1:
            method_name = next(iter(methods.keys()))
            method_data = methods[method_name]

        program = method_data.get("program")
        accuracy_single = single_json.get("accuracy")
        fitness_single = single_json.get("fitness")
        execution_time_single = single_json.get("executionTime")

        if accuracy_single is not None:
            single_acc_values.append(accuracy_single)
        if execution_time_single is not None:
            single_time_total += execution_time_single

        comparisons.append({
            "fileName": file_name,
            "formula": formula,
            "summary": {
                "accuracy": accuracy_summary,
                "fitness": fitness_summary,
                "executionTime": execution_time_summary
            },
            "single": {
                "accuracy": accuracy_single,
                "fitness": fitness_single,
                "executionTime": execution_time_single,
                "program": program
            }
        })

    overall_summary_accuracy = summary_correct_total / max(summary_eval_total, 1)
    overall_single_accuracy = sum(single_acc_values) / max(len(single_acc_values), 1)

    return {
        "comparisons": comparisons,
        "unmatched": unmatched,
        "overall": {
            "summary_accuracy": overall_summary_accuracy,
            "single_accuracy": overall_single_accuracy,
            "summary_total_time": summary_time_total,
            "single_total_time": single_time_total
        }
    }

import json
import os

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

def normalize_summary_name(summary_name: str) -> str:
    return summary_name.replace("_best_individual.json", "")

def normalize_single_name(single_name: str) -> str:
    return single_name.replace(".json_genome.json", "")

def compare(summary_json, single_folder):
    comparisons = []
    unmatched = []

    # Build index of single files by normalized base
    single_index = {}
    for fname in os.listdir(single_folder):
        if fname.endswith(".json"):
            base = normalize_single_name(fname)
            single_index[base] = os.path.join(single_folder, fname)

    # Track totals for overall accuracy and time
    summary_correct_total = 0
    summary_eval_total = 0
    summary_time_total = 0.0
    summary_over_90 = 0
    single_over_90 = 0
    summary_fully_correct = 0
    single_fully_correct = 0
    unmatched_fully_correct = 0
    unmatched_over_90 = 0

    un_methods_fully_correct = []
    un_methods_over_90 = []
    single_acc_values = []
    single_time_total = 0.0
    methods_compared = []

    for entry in summary_json:
        file_name = entry.get("fileName")
        formula = entry.get("formula")
        correct_count = entry.get("correctCount", 0)
        total_eval = entry.get("totalEvaluated", 1)
        accuracy_summary = correct_count / max(total_eval, 1)
        fitness_summary = entry.get("relativeError", None)
        execution_time_summary = entry.get("generationTime", None)

        summary_correct_total += correct_count
        summary_eval_total += total_eval
        if execution_time_summary is not None:
            summary_time_total += execution_time_summary

        base = normalize_summary_name(os.path.basename(file_name))
        single_path = single_index.get(base)

        if not single_path:
            unmatched.append(file_name)
            if accuracy_summary >= 0.9:
                unmatched_over_90 += 1
                un_methods_over_90.append(file_name)
            
            if accuracy_summary == 1.0:
                unmatched_fully_correct += 1
                un_methods_fully_correct.append(file_name)
            
            continue

        single_json = load_json(single_path)

        method_name = file_name.split("___")[0].split("_")[-1]
        methods = single_json.get("methods", {})
        method_data = methods.get(method_name, {})

        if not method_data and len(methods) == 1:
            method_name = next(iter(methods.keys()))
            method_data = methods[method_name]

        program = method_data.get("program")
        accuracy_single = single_json.get("accuracy")
        fitness_single = single_json.get("fitness")
        execution_time_single = single_json.get("executionTime")

        if accuracy_single is not None:
            single_acc_values.append(accuracy_single)
        if execution_time_single is not None:
            single_time_total += execution_time_single

        if accuracy_summary >= 0.9:
            summary_over_90 += 1
        if accuracy_single is not None and accuracy_single >= 0.9:
            single_over_90 += 1
        if accuracy_summary == 1.0:
            summary_fully_correct += 1
        if accuracy_single is not None and accuracy_single == 1.0:
            single_fully_correct += 1

        comparisons.append({
            "fileName": file_name,
            "methodName": method_name,
            "formula": formula,
            "summary": {
                "accuracy": accuracy_summary,
                "fitness": fitness_summary,
                "executionTime": execution_time_summary
            },
            "single": {
                "accuracy": accuracy_single,
                "fitness": fitness_single,
                "executionTime": execution_time_single,
                "program": program
            }
        })

        methods_compared.append(method_name)

    overall_summary_accuracy = summary_correct_total / max(summary_eval_total, 1)
    overall_single_accuracy = sum(single_acc_values) / max(len(single_acc_values), 1)

    return {
        "comparisons": comparisons,
        "unmatched": unmatched,
        "unmatched_fully_correct_methods": un_methods_fully_correct,
        "unmatched_over_90_methods": un_methods_over_90,
        "overall": {
            "summary_accuracy": overall_summary_accuracy,
            "single_accuracy": overall_single_accuracy,
            "summary_total_time": summary_time_total,
            "single_total_time": single_time_total,
            "summary_over_90": summary_over_90,
            "single_over_90": single_over_90,
            "summary_fully_correct": summary_fully_correct,
            "single_fully_correct": single_fully_correct,
            "methods_compared_count": len(methods_compared),
            "unmatched_count": len(unmatched),
            "unmatched_fully_correct": unmatched_fully_correct,
            "unmatched_over_90": unmatched_over_90
        },
        "methods_compared": methods_compared
    }

if __name__ == "__main__":
    summary_path = "./PushSymbolicLearner/evaluation-merged.json"        # path to your summary JSON list
    single_folder = "./PushSymbolicLearner/LearnedGenomes"  # folder containing individual JSON files
    output_path = "comparison_results.json"

    summary_json = load_json(summary_path)
    results = compare(summary_json, single_folder)
    save_json(output_path, results)

    print(f"Saved {len(results['comparisons'])} comparisons to {output_path}.")
    print("Methods compared:", results["methods_compared"])

