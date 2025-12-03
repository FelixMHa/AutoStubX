import subprocess
import os

mainfolder = "../Training-Data-Generation/symbolic-regression-data/training"

for folder in os.listdir(mainfolder):
    folder_path = os.path.join(mainfolder, folder)

    # Only process subfolders, skip files directly in mainfolder
    if os.path.isdir(folder_path):
        for filename in os.listdir(folder_path):
            if filename.endswith(".json"):  # only process JSON files
                filepath = os.path.join(folder_path, filename)
                print(f"Running on {filepath}...")

                subprocess.run([
                    "python", "rungp.py", filepath,
                    "--population", "200",
                    "--generations", "200",
                    "--output", f"{filename}_genome.json"
                ])
