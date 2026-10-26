import os
import re
import matplotlib.pyplot as plt

def parse_logs_and_plot(log_dir="./evaluation/test_all_logs"):
    accuracies = {}

    # Regular expressions to extract data
    # Matches the JSON filename to use as the stub label
    name_pattern = re.compile(r"Loading training data from .*?[/\\](.*?)\.json")
    gen_pattern = re.compile(r"Generated:\s*(\d+)")
    pass_pattern = re.compile(r"Passed\s*:\s*(\d+)")

    if not os.path.exists(log_dir):
        print(f"Directory not found: {log_dir}")
        return

    for filename in os.listdir(log_dir):
        filepath = os.path.join(log_dir, filename)
        if not os.path.isfile(filepath):
            continue

        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

            name_match = name_pattern.search(content)
            gen_match = gen_pattern.search(content)
            pass_match = pass_pattern.search(content)

            if gen_match and pass_match:
                # Use the extracted JSON name, or fallback to the log filename
                stub_name = name_match.group(1) if name_match else filename
                
                generated = int(gen_match.group(1))
                passed = int(pass_match.group(1))

                # Calculate accuracy, defaulting to 0 if no tests were generated
                accuracy = (passed / generated * 100) if generated > 0 else 0.0
                accuracies[stub_name] = accuracy

    if not accuracies:
        print("No valid round-trip data found in the logs.")
        return

    # Sort by accuracy descending for a cleaner graph
    sorted_stubs = sorted(accuracies.items(), key=lambda x: x[1], reverse=True)
    labels = [item[0] for item in sorted_stubs]
    values = [item[1] for item in sorted_stubs]

    # Generate the bar chart
    plt.figure(figsize=(12, 6))
    bars = plt.bar(labels, values, color='skyblue', edgecolor='black')
    
    plt.title("Stub Round-Trip Accuracies", fontsize=14, fontweight='bold')
    plt.ylabel("Accuracy (%)", fontsize=12)
    plt.xlabel("Stub Name", fontsize=12)
    plt.ylim(0, 105) # Add slight padding above 100%
    
    # Rotate x-axis labels to prevent overlap
    plt.xticks(rotation=45, ha="right", fontsize=9)

    # Add the percentage text on top of each bar
    for bar in bars:
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2, 
            height + 1, 
            f'{height:.1f}%', 
            ha='center', 
            va='bottom', 
            fontsize=9
        )

    plt.tight_layout()
    
    # Save and show the plot
    output_image = "roundtrip_accuracies.png"
    plt.savefig(output_image)
    print(f"Graph saved as {output_image}")
    plt.show()

if __name__ == "__main__":
    parse_logs_and_plot()