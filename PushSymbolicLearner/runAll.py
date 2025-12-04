import subprocess
import os
import argparse



def startRun(mainfolder, folder):
    folder_path = os.path.join(mainfolder, folder)
    if os.path.isdir(folder_path):
        for filename in os.listdir(folder_path):
            if filename.endswith(".json"):  # only process JSON files
                filepath = os.path.join(folder_path, filename)
                print(f"Running on {filepath}...")

                subprocess.run([
                    "python", "rungp.py", filepath,
                    "--population", "200",
                    "--generations", "200",
                    "--output", f"{filename}_genome.json",
                    "--fast"
                ])
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_directory", nargs='?', default="../Training-Data-Generation/symbolic-regression-data/training",
                        help="Path to the main data directory containing subfolders")
    parser.add_argument("--includefilesInMain", default=False, nargs='?', type=bool,
                        help="Whether to include files in the main directory")
    args = parser.parse_args()
    mainfolder = args.data_directory
    if args.includefilesInMain:
        startRun(mainfolder, "")
    else:
        for folder in os.listdir(mainfolder):
            startRun(mainfolder, folder)

if __name__ == "__main__":
    main()