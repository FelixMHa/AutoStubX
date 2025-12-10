from pathlib import Path
import argparse
from typing import Set

#!/usr/bin/env python3
"""
filefinder.py

Compare filenames in two folders. Usage:
    python filefinder.py /path/to/dirA /path/to/dirB [--recursive] [--ignore-ext] [--ignore-case]

Outputs lists of:
 - common filenames
 - only in dir A
 - only in dir B
"""


def list_filenames(directory: Path, recursive: bool) -> Set[str]:
    if recursive:
        paths = (p for p in directory.rglob("*") if p.is_file())
    else:
        paths = (p for p in directory.iterdir() if p.is_file())
    return {p.name for p in paths}


def normalize_names(names: Set[str], ignore_ext: bool, ignore_case: bool) -> Set[str]:
    out = set()
    for n in names:
        if ignore_ext:
            n = Path(n).stem
        if ignore_case:
            n = n.lower()
        out.add(n)
    return out


def compare_dirs(dir_a: Path, dir_b: Path, recursive: bool, ignore_ext: bool, ignore_case: bool):
    a_names = list_filenames(dir_a, recursive)
    b_names = list_filenames(dir_b, recursive)
    print("Start")
    a_norm = normalize_names(a_names, ignore_ext, ignore_case)
    b_norm = normalize_names(b_names, ignore_ext, ignore_case)

    common = sorted(a_norm & b_norm)
    only_a = sorted(a_norm - b_norm)
    only_b = sorted(b_norm - a_norm)

    print(f"Directory A: {dir_a}")
    print(f"Directory B: {dir_b}")
    print()
    print(f"Common ({len(common)}):")
    for n in common:
        print("  ", n)
    print()
    print(f"Only in A ({len(only_a)}):")
    for n in only_a:
        print("  ", n)
    print()
    print(f"Only in B ({len(only_b)}):")
    for n in only_b:
        print("  ", n)


def parse_args():
    p = argparse.ArgumentParser(description="Compare filenames in two folders")
    p.add_argument("dir_a", type=Path)
    p.add_argument("dir_b", type=Path)
    p.add_argument("--recursive", "-r", action="store_true", help="Recurse into subfolders")
    p.add_argument("--ignore-ext", "-e", action="store_true", help="Compare names ignoring file extensions")
    p.add_argument("--ignore-case", "-c", action="store_true", help="Case-insensitive comparison")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if not args.dir_a.is_dir() or not args.dir_b.is_dir():
        raise SystemExit("Both paths must be directories.")
    compare_dirs(args.dir_a, args.dir_b, args.recursive, args.ignore_ext, args.ignore_case)