#!/usr/bin/env python3
"""
Automated BSP Example Generator & Compiler Validation Pipeline.
Iterates over ESP32-S3 BSP header files, prompts Gemini via Google's official GenAI SDK (from google import genai / from google.cloud)
for isolated reference examples, and iterates against compiler feedback until clean builds are achieved.

Includes model listing (--list-models) and token usage statistics tracking (--show-usage).
"""

import os
import re
import sys
import argparse
import subprocess
import warnings
from pathlib import Path
from functools import partial

# Suppress SDK warnings (e.g. AFC deprecation warnings from google-genai)
warnings.filterwarnings("ignore", category=UserWarning)

# Override print to ensure immediate unbuffered output to stdout
print = partial(print, flush=True)

# Google SDK Imports
GENAI_AVAILABLE = False
VERTEX_AVAILABLE = False

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    pass

try:
    from google.cloud import aiplatform
    VERTEX_AVAILABLE = True
except ImportError:
    pass


SYSTEM_INSTRUCTION = """\
You are an expert embedded firmware engineer writing unit-level hardware examples for ESP32-S3 BSP.
Rules you must strictly follow:
1. Use ONLY function prototypes, macros, types, and enums declared in the provided header file and pinout.h.
2. NEVER guess, invent, or extrapolate peripheral APIs.
3. Every API call returning an error code (e.g., esp_err_t) MUST be wrapped in ESP_ERROR_CHECK() or checked explicitly.
4. Keep the example focused solely on the peripheral declared in the header. Keep it under 150 lines.
5. Provide ONLY valid C code inside code fences.
6. Always include BSP headers using the 'bsp/' subdirectory prefix (e.g., #include "bsp/bsp.h", #include "bsp/pinout.h", #include "bsp/bsp_display.h"). NEVER use `#include "bsp.h"` without the `bsp/` prefix.
"""

INITIAL_PROMPT_TEMPLATE = """\
Generate a standalone reference example for the following BSP peripheral header:

Header File: {header_name}
```c
{header_content}
```

{source_section}

Requirements:
- Target function: app_main(void)
- Perform necessary system/power initialization before peripheral access.
- Execute one clear, observable peripheral action.
- Log events cleanly via ESP_LOGI or printf.
- Terminate or idle safely (e.g. vTaskDelete(NULL) or vTaskDelay).
"""

FIX_PROMPT_TEMPLATE = """\
The code you generated failed to compile.

Compiler Diagnostic Output:
```
{compiler_errors}
```

Original Broken Source Code:
```c
{broken_code}
```

Header File Reference:
```c
{header_content}
```

Fix the errors. Ensure all types, parameters, and signatures strictly match the header.
Return the entire updated, compilable C source code inside a ```c block.
"""


class TokenUsageTracker:
    """Tracks cumulative prompt, candidate (response), and total token counts across API requests."""
    def __init__(self):
        self.requests_count = 0
        self.total_prompt_tokens = 0
        self.total_candidate_tokens = 0
        self.total_tokens = 0

    def record_usage(self, usage_metadata):
        if not usage_metadata:
            return
        self.requests_count += 1
        prompt = getattr(usage_metadata, "prompt_token_count", 0) or 0
        candidate = getattr(usage_metadata, "candidates_token_count", 0) or 0
        total = getattr(usage_metadata, "total_token_count", 0) or (prompt + candidate)

        self.total_prompt_tokens += prompt
        self.total_candidate_tokens += candidate
        self.total_tokens += total
        return prompt, candidate, total

    def print_summary(self):
        print("\n==================================================")
        print("  GEMINI API TOKEN USAGE SUMMARY REPORT")
        print("==================================================")
        print(f" Total API Requests Executed : {self.requests_count}")
        print(f" Total Prompt Tokens         : {self.total_prompt_tokens:,}")
        print(f" Total Candidate Tokens      : {self.total_candidate_tokens:,}")
        print(f" Combined Total Tokens Used  : {self.total_tokens:,}")
        print("==================================================")


def extract_c_code(response_text: str) -> str:
    """Extracts raw C code from markdown code fences."""
    match = re.search(r"```(?:c|cpp)?\s*(.*?)\s*```", response_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return response_text.strip()


def compile_project(build_cmd, working_dir: Path) -> tuple[bool, str]:
    """Runs the build system command and captures diagnostics."""
    try:
        cmd_input = " ".join(build_cmd) if isinstance(build_cmd, list) else build_cmd
        proc = subprocess.run(
            cmd_input,
            cwd=working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=180,
            check=False,
            shell=True,
        )
        return proc.returncode == 0, proc.stdout
    except subprocess.TimeoutExpired:
        return False, "Build timed out after 180 seconds."
    except Exception as exc:
        return False, f"Failed to execute build command: {exc}"


def filter_compiler_errors(build_output: str, max_lines: int = 40) -> str:
    """Isolates compiler error lines to keep context tight for the LLM."""
    lines = build_output.splitlines()
    error_lines = [line for line in lines if "error:" in line.lower() or "undefined reference" in line.lower()]
    if not error_lines:
        return "\n".join(lines[-max_lines:])
    return "\n".join(error_lines[:max_lines])


_LAST_API_CALL_TIME = 0.0


def call_gemini_with_retry(client, model: str, contents, config, max_retries: int = 3, min_delay: float = 12.0, verbose: bool = False):
    """Executes client.models.generate_content with strict pacing delay, 503/429 backoff, and model fallbacks."""
    import time
    global _LAST_API_CALL_TIME

    # Enforce minimum delay between ANY two API calls to prevent 429 rate limits
    now = time.time()
    elapsed = now - _LAST_API_CALL_TIME
    if min_delay > 0 and _LAST_API_CALL_TIME > 0 and elapsed < min_delay:
        sleep_dur = min_delay - elapsed
        print(f" [PACING] Pausing {sleep_dur:.1f}s for 5 RPM rate limit...")
        time.sleep(sleep_dur)

    clean_model = model.replace("models/", "")
    fallback_chain = [model]
    for alt in ("gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-2.5-flash", "gemini-flash-latest"):
        if alt not in fallback_chain and alt != clean_model:
            fallback_chain.append(alt)

    for target_model in fallback_chain:
        for attempt in range(1, max_retries + 1):
            try:
                _LAST_API_CALL_TIME = time.time()
                response = client.models.generate_content(
                    model=target_model,
                    contents=contents,
                    config=config,
                )
                return response
            except Exception as exc:
                err_str = str(exc).lower()
                is_transient = any(k in err_str for k in ("503", "unavailable", "429", "rate", "overloaded", "resource_exhausted", "quota"))
                is_not_found = any(k in err_str for k in ("404", "not_found", "no longer available", "invalid model"))

                if is_transient and attempt < max_retries:
                    wait_sec = attempt * 15
                    print(f" [503/429 BUSY] Model '{target_model}' rate-limited or busy. Retrying in {wait_sec}s (Attempt {attempt}/{max_retries})...")
                    time.sleep(wait_sec)
                elif (is_transient or is_not_found) and target_model != fallback_chain[-1]:
                    print(f" [API FALLBACK] Model '{target_model}' failed ({'Not Found' if is_not_found else 'Busy'}). Switching to fallback model...")
                    break
                else:
                    if verbose:
                        import traceback
                        print(f" [FATAL API ERROR] ({target_model} attempt {attempt}): {exc}")
                        traceback.print_exc()
                    raise exc
    raise RuntimeError(f"Failed to generate content with model {model} and all fallback options.")


def initialize_genai_client(api_key: str = "", use_vertex: bool = False, project: str = "", location: str = "us-central1"):
    """Initializes and returns the official Google GenAI Client with API key or Vertex AI mode."""
    if not GENAI_AVAILABLE:
        sys.exit("Error: 'google-genai' SDK is not installed. Install via: pip install google-genai")

    if use_vertex:
        project_id = project or os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
        if not project_id:
            sys.exit("Error: Vertex AI mode requires a Google Cloud project ID (pass --project or set GOOGLE_CLOUD_PROJECT env var).")
        print(f"[AUTH] Initializing Google GenAI Client (Vertex AI mode) - Project: {project_id}, Location: {location}")
        return genai.Client(vertexai=True, project=project_id, location=location)
    else:
        key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            sys.exit("Error: GEMINI_API_KEY environment variable is not set. Set GEMINI_API_KEY or pass --api-key.")
        print("[AUTH] Initializing Google GenAI Client (Developer API mode)")
        return genai.Client(api_key=key)


def list_available_models(client):
    """Queries and displays available Gemini models from the Google API."""
    print("\n==================================================")
    print("  AVAILABLE GEMINI MODELS")
    print("==================================================")
    try:
        models = list(client.models.list())
        for m in models:
            name = getattr(m, "name", str(m))
            disp_name = getattr(m, "display_name", "")
            print(f" - {name:<35} | {disp_name}")
    except Exception as exc:
        print(f"Error querying model list: {exc}")
    print("==================================================\n")


def main():
    parser = argparse.ArgumentParser(description="Batch generate and compile BSP examples using Google GenAI SDK.")
    parser.add_argument(
        "--headers-dir",
        type=Path,
        default=Path(r"C:\Users\Matt\Documents\GitHub\esp32-s3_bsp\components\esp32-s3_bsp\include\bsp"),
        help="Directory containing BSP .h files",
    )
    parser.add_argument(
        "--sources-dir",
        type=Path,
        default=Path(r"C:\Users\Matt\Documents\GitHub\esp32-s3_bsp\components\esp32-s3_bsp\src"),
        help="Optional directory containing corresponding BSP .c implementation files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(r"C:\Users\Matt\Documents\GitHub\esp32-s3_bsp\examples"),
        help="Destination directory for verified examples",
    )
    parser.add_argument(
        "--test-runner-file",
        type=Path,
        default=Path(r"C:\Users\Matt\Documents\GitHub\esp32-s3_bsp\examples\Peripherals_Test_Suite\main\main.c"),
        help="Source file overwritten temporarily during build validation",
    )
    parser.add_argument(
        "--build-cmd",
        type=str,
        default="idf.py build",
        help="Build command to execute for compilation verification",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum self-correction compile attempts per header",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gemini-3.8-flash",
        help="Gemini model ID to use (default: gemini-3.8-flash)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default="",
        help="Google Gemini API key (or set GEMINI_API_KEY env var)",
    )
    parser.add_argument(
        "--use-vertex",
        action="store_true",
        help="Use Google Cloud Vertex AI mode instead of Developer API",
    )
    parser.add_argument(
        "--project",
        type=str,
        default="",
        help="Google Cloud Project ID (required for --use-vertex)",
    )
    parser.add_argument(
        "--location",
        type=str,
        default="us-central1",
        help="Google Cloud Vertex AI region (default: us-central1)",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List all available Gemini models and exit",
    )
    parser.add_argument(
        "--show-usage",
        action="store_true",
        help="Display detailed token usage statistics after generation",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=12.0,
        help="Delay in seconds between API calls to respect 5 RPM rate limit (default: 12.0s)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output (shows full compiler build logs, generated code, and API tracebacks)",
    )
    args = parser.parse_args()

    client = initialize_genai_client(
        api_key=args.api_key,
        use_vertex=args.use_vertex,
        project=args.project,
        location=args.location,
    )

    if args.list_models:
        list_available_models(client)
        return

    if not args.headers_dir.is_dir():
        sys.exit(f"Error: Headers directory '{args.headers_dir}' not found.")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    build_cmd_list = args.build_cmd.split()
    usage_tracker = TokenUsageTracker()

    # Backup existing test-runner file if present
    backup_file = None
    if args.test_runner_file.exists():
        backup_file = args.test_runner_file.with_suffix(".c.bak")
        args.test_runner_file.rename(backup_file)
        print(f"[SETUP] Backed up original {args.test_runner_file} to {backup_file}")

    try:
        headers = sorted(args.headers_dir.glob("*.h"))
        if not headers:
            print(f"No .h files found in {args.headers_dir}")
            return

        print(f"[START] Processing {len(headers)} BSP headers from {args.headers_dir}...")

        for header_path in headers:
            header_name = header_path.name
            print(f"\n==================================================")
            print(f"Processing Subsystem: {header_name}")
            print(f"==================================================")

            header_content = header_path.read_text(encoding="utf-8")

            # Check for matching implementation source file
            source_section = ""
            if args.sources_dir and args.sources_dir.exists():
                candidate_src = args.sources_dir / f"{header_path.stem}.c"
                if candidate_src.exists():
                    src_content = candidate_src.read_text(encoding="utf-8", errors="ignore")
                    source_section = f"Matching Implementation Source File ({candidate_src.name}):\n```c\n{src_content}\n```\n"
                    print(f" [INFO] Included matching implementation source: {candidate_src.name}")

            try:
                # Phase 1: Initial Generation
                prompt = INITIAL_PROMPT_TEMPLATE.format(
                    header_name=header_name,
                    header_content=header_content,
                    source_section=source_section,
                )

                print(f" [API] Sending initial prompt to Gemini ({args.model})...")
                response = call_gemini_with_retry(
                    client=client,
                    model=args.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        temperature=0.2,
                    ),
                    min_delay=args.delay,
                    verbose=args.verbose,
                )

                usage = usage_tracker.record_usage(getattr(response, "usage_metadata", None))
                if usage and args.show_usage:
                    print(f" [TOKENS] Initial Turn: Prompt={usage[0]}, Candidate={usage[1]}, Total={usage[2]}")

                current_code = extract_c_code(response.text)
                if args.verbose:
                    print("\n--- GENERATED CODE (INITIAL) ---")
                    print(current_code)
                    print("--------------------------------\n")
                success = False

                # Phase 2: Compiler Verification & Self-Correction Loop
                for attempt in range(1, args.max_retries + 1):
                    print(f" -> Compilation Attempt {attempt}/{args.max_retries}...")
                    print(f" [BUILD] Executing '{args.build_cmd}' (this typically takes 20-60s)...")

                    args.test_runner_file.parent.mkdir(parents=True, exist_ok=True)
                    args.test_runner_file.write_text(current_code, encoding="utf-8")

                    compiled_ok, build_log = compile_project(build_cmd_list, args.test_runner_file.parent.parent)

                    if compiled_ok:
                        print(f" [PASS] Clean build succeeded on attempt {attempt}!")
                        if args.verbose:
                            print("\n--- FULL BUILD LOG (SUCCESS) ---")
                            print(build_log)
                            print("--------------------------------\n")
                        success = True
                        break

                    print(f" [FAIL] Build failed. Extracting diagnostics...")
                    diagnostics = filter_compiler_errors(build_log)
                    if args.verbose:
                        print("\n--- FULL BUILD LOG (FAILURE) ---")
                        print(build_log)
                        print("--------------------------------\n")
                    else:
                        print(f"Diagnostics preview:\n{diagnostics[:300]}...\n")

                    if attempt == args.max_retries:
                        print(f" [ABORT] Exceeded max retries for {header_name}.")
                        break

                    fix_prompt = FIX_PROMPT_TEMPLATE.format(
                        compiler_errors=diagnostics,
                        broken_code=current_code,
                        header_content=header_content,
                    )

                    fix_response = call_gemini_with_retry(
                        client=client,
                        model=args.model,
                        contents=fix_prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_INSTRUCTION,
                            temperature=0.1,
                        ),
                        min_delay=args.delay,
                        verbose=args.verbose,
                    )
                    fix_usage = usage_tracker.record_usage(getattr(fix_response, "usage_metadata", None))
                    if fix_usage and args.show_usage:
                        print(f" [TOKENS] Retry {attempt}: Prompt={fix_usage[0]}, Candidate={fix_usage[1]}, Total={fix_usage[2]}")

                    current_code = extract_c_code(fix_response.text)
                    if args.verbose:
                        print(f"\n--- GENERATED CODE (RETRY {attempt}) ---")
                        print(current_code)
                        print("----------------------------------------\n")

                # Phase 3: Save generated example
                target_filename = f"{header_path.stem}_example.c"
                destination = args.output_dir / target_filename

                if success:
                    destination.write_text(current_code, encoding="utf-8")
                    print(f" [SAVED] Verified example saved to: {destination}")
                else:
                    failed_destination = args.output_dir / f"{header_path.stem}_failed.c"
                    failed_destination.write_text(current_code, encoding="utf-8")
                    print(f" [FAILED] Saved unverified candidate to: {failed_destination}")

            except Exception as header_exc:
                print(f" [ERROR] API call failed for {header_name}: {header_exc}")
                if args.verbose:
                    import traceback
                    traceback.print_exc()
                print(f" [SKIP] Skipping {header_name} and continuing with remaining headers...")

            if args.delay > 0 and header_path != headers[-1]:
                import time
                print(f" [PACING] Pausing {args.delay}s to respect 5 RPM rate limit...")
                time.sleep(args.delay)

    finally:
        if backup_file and backup_file.exists():
            if args.test_runner_file.exists():
                args.test_runner_file.unlink()
            backup_file.rename(args.test_runner_file)
            print(f"\n[CLEANUP] Restored original {args.test_runner_file}")

        if args.show_usage:
            usage_tracker.print_summary()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Script execution stopped by user.")
        sys.exit(0)