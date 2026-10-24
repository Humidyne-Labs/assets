---
name: mcp-tool-harness
description: Operational reference and subagent orchestration for the 3-Finger ESP32-S3 and H1OS MCP Tool Suite.
---

# 3-Finger MCP Architecture & Subagent Orchestration Skill

## Overview
This skill governs the operational procedures, subagent delegation patterns, and tool interaction models for the 3-Finger MCP embedded firmware development architecture supporting H1OS on ESP32-S3.

## The 3-Finger Architecture

### Finger 1: Semantic Code Intelligence (`clangd`)
* **Engine:** `schuay/clangd-mcp` via `uvx --with "mcp<2" clangd-mcp` bound to LLVM 18 (`C:\clang+llvm-18.1.8\bin\clangd.exe`) and H1OS's `compile_commands.json`.
* **Zero-Hallucination Capabilities:**
  - `get_callers` & `get_callees`: Full incoming/outgoing call hierarchies across tasks, drivers, and HAL.
  - `get_definition`: Exact jumps to implementation or header declarations.
  - `find_references`: Deterministic list of all call sites and symbol uses.
  - `find_symbol`: Instant symbol lookups for structs, enums, typedefs, and functions.
  - `get_type_info`: Complete type layout, sizing, and struct member signatures.
* **Cost & Accuracy:** Runs locally at $0.00 token cost, replacing token-heavy eager whole-repo extraction.

### Finger 2: Hardware, Build & Serial Execution (`esp-idf`)
* **Engine:** Native ESP-IDF v6.1 MCP server (`idf.py -C <project_dir> mcp-server`).
* **Environment:** Automatically exports IDF environment (`C:\esp\v6.1\esp-idf\export.bat`).
* **Capabilities:**
  - `build_project`: Incremental compilation via Ninja, returning line-numbered diagnostics.
  - `flash_project`: Direct flashing over USB/UART JTAG.
  - Monitor tools: Captures boot sequence and runtime panic backtraces directly without manual terminal copy-paste.

### Finger 3: Documentation & Datasheets (`local-index` & `espressif-documentation`)
* **Local Indexer (`local-index`):** Runs `uvx code-index-mcp` targeting `H1OS/docs/` and converted markdown datasheets (`SHTC3`, `PCF85063A`, `ES8311`, `SSD1681`). Delivers pinpoint register definitions and blueprint excerpts on demand.
* **Upstream Docs (`espressif-documentation`):** Official Espressif API docs, Technical Reference Manual (TRM) sections, and silicon errata via `https://mcp.espressif.com/docs`.
* **Component Registry (`esp-component-registry`):** On-demand searches for certified Espressif IDF component packages.

## Scientific Computing, Verification & Telemetry (Lazy-Loaded)

### 1. Telemetry Analytics Engine (`duckdb`)
* **Engine:** `uvx --with "mcp<2" mcp-server-duckdb --db-path :memory:`
* **Usage:** Queries disk logs directly using SQL (`read_csv_auto('docs/telemetry/*.csv')`). No database ingestion or file-locking conflicts.

### 2. Science & Math Prover (`science`)
* **Engine:** `uv run --with "mcp<2" --with sympy --with z3-solver --with scipy --with numpy tools/science_mcp.py`
* **Tools:**
  - `derive_fixed_point_polynomial`: Computes Padé/Chebyshev integer polynomial approximations for FPU-less ULP RISC-V in Q16.16 / Q8.24 format with Horner evaluation code and error bounds.
  - `solve_z3_assertions`: Formal verification using Microsoft Z3 SMT solver. Proves freedom from race conditions and GPIO latching deadlocks across sleep/wake state machines.
  - `fit_thermal_rc`: SciPy curve fitting of empirical sensor heating/cooling curves to derive time constant $\tau$.
  - `eval_symbolic_math`: SymPy symbolic simplification, factoring, and evaluation.

## Subagent Orchestration Guidelines

### 1. Subagent Specialization
* **Research Subagents (`research`):** Spawn for targeted, multi-step documentation searches, external datasheet verification, or deep header inspections that would clutter main conversation context.
* **Parallel Execution:** Launch concurrent tasks for independent work (e.g. running build verification alongside documentation review).
* **Reactive Wakeup:** Do NOT poll subagents in loops. Wait for background reactive wakeups from the agent messaging system.

### 2. Zero Token-Burn Policy
* **Never load entire repositories into context:** Always query `clangd` or `local-index` lazily.
* **Single-file surgical edits:** Use `edit_file` with precise targets; avoid re-emitting whole files unnecessarily.
* **Physical constraints over snapshots:** Validate UI against hardware constraints defined in `lvgl.md` rather than maintaining brittle host emulation frameworks.
