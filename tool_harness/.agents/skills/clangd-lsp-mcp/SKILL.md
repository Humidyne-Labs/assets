---
name: clangd-lsp-mcp
description: Semantic C/C++ code navigation, type inspection, definition jumps, reference finding, and compiler diagnostics via the Clangd LSP FastMCP Bridge.
---

# Clangd LSP Bridge & Semantic Code Intelligence Skill

## Overview
This skill guides the usage of the **Clangd LSP FastMCP Bridge** (`clangd_mcp_server.py`) for semantic C/C++ codebase analysis on the ESP32-S3 Board Support Package (BSP) and application firmware.

Instead of relying on regex or plain-text searches, the Clangd MCP bridge uses LLVM's `clangd` language server to navigate the real type system, expand macros, trace cross-references across source trees, and fetch real-time compiler diagnostics.

---

## Architecture & Configuration

* **MCP Server Script**: `c:/Users/Matt/Documents/GitHub/assets/tool_harness/mcp_servers/clangd_mcp_server.py`
* **Underlying Binary**: `C:\clang+llvm-18.1.8\bin\clangd.exe`
* **Global Config**: `C:\Users\Matt\.gemini\config\mcp_config.json`
* **Log Location**: `C:\Users\Matt\.mcp_logs\clangd_mcp_server.log`
* **Compilation Database**: Auto-discovers `compile_commands.json` in `build_dev/` or `build/` directories.

---

## Available MCP Tools & Best Practices

### 1. Jump to Definition / Declaration (`clangd_get_definition`)
Use when you need to find the exact definition or declaration of a function, struct, typedef, enum, or macro:
* **Arguments**:
  - `file_path`: Absolute or workspace-relative path (e.g. `components/h1os/src/sub_display.cpp`).
  - `line`: 1-indexed line number.
  - `character`: 1-indexed column position of the token.
* **Return**: Exact file path, line, and column of the target definition.

### 2. Find All References (`clangd_find_references`)
Use when refactoring APIs, modifying struct fields, or verifying call sites across the entire project:
* **Arguments**:
  - `file_path`: File path containing the symbol.
  - `line`: 1-indexed line number.
  - `character`: 1-indexed column position.
  - `include_declaration`: `true` to include original declaration.
* **Return**: List of all source and header locations referencing the symbol.

### 3. Hover Information & Type Inspection (`clangd_get_hover`)
Use to inspect inferred types, function signatures, docstrings, or evaluated preprocessor macro values:
* **Arguments**:
  - `file_path`: Target file.
  - `line`, `character`: 1-indexed token coordinates.
* **Return**: Markdown formatted type signature and documentation.

### 4. Workspace Symbol Search (`clangd_workspace_symbol`)
Use for fuzzy searching global symbols (functions, classes, structs, typedefs, macros) across all indexed files:
* **Arguments**:
  - `query`: Search substring or prefix (e.g. `bsp_sensors_` or `s_app_state`).
* **Return**: List of matching symbols with their container namespace and file:line locations.

### 5. Document Outline / Structure (`clangd_document_symbols`)
Use to generate an instant hierarchical outline of a source or header file:
* **Arguments**:
  - `file_path`: File to outline.
* **Return**: Tree view of classes, structs, member variables, functions, and enums with line numbers.

### 6. Compiler Diagnostics & Linter Warnings (`clangd_get_diagnostics`)
Use to retrieve real-time compiler warnings, syntax errors, and clang-tidy lints without running a full build:
* **Arguments**:
  - `file_path`: Source or header file.
* **Return**: List of `[ERROR]`, `[WARNING]`, and `[NOTE]` items with line/column coordinates.

### 7. Operational Status (`clangd_status`)
Use to check if the clangd subprocess is active, verify the active `compile_commands.json` path, and inspect open document count.

---

## Compilation Database Maintenance

When adding new source files or components to CMake:
1. Re-run project configuration or build in the active example (e.g. `idf.py reconfigure` or `idf.py build`).
2. CMake will update `build_dev/compile_commands.json`.
3. Clangd will automatically detect changes via `--background-index` and re-index the modified files.
