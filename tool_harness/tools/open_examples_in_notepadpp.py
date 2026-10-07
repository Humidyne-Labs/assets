#!/usr/bin/env python3
"""
Open All BSP Example main.c Source Files in Notepad++ for Code Review.
Locates Notepad++ and opens all standalone example main.c files in tabs.
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

DEFAULT_NOTEPADPP_PATHS = [
    Path(r"C:\Program Files\Notepad++\notepad++.exe"),
    Path(r"C:\Program Files (x86)\Notepad++\notepad++.exe"),
]


def find_notepadpp() -> Path:
    """Finds Notepad++ executable on the system."""
    for p in DEFAULT_NOTEPADPP_PATHS:
        if p.exists():
            return p
    return None


def main():
    parser = argparse.ArgumentParser(description="Open all BSP example main.c files in Notepad++.")
    parser.add_argument(
        "--examples-dir",
        type=Path,
        default=Path(r"C:\Users\Matt\Documents\GitHub\esp32-s3_bsp\examples"),
        help="Root directory containing example project folders",
    )
    parser.add_argument(
        "--notepad-path",
        type=Path,
        default=None,
        help="Custom path to notepad++.exe",
    )
    parser.add_argument(
        "--include-test-suite",
        action="store_true",
        help="Include Peripherals_Test_Suite main.c",
    )
    args = parser.parse_args()

    # Resolve Notepad++ path
    npp_path = args.notepad_path or find_notepadpp()
    if not npp_path or not npp_path.exists():
        sys.exit(f"Error: Notepad++ executable not found at {npp_path or 'default paths'}.\nInstall Notepad++ or pass --notepad-path.")

    if not args.examples_dir.exists():
        sys.exit(f"Error: Examples directory '{args.examples_dir}' not found.")

    # Find all main.c files inside examples directory
    main_files = []
    for p in sorted(args.examples_dir.glob("*/main/main.c")):
        if not args.include_test_suite and "peripherals_test_suite" in p.parts[-3].lower():
            continue
        main_files.append(p)

    # Also check for any standalone *.c files directly in examples root
    for p in sorted(args.examples_dir.glob("*.c")):
        main_files.append(p)

    if not main_files:
        sys.exit(f"No main.c files found in {args.examples_dir}")

    print("==================================================")
    print("  OPEN EXAMPLES IN NOTEPAD++")
    print("==================================================")
    print(f" Notepad++ Executable : {npp_path}")
    print(f" Found Examples Count : {len(main_files)}")
    print("--------------------------------------------------")

    for idx, f in enumerate(main_files, 1):
        print(f" {idx:>2}. {f.parent.parent.name:<25} -> {f}")

    cmd = [str(npp_path)] + [str(f) for f in main_files]
    print("--------------------------------------------------")
    print("[LAUNCH] Opening all files in Notepad++ tabs...")

    subprocess.Popen(cmd)
    print(" [OK] Launched Notepad++ successfully!")
    print("==================================================\n")


if __name__ == "__main__":
    main()
