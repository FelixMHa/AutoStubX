import matplotlib.pyplot as plt

# Your data
data = {
    "A_accuracy": 0.6216662883211679,
    "X_accuracy": 0.7735325861353258,
    "A_over_90": 136,
    "X_over_90": 134,
    "A_fully_correct": 77,
    "X_fully_correct": 87,
    "methods_compared_count": 219,
}

methods = data["methods_compared_count"]

# Convert to percentages
A_acc_pct = data["A_accuracy"] * 100
X_acc_pct = data["X_accuracy"] * 100
A_over90_pct = (data["A_over_90"] / methods) * 100
X_over90_pct = (data["X_over_90"] / methods) * 100
A_fully_pct = (data["A_fully_correct"] / methods) * 100
X_fully_pct = (data["X_fully_correct"] / methods) * 100

labels = ["Accuracy", "Over 90", "Fully Correct"]
A_values = [A_acc_pct, A_over90_pct, A_fully_pct]
X_values = [X_acc_pct, X_over90_pct, X_fully_pct]

x = range(len(labels))
width = 0.35

# Thesis-quality chart
fig, ax = plt.subplots(figsize=(8,6))
bars_A = ax.bar([i - width/2 for i in x], A_values, width, label="AutoStub", color="#4C78A8")
bars_X = ax.bar([i + width/2 for i in x], X_values, width, label="AutoStubX", color="#F58518")

ax.set_xticks(list(x))
ax.set_xticklabels(labels, fontsize=12)
ax.set_ylabel("Percentage of Methods (%)", fontsize=12)
ax.set_title("Comparison of AutoStub vs AutoStubX", fontsize=14, fontweight="bold")
ax.legend(fontsize=11)

# Annotate bars with values
for bars in [bars_A, bars_X]:
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f"{height:.1f}%",
                    xy=(bar.get_x() + bar.get_width()/2, height),
                    xytext=(0,3),
                    textcoords="offset points",
                    ha="center", va="bottom", fontsize=10)

plt.tight_layout()
plt.savefig("autostub_vs_autostubx_thesis.png", dpi=300)
plt.savefig("autostub_vs_autostubx_thesis.pdf")
plt.close()

print("Saved: autostub_vs_autostubx_thesis.(png|pdf)")
