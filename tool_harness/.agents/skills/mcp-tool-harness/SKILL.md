---
name: mcp-tool-harness
description: Development, testing, logging, environment export, and subagent orchestration for the ESP32-S3 BSP and LVGL 9 MCP Tool Harness.
---

# MCP Tool Harness Development & Subagent Orchestration Skill

## Overview
This skill provides operational procedures for maintaining, testing, and expanding the MCP Python Tool Harness for ESP32-S3 BSP development, LVGL 9 UI virtualization, and firmware analysis.

## Key Operational Capabilities

### 1. Subagent Orchestration (`invoke_subagent` / `define_subagent`)
* **Research Subagents**: Spawn `research` subagents when deep documentation searches, multi-file header analysis, or datasheet inspections are required.
* **Parallel Execution**: Launch concurrent subagents for independent tasks (e.g. build verification running alongside UI snapshot diffing).
* **Autonomous Continuation**: Do NOT poll subagents in loops. Wait for reactive background system messages.

### 2. ESP-IDF Environment Export & Build Automation
* **Automatic Discovery**: `init_idf_environment` discovers `C:\esp\v6.1\esp-idf\export.bat` or `export.sh` and exports `IDF_PATH`, `PATH`, GCC toolchains, Ninja, CMake, and Python virtualenv into `os.environ`.
* **Execution**: Call `trigger_idf_build`, `get_idf_size`, or `reconfigure_idf_project` directly; environment variables auto-initialize prior to execution.

### 3. MCP Server Transport & Logging Integrity
* **Oversight File Logs**: All servers append execution logs to `Path.home() / ".mcp_logs" / "<server_name>.log"` (`C:\Users\Matt\.mcp_logs\`).
* **Stdio Transport**: All logging handlers write exclusively to physical log files and `sys.stderr`. `sys.stdout` must remain 100% pure JSON-RPC.

### 4. LVGL 9 Headless UI Snapshot & Visual Regression
* **Virtualization**: Compile C widget code using `render_ui_snapshot` (LVGL 9.6.0 target).
* **Regression Testing**: Use `compare_ui_snapshots` to compute pixel delta and SSIM similarity overlay heatmaps between baseline and candidate UI code.
