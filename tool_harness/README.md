# ESP32-S3 & H1OS Tool Harness

A specialized tool harness and Model Context Protocol (MCP) suite for AI-assisted embedded firmware development on **ESP32-S3**, **H1OS Operating System**, and **Waveshare 1.54" e-Paper**.

---

## 📁 Repository Directory Structure

```
tool_harness/
├── README.md                     # Complete user guide & tool harness documentation (this file)
├── sync_agents.bat               # Windows batch synchronization tool for .agents rules/skills
├── config/
│   └── mcp_config.json           # Unified MCP server config for Antigravity / Claude Desktop
├── mcp_servers/
│   ├── clangd_mcp_server.py      # MCP server: Clangd semantic C/C++ navigation & diagnostics
│   ├── firmware_analyzer_mcp.py  # MCP server: Linker map memory footprint & symbol profiler
│   └── idf_build_mcp_server.py   # MCP server: ESP-IDF build, size & compilation harness
├── tools/
│   ├── generate_bsp_examples.py     # Gemini-driven BSP example generator & build validator
│   ├── rebuild_all_examples.py     # Batch ESP-IDF example rebuilder & master build log generator
│   ├── open_examples_in_notepadpp.py# Opens all example main.c files in Notepad++ tabs
│   ├── open_examples_in_notepadpp.bat# Windows batch launcher for Notepad++ review
│   └── test_gemini_api.py           # Fast Gemini API connection, latency & authentication tester
├── .agents/
│   ├── rules/                    # Authoritative execution rules & constraints
│   │   ├── arch.md               # Four-layer unidirectional architecture hierarchy
│   │   ├── coding.md             # Embedded C/C++ standards, hardware-first, pointer hygiene
│   │   ├── docs.md               # Documentation governance & living memory
│   │   ├── doxygen.md            # Doxygen formatting specifications
│   │   ├── gfm.md                # Strict GFM, CommonMark, and MathJax rules
│   │   ├── graphify.md           # Graphify knowledge graph rules
│   │   ├── lexicon.md            # Engineering tone policy & prohibited phrasing
│   │   ├── lifecycle.md          # H1OS lifecycle, Flow A / Flow B, and sleep sequences
│   │   ├── lvgl.md               # LVGL 9 1-bit bilevel constraints (200x200, 188 DPI)
│   │   ├── master.md             # Master paired execution rules & two-strike protocol
│   │   ├── naming.md             # Gump naming rule & literal identifiers
│   │   └── science.md            # Empirical grounding & psychrometric invariants
│   ├── skills/                   # On-demand operational skills
│   │   ├── clangd-lsp-mcp        # Semantic C/C++ code navigation via Clangd
│   │   ├── esp-idf-codegen       # Conservative single-file C/C++ patching
│   │   ├── gfm                   # GFM authoring engine and MathJax specifications
│   │   ├── h1os-build            # Canonical ESP-IDF v6.1 profile build commands
│   │   ├── h1os-firmware-standards # 3-layer safety hierarchy & compiler hardening
│   │   ├── mcp-tool-harness      # Tool harness operations & subagent delegation
│   │   └── science-approval      # Interactive milestone approval & celebration widgets
│   └── workflows/
│       └── graphify.md           # Knowledge graph pipeline workflow
└── _old/                         # Archived legacy MCP servers & tools (git-ignored)
```

---

## 🚀 Quick Start: Registering MCP Servers

To enable the active MCP tool servers in your AI environment:

1. Open your MCP client configuration (e.g. `~/.gemini/config/mcp_config.json` or `claude_desktop_config.json`).
2. Copy the content of [`config/mcp_config.json`](file:///c:/Users/Matt/Documents/GitHub/assets/tool_harness/config/mcp_config.json) into your active MCP configuration file.
3. Restart your AI client session.

---

## 🛠️ Complete MCP Tool Reference

### 1. Clangd Semantic Code Navigation (`clangd`)
Bridge: Clangd FastMCP LSP Server (`C:\clang+llvm-18.1.8\bin\clangd.exe`)
- `clangd_get_definition(file_path, line, character)`: Jumps directly to symbol definitions.
- `clangd_find_references(file_path, line, character)`: Finds all call sites and references across the codebase.
- `clangd_get_hover(file_path, line, character)`: Retrieves exact type signatures, docstrings, and struct layouts.
- `clangd_workspace_symbol(query)`: Searches for functions, enums, and types across the entire compilation database.
- `clangd_get_diagnostics(file_path)`: Captures compiler-grade diagnostics and header inclusion errors.

### 2. Firmware Memory Analyzer Server (`firmware-analyzer`)
- `get_memory_usage_summary(project_path="")`: Parses linker map files to report DRAM, IRAM, DIRAM, PSRAM, and Flash consumption.
- `analyze_top_symbols(project_path="", limit=25)`: Identifies the largest functions and static variables consuming Flash or RAM.

### 3. ESP-IDF Build Harness Server (`idf-build`)
Requires: ESP-IDF environment (`C:\esp\v6.1\esp-idf`)
Default target: `C:\Users\Matt\Documents\GitHub\H1OS\examples\H1OS`
- `trigger_idf_build(project_path="", target="esp32s3")`: Executes clean Ninja compilation and returns line-numbered diagnostics.
- `get_idf_size(project_path="")`: Runs `idf.py size` and returns component size breakdown.
- `reconfigure_idf_project(project_path="")`: Runs `idf.py reconfigure`.

### 4. Knowledge Graph Server (`graphify`)
- Serves knowledge graphs generated by Graphify to navigate dependencies and code communities.

---

## 🎨 UI Development: Constraint-Driven Specification

Host-compiled UI snapshot runners and virtualization MCP tools have been retired. All UI development for the **Waveshare 1.54" V2 e-Paper** is strictly evaluated against physical hardware constraints detailed in [`.agents/rules/lvgl.md`](file:///c:/Users/Matt/Documents/GitHub/assets/tool_harness/.agents/rules/lvgl.md):

* **Resolution & Aspect:** 200 x 200 pixels (1:1 square, 188 DPI).
* **Color Depth:** 1-bit Monochrome (`LV_COLOR_FORMAT_I1`), pure black and white.
* **Opacity:** 100% (`LV_OPA_COVER`). Alpha blending and partial opacity are strictly prohibited.
* **Spatial Budget:** Header ($Y = 0..20\text{ px}$), Body ($Y = 22..148\text{ px}$), Footer ($Y = 150..200\text{ px}$).
* **Typography:** Minimum font height is **14 pixels** (smaller fonts bleed on e-Paper).
* **QR Codes:** Whole-factor integer scaling only ($\ge 3$ px per module).
* **Thread Boundary:** Wrap all mutations in `h1os_lvgl_lock()` / `h1os_lvgl_unlock()`.

---

## 🔄 Rules & Skills Synchronization

Use [`sync_agents.bat`](file:///c:/Users/Matt/Documents/GitHub/assets/tool_harness/sync_agents.bat) to push updated rules and skills to dependent repositories:
- `C:\Users\Matt\Documents\GitHub\H1OS`
