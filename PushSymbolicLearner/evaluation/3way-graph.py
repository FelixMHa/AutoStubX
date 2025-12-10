import re
import matplotlib.pyplot as plt
import numpy as np
import glob
import os

# ------------------------------------------------------
# Find all log files (now supports both .txt and .log)
# ------------------------------------------------------
log_files = sorted(glob.glob("*.log") + glob.glob("runs/*.txt") + glob.glob("runs/*.log"))
print("Found runs:", log_files)

if not log_files:
    raise ValueError("No log files found! Place .log files in current directory or .txt/.log files in runs/ directory")

# Regex to extract values
pattern = re.compile(
    r"Gen (\d+): Fitness=([0-9.]+), Acc=([0-9.]+), Complexity=([0-9.]+)"
)

# ------------------------------------------------------
# Extract Gens, Fitness, Acc, Complexity for each run
# ------------------------------------------------------
all_gens = []
all_fitness = []
all_acc = []
all_complexity = []

for logfile in log_files:
    gens, fitness, acc, complexity = [], [], [], []
    with open(logfile, "r", encoding="utf-8") as f:
        for line in f:
            match = pattern.search(line)
            if match:
                gens.append(int(match.group(1)))
                fitness.append(float(match.group(2)))
                acc.append(float(match.group(3)))
                complexity.append(float(match.group(4)))
    
    if len(gens) > 0:
        all_gens.append(gens)
        all_fitness.append(fitness)
        all_acc.append(acc)
        all_complexity.append(complexity)
        print(f"  {os.path.basename(logfile)}: {len(gens)} generations")

if not all_gens:
    raise ValueError("No valid data extracted from log files!")

# ------------------------------------------------------
# Find common generation points across all runs
# ------------------------------------------------------
# Get all unique generation numbers
unique_gens = sorted(set(gen for run_gens in all_gens for gen in run_gens))
print(f"\nGenerations found: {len(unique_gens)} points from Gen {min(unique_gens)} to Gen {max(unique_gens)}")

# ------------------------------------------------------
# Interpolate/align data to common generation points
# ------------------------------------------------------
def align_to_gens(gens, values, target_gens):
    """Interpolate values to match target generation points"""
    aligned = []
    for tgen in target_gens:
        if tgen in gens:
            idx = gens.index(tgen)
            aligned.append(values[idx])
        else:
            # Find nearest generations for interpolation
            lower = [g for g in gens if g < tgen]
            upper = [g for g in gens if g > tgen]
            
            if lower and upper:
                # Linear interpolation
                g1, g2 = max(lower), min(upper)
                i1, i2 = gens.index(g1), gens.index(g2)
                v1, v2 = values[i1], values[i2]
                interpolated = v1 + (v2 - v1) * (tgen - g1) / (g2 - g1)
                aligned.append(interpolated)
            elif lower:
                # Use last known value
                aligned.append(values[gens.index(max(lower))])
            elif upper:
                # Use first known value
                aligned.append(values[gens.index(min(upper))])
            else:
                aligned.append(np.nan)
    return aligned

fitness_matrix = []
acc_matrix = []
complexity_matrix = []

for gens, fitness, acc, complexity in zip(all_gens, all_fitness, all_acc, all_complexity):
    fitness_matrix.append(align_to_gens(gens, fitness, unique_gens))
    acc_matrix.append(align_to_gens(gens, acc, unique_gens))
    complexity_matrix.append(align_to_gens(gens, complexity, unique_gens))

fitness_matrix = np.array(fitness_matrix, dtype=float)
acc_matrix = np.array(acc_matrix, dtype=float)
complexity_matrix = np.array(complexity_matrix, dtype=float)
gens_array = np.array(unique_gens)

# Calculate mean and std
mean_f = np.nanmean(fitness_matrix, axis=0)
std_f = np.nanstd(fitness_matrix, axis=0)
mean_a = np.nanmean(acc_matrix, axis=0)
std_a = np.nanstd(acc_matrix, axis=0)
mean_c = np.nanmean(complexity_matrix, axis=0)
std_c = np.nanstd(complexity_matrix, axis=0)

# ------------------------------------------------------
# Create 3-in-1 Figure
# ------------------------------------------------------
fig, axes = plt.subplots(3, 1, figsize=(10, 12), sharex=True)

titles = ["Fitness over Generations", "Accuracy over Generations", "Complexity over Generations"]
means = [mean_f, mean_a, mean_c]
stds = [std_f, std_a, std_c]
ylabels = ["Fitness", "Accuracy", "Complexity"]
colors = ['#1f77b4', '#ff7f0e', '#2ca02c']

for ax, title, mean, std, ylabel, color in zip(axes, titles, means, stds, ylabels, colors):
    ax.plot(gens_array, mean, linewidth=2, label="Mean", color=color)
    ax.fill_between(gens_array, mean - std, mean + std, alpha=0.25, label="Std. Deviation", color=color)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.set_title(title, fontsize=12)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc='best')

axes[-1].set_xlabel("Generation", fontsize=11)
fig.suptitle(f"Evolutionary Optimization Progress – Multi-Run Summary ({len(log_files)} runs)", 
             fontsize=16, fontweight='bold')

plt.tight_layout(rect=[0, 0, 1, 0.97])

# Save for thesis
output_file = "multi_run_3in1_plot.pdf"
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"\nPlot saved to: {output_file}")
