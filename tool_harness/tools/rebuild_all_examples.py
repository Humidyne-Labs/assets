#!/usr/bin/env python3
"""
Batch ESP-IDF Example Rebuilder & Verification Suite.
Iterates over all standalone example project directories in the BSP examples folder,
triggers clean builds, captures compiler diagnostics, and outputs a master build summary report.
"""

import os
import sys
import time
import datetime
import argparse
import subprocess
from pathlib import Path
from functools import partial

# Override print to ensure immediate unbuffered output to stdout
print = partial(print, flush=True)


class TeeLogger:
    """Tee output stream that writes simultaneously to terminal stdout and a master log file."""
    def __init__(self, log_path: Path):
        self.terminal = sys.stdout
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_file = open(self.log_path, "a", encoding="utf-8", buffering=1)

        latest_path = self.log_path.parent / "latest_rebuild.log"
        self.latest_file = open(latest_path, "w", encoding="utf-8", buffering=1)

    def write(self, message):
        self.terminal.write(message)
        self.terminal.flush()
        self.log_file.write(message)
        self.log_file.flush()
        self.latest_file.write(message)
        self.latest_file.flush()

    def flush(self):
        self.terminal.flush()
        self.log_file.flush()
        self.latest_file.flush()

    def close(self):
        self.log_file.close()
        self.latest_file.close()


def compile_project(build_cmd: str, working_dir: Path, timeout: int = 300) -> tuple[bool, str]:
    """Runs the build system command and captures stdout/stderr diagnostics."""
    try:
        proc = subprocess.run(
            build_cmd,
            cwd=working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
            shell=True,
        )
        return proc.returncode == 0, proc.stdout
    except subprocess.TimeoutExpired:
        return False, f"Build timed out after {timeout} seconds."
    except Exception as exc:
        return False, f"Failed to execute build command: {exc}"


def filter_compiler_errors(build_output: str, max_lines: int = 40) -> str:
    """Isolates compiler error lines to present a clean preview."""
    lines = build_output.splitlines()
    error_lines = [line for line in lines if "error:" in line.lower() or "undefined reference" in line.lower() or "ninja: error" in line.lower()]
    if not error_lines:
        return "\n".join(lines[-max_lines:])
    return "\n".join(error_lines[:max_lines])


def main():
    parser = argparse.ArgumentParser(description="Batch compile all ESP32-S3 BSP example projects.")
    parser.add_argument(
        "--examples-dir",
        type=Path,
        default=Path(r"C:\Users\Matt\Documents\GitHub\esp32-s3_bsp\examples"),
        help="Root directory containing example project folders",
    )
    parser.add_argument(
        "--build-cmd",
        type=str,
        default="idf.py build",
        help="Build command to execute for each project (default: idf.py build)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Perform clean build by removing build/ folder before compiling",
    )
    parser.add_argument(
        "--include-test-suite",
        action="store_true",
        help="Include Peripherals_Test_Suite in the rebuild pass (default: excluded)",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path(r"C:\Users\Matt\Documents\GitHub\assets\tool_harness\run_log"),
        help="Directory to store persistent master rebuild logs (default: run_log/)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print full compiler output for all projects",
    )
    args = parser.parse_args()

    # Initialize master log stream
    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file_path = args.log_dir / f"rebuild_{timestamp_str}.log"
    logger = TeeLogger(log_file_path)
    sys.stdout = logger
    sys.stderr = logger

    print("==================================================")
    print("  ESP32-S3 BSP BATCH EXAMPLES REBUILD SUITE")
    print("==================================================")
    print(f" Target Directory : {args.examples_dir}")
    print(f" Build Command    : {args.build_cmd}")
    print(f" Master Log File  : {log_file_path}")
    print("==================================================")

    if not args.examples_dir.exists():
        sys.exit(f"Error: Examples directory '{args.examples_dir}' not found.")

    # Locate all subdirectories containing CMakeLists.txt and main/main.c
    subdirs = sorted([d for d in args.examples_dir.iterdir() if d.is_dir()])
    project_dirs = []

    for d in subdirs:
        if not args.include_test_suite and d.name.lower() == "peripherals_test_suite":
            continue
        if (d / "CMakeLists.txt").exists() or (d / "main" / "main.c").exists():
            project_dirs.append(d)

    if not project_dirs:
        print(f"No valid ESP-IDF example projects found in {args.examples_dir}")
        return

    print(f"[START] Found {len(project_dirs)} example projects to compile...\n")

    passed_projects = []
    failed_projects = []
    total_start_time = time.time()

    for idx, proj_dir in enumerate(project_dirs, 1):
        proj_name = proj_dir.name
        print(f"--------------------------------------------------")
        print(f"[{idx}/{len(project_dirs)}] Building Example: {proj_name}")
        print(f"--------------------------------------------------")

        # Optional clean build
        if args.clean:
            build_folder = proj_dir / "build"
            if build_folder.exists():
                print(f" [CLEAN] Removing build directory: {build_folder}")
                import shutil
                try:
                    shutil.rmtree(build_folder)
                except Exception as clean_err:
                    print(f" [WARN] Could not remove build folder: {clean_err}")

        proj_start_time = time.time()
        compiled_ok, build_log = compile_project(args.build_cmd, proj_dir)
        proj_duration = time.time() - proj_start_time

        # Save individual per-project log
        per_project_log_path = proj_dir / "build_validation.log"
        log_header = f"=== BUILD VALIDATION REPORT: {proj_name} ===\nDate: {datetime.datetime.now().isoformat()}\nDuration: {proj_duration:.2f}s\nStatus: {'PASS' if compiled_ok else 'FAIL'}\n\n"
        per_project_log_path.write_text(log_header + build_log, encoding="utf-8")

        if compiled_ok:
            print(f" [PASS] Clean build succeeded! ({proj_duration:.1f}s)")
            passed_projects.append((proj_name, proj_duration))
            if args.verbose:
                print("\n--- FULL BUILD LOG (SUCCESS) ---")
                print(build_log)
                print("--------------------------------\n")
        else:
            print(f" [FAIL] Build failed! ({proj_duration:.1f}s)")
            diagnostics = filter_compiler_errors(build_log)
            failed_projects.append((proj_name, proj_duration, diagnostics))
            print(f"Compiler Diagnostics:\n{diagnostics}\n")
            if args.verbose:
                print("\n--- FULL BUILD LOG (FAILURE) ---")
                print(build_log)
                print("--------------------------------\n")

    total_duration = time.time() - total_start_time

    # Final Master Summary Report
    print("\n==================================================")
    print("  BATCH REBUILD SUMMARY REPORT")
    print("==================================================")
    print(f" Total Projects Evaluated : {len(project_dirs)}")
    print(f" Passed Projects          : {len(passed_projects)}")
    print(f" Failed Projects          : {len(failed_projects)}")
    print(f" Total Execution Time     : {total_duration / 60:.2f} minutes ({total_duration:.1f}s)")
    print("--------------------------------------------------")

    if passed_projects:
        print("\n [PASSED PROJECTS]")
        for name, dur in passed_projects:
            print(f"   [PASS] {name:<30} ({dur:.1f}s)")

    if failed_projects:
        print("\n [FAILED PROJECTS]")
        for name, dur, diag in failed_projects:
            print(f"   [FAIL] {name:<30} ({dur:.1f}s)")
            print(f"         Preview: {diag.splitlines()[0] if diag.splitlines() else 'No diagnostic line'}")

    print("==================================================")
    print(f" Detailed Master Log Saved To: {log_file_path}")
    print("==================================================\n")

    sys.exit(0 if len(failed_projects) == 0 else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Rebuild process interrupted by user.")
        sys.exit(0)
