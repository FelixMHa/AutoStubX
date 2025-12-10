import subprocess, os, sys



PY = sys.executable 
MAIN_FOLDER = "../../Training-Data-Generation/symbolic-regression-data/training/"
FILES = [
    "public_class_java_util_ArrayList_E_.json",
    "public_class_java_util_Stack_E_.json",
    "public_class_java_util_HashSet_E_.json",
]
RUNS_PER_CLASS = 5
GENOMES_DIR = "genomes"
LOGS_DIR = "logs"

os.makedirs(GENOMES_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)


def start_run(mainfolder: str, filename: str, run_idx: int):
    """Run rungp.py on `filename` and save console output and genome for this run."""
    filepath = os.path.join(mainfolder, filename)
    base = os.path.splitext(filename)[0]
    genome_out = os.path.join(GENOMES_DIR, f"{base}_run{run_idx}.json")
    log_out = os.path.join(LOGS_DIR, f"{base}_run{run_idx}.log")

    if not filename.endswith(".json"):
        return

    print(f"Run {run_idx} for {filename} -> genome: {genome_out}, log: {log_out}")

    cmd = [
    PY, "-u", "rungp.py", filepath,
    "--profile", "ds_smt_minimal",
    "--population", "1000",
    "--generations", "2000",
    "--output", genome_out,
]

    # Run and capture combined stdout+stderr into the log file
    with open(log_out, "w", encoding="utf-8") as logf:
        try:
            subprocess.run(cmd, stdout=logf, stderr=subprocess.STDOUT, check=True)
        except subprocess.CalledProcessError as e:
            # record non-zero exit in the log and print a short message
            logf.write(f"\n\nProcess exited with return code {e.returncode}\n")
            print(f"Run {run_idx} for {filename} failed (see {log_out})")


def main():
    for filename in FILES:
        for run_idx in range(1, RUNS_PER_CLASS + 1):
            start_run(MAIN_FOLDER, filename, run_idx)


if __name__ == "__main__":
    main()
