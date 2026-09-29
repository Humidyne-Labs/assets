# ESP32-S3 BSP & LVGL 9 Tool Harness

A specialized tool harness and Model Context Protocol (MCP) suite for AI-assisted embedded firmware development on the **ESP32-S3 BSP**, **LVGL 9 UI rendering**, and repository documentation maintenance.

---

## 📁 Repository Directory Structure

```
tool_harness/
├── README.md                     # Complete user guide & tool documentation (this file)
├── MASTER_RULES.md               # Authoritative execution rules & mandates for AI agents
├── features.md                   # Feature specification & tool capability matrix
├── Tool_Harness_Plan.md          # Architecture & design documentation
├── config/
│   └── mcp_config.json           # Unified MCP server config for Antigravity / Claude Desktop
├── mcp_servers/
│   ├── bsp_mcp_server.py         # MCP server: ESP32-S3 BSP headers, sources & examples
│   ├── lvgl_mcp_server.py        # MCP server: LVGL 9 headers, API & reference examples
│   ├── lvgl_virt_mcp_server.py   # MCP server: Headless C compilation & PNG UI rendering
│   ├── lvgl_diff_mcp_server.py   # MCP server: SSIM visual diff & layout regression tester
│   ├── docs_mcp_server.py        # MCP server: Datasheets (PDF), markdown & text docs
│   ├── docgen_mcp_server.py      # MCP server: Doxygen + Moxygen API doc generation
│   ├── firmware_analyzer_mcp.py  # MCP server: Linker map memory footprint & symbol profiler
│   └── idf_build_mcp_server.py   # MCP server: ESP-IDF build, size & compilation harness
├── tools/
│   ├── generate_bsp_examples.py  # Gemini-driven BSP example generator & build validator
│   └── lvgl_headless/
│       ├── headless_harness.c    # C harness template for LVGL 9 UI rendering
│       └── stb_image_write.h     # Single-header PNG encoder
└── lvgl-9.6.0/                   # LVGL 9 source tree & reference examples
```

---

## 🚀 Quick Start: Registering MCP Servers

To enable all 8 MCP tool servers in your AI environment:

1. Open your MCP client configuration (e.g. Antigravity settings or `claude_desktop_config.json`).
2. Copy the content of [`config/mcp_config.json`](file:///c:/Users/Matt/Documents/GitHub/assets/tool_harness/config/mcp_config.json) into your active MCP configuration file.
3. Restart your AI client session.

---

## 🛠️ Complete MCP Tool Reference

### 1. ESP32-S3 BSP Server (`esp32-s3-bsp`)
Target path: `C:\Users\Matt\Documents\GitHub\esp32-s3_bsp`
- `list_bsp_headers_and_sources()`: Lists all headers, C sources, and examples in the BSP.
- `read_bsp_header(header_name)`: Reads specific BSP header file (e.g. `pinout.h`, `bsp_display.h`).
- `read_bsp_source(source_name)`: Reads specific BSP C implementation file (e.g. `bsp_display.c`, `bsp_i2c.c`).
- `search_bsp_api(query)`: Searches across BSP files for symbols, function prototypes, or GPIO macros.
- `list_bsp_examples()`: Lists available reference example files.
- `get_bsp_example_code(example_relative_path)`: Reads source code of a specific BSP example.

### 2. LVGL 9 Context Server (`lvgl-context`)
Target path: `./lvgl-9.6.0`
- `get_lvgl_version()`: Verifies exact major/minor version (`9.6.0`).
- `search_lvgl_api(function_or_type)`: Finds Doxygen docstrings and function prototypes for any LVGL 9 symbol.
- `get_widget_api(widget_name)`: Lists public methods and enums for widgets (`button`, `label`, `slider`, `chart`, etc.).
- `search_lvgl_examples(keyword)`: Finds official LVGL reference examples matching a keyword.
- `get_lvgl_example_code(example_relative_path)`: Reads full C source code of official LVGL examples.

### 3. LVGL Virtualization Server (`lvgl-virtualization`)
Host Compiler: MSVC (`cl.exe` via `vcvars64.bat`) or GCC
- `render_ui_snapshot(c_ui_code, width=200, height=200)`: Compiles C UI setup code into a native host binary, executes LVGL 9 rendering in memory, and returns a base64-encoded 200x200 PNG snapshot for visual inspection.

### 4. LVGL Visual Diff & SSIM Server (`lvgl-diff`)
- `compare_ui_snapshots(baseline_code, candidate_code, width=200, height=200)`: Renders baseline and candidate UI snippets, computes pixel-by-pixel delta and SSIM percentage, and outputs a base64-encoded visual diff heatmap (highlighting changes in red/magenta).

### 5. Project Docs & Datasheet Server (`project-docs`)
Target paths: `./docs` and `esp32-s3_bsp/docs` (extendable via `EXTRA_DOCS_DIRS` / `ASSETS_DIRS` or dynamic tools)
- `list_available_docs()`: Lists all PDF datasheets, Markdown notes, and schematics across all registered asset directories.
- `search_docs_text(keyword, max_results=10)`: Searches text in Markdown files and page-by-page in PDFs across all asset roots.
- `read_doc_file(relative_path)`: Reads full Markdown or text documentation files.
- `read_pdf_page(pdf_relative_path, page_number)`: Reads full text content of a specific PDF page.
- `render_pdf_page_to_image(pdf_relative_path, page_number, dpi=144)`: Renders a PDF page (schematics, pinout table) as a high-res base64 PNG image.
- `add_asset_directory(directory_path)`: Dynamically registers a new asset root directory at runtime (persisted in `config/extra_asset_dirs.json`).
- `list_asset_directories()`: Lists all active asset search directories (default, environment variable, or dynamically registered).
- `remove_asset_directory(directory_path)`: Removes a dynamically registered asset directory.

### 6. Doxygen & Moxygen Doc Generator (`docgen`)
Requires: Doxygen (`C:\Program Files\doxygen\bin\doxygen.exe`) and Moxygen (`npm install -g moxygen`)
- `generate_api_docs(mode="full")`:
  - `mode="full"`: Generates single-page `docs/api.md` matching `tasks.json`.
  - `mode="multi"`: Generates multi-page `docs/api/*.md` categorized by group.
  - `mode="doxygen_only"`: Runs `doxygen Doxyfile`.
  - `mode="moxygen_only"`: Runs Moxygen conversion on existing XML.
- `clean_generated_docs()`: Removes `docs/doxygen/`, `docs/api.md`, and `docs/api/`.

### 7. Firmware Memory Analyzer Server (`firmware-analyzer`)
- `get_memory_usage_summary(project_path="")`: Parses build map file to report DRAM, IRAM, DIRAM, PSRAM, and Flash byte counts and percentages.
- `analyze_top_symbols(project_path="", limit=25)`: Identifies the largest functions and static variables consuming Flash or RAM.

### 8. ESP-IDF Build Harness Server (`idf-build`)
Requires: ESP-IDF environment (`idf.py`)
Default BSP Build Target: `C:\Users\Matt\Documents\GitHub\esp32-s3_bsp\examples\Peripherals_Test_Suite`
- `trigger_idf_build(project_path="", target="esp32s3")`:
  - For BSP testing: Run against `examples/Peripherals_Test_Suite` (default target).
  - For Main User Application: Pass `project_path="C:/path/to/main_app"`.
  - Returns pass/fail status with line-numbered compiler error diagnostics.
- `get_idf_size(project_path="")`: Runs `idf.py size` and returns component size breakdown.
- `reconfigure_idf_project(project_path="")`: Runs `idf.py reconfigure`.

---

## ⚡ Generating BSP Examples with Google GenAI SDK

To auto-generate unit-level reference examples for all headers in `esp32-s3_bsp/components/esp32-s3_bsp/include/bsp` (with matching C implementation context, model selection, and token usage tracking):

```bash
# Set environment API key
set GEMINI_API_KEY=your_api_key_here

# 1. List available Gemini models
python tools/generate_bsp_examples.py --list-models

# 2. Batch generate and compile examples with token usage statistics
python tools/generate_bsp_examples.py \
    --headers-dir "C:\Users\Matt\Documents\GitHub\esp32-s3_bsp\components\esp32-s3_bsp\include\bsp" \
    --sources-dir "C:\Users\Matt\Documents\GitHub\esp32-s3_bsp\components\esp32-s3_bsp\src" \
    --output-dir "C:\Users\Matt\Documents\GitHub\esp32-s3_bsp\examples" \
    --model "gemini-2.5-flash" \
    --show-usage \
    --build-cmd "idf.py build"

# 3. Alternative: Use Google Cloud Vertex AI mode
python tools/generate_bsp_examples.py --use-vertex --project "your-gcp-project-id" --show-usage
```

---

## 📋 Typical AI Workflow Cycle

1. **BSP Subsystem Development**:
   - Agent reads `MASTER_RULES.md` and uses `search_bsp_api("pinout.h")` to verify peripheral pins.
   - Agent writes driver code adhering to header prototypes.
   - Agent calls `trigger_idf_build()` to verify compilation and self-correct on any errors.
   - Agent calls `get_memory_usage_summary()` to check DRAM/Flash footprints.

2. **LVGL UI Design & Layout Verification**:
   - Agent searches LVGL v9 widget signatures using `get_widget_api("button")`.
   - Agent calls `render_ui_snapshot()` to generate a visual 200x200 PNG layout snapshot.
   - Agent calls `compare_ui_snapshots()` to verify visual diff against baseline UI.

3. **Documentation Maintenance**:
   - Agent updates Doxygen comments in header files.
   - Agent calls `generate_api_docs(mode="full")` to rebuild `docs/api.md`.
