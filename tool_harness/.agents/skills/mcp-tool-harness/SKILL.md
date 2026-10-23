---
name: mcp-tool-harness
description: Development, testing, logging, environment export, and subagent orchestration for the ESP32-S3 and H1OS MCP Tool Harness.
---

# MCP Tool Harness Development & Subagent Orchestration Skill

## Overview
This skill provides operational procedures for maintaining, testing, and expanding the MCP Python Tool Harness for ESP32-S3 firmware development, Clangd LSP semantic code intelligence, and firmware memory footprint analysis.

## Key Operational Capabilities

### 1. Subagent Orchestration (`invoke_subagent` / `define_subagent`)
* **Research Subagents**: Spawn `research` subagents when deep documentation searches, multi-file header analysis, or datasheet inspections are required.
* **Parallel Execution**: Launch concurrent subagents for independent tasks (e.g. build verification running alongside documentation synthesis).
* **Autonomous Continuation**: Do NOT poll subagents in loops. Wait for reactive background system messages.

### 2. ESP-IDF Environment Export & Build Automation
* **Automatic Discovery**: `init_idf_environment` discovers `C:\esp\v6.1\esp-idf\export.bat` or `export.sh` and exports `IDF_PATH`, `PATH`, GCC toolchains, Ninja, CMake, and Python virtualenv into `os.environ`.
* **Execution**: Call `trigger_idf_build`, `get_idf_size`, or `reconfigure_idf_project` directly; environment variables auto-initialize prior to execution.

### 3. Semantic Code Navigation & Diagnostics (Clangd FastMCP Bridge)
* **Symbol Navigation**: Call `clangd_find_references`, `clangd_get_definition`, `clangd_get_hover`, and `clangd_workspace_symbol` for authoritative type checking and cross-referencing without guessing.
* **Diagnostics**: Query `clangd_get_diagnostics` to capture compiler-grade warnings and header inclusion errors across files.

### 4. Memory Footprint Profiling (Firmware Analyzer)
* **Map Analysis**: Call `get_memory_usage_summary` and `analyze_top_symbols` to inspect SRAM, PSRAM, and Flash consumption against partition constraints.

### 5. MCP Server Transport & Logging Integrity
* **Oversight File Logs**: All servers append execution logs to `Path.home() / ".mcp_logs" / "<server_name>.log"` (`C:\Users\Matt\.mcp_logs\`).
* **Stdio Transport**: All logging handlers write exclusively to physical log files and `sys.stderr`. `sys.stdout` must remain 100% pure JSON-RPC.
