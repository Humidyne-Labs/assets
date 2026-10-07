# Master Agent Execution Rules: ESP32-S3 BSP & LVGL 9 Development

## Core Directives & Mandates
1. **Zero Guesswork Policy**: NEVER guess or extrapolate function signatures, enums, peripheral pins, or configuration structs.
2. **Authoritative Sources First**: 
   - For BSP: Inspect `pinout.h` (`esp32-s3_bsp/components/esp32-s3_bsp/include/bsp/pinout.h`), module headers (`read_bsp_header`), and implementation source files (`read_bsp_source`) before writing calls.
   - For LVGL 9: Use `get_lvgl_version` and `search_lvgl_api` before writing layout or widget code.
3. **Strict Error Checking**: Every ESP-IDF / BSP API call returning `esp_err_t` MUST be wrapped in `ESP_ERROR_CHECK()` or handled explicitly.
4. **Header & Source Discovery Protocol**:
   - Phase 1: Read target header files (`read_bsp_header`) and source files (`read_bsp_source`) to extract function prototypes, initialization sequences, and parameter types.
   - Phase 2: Formulate Implementation Plan artifact (initialization order: Power -> Bus -> Driver -> Peripheral).
   - Phase 3: Write concise, focused C code (< 200 lines per module).
   - Phase 4: Validate via compiler diagnostics (`trigger_idf_build` or MSVC/GCC headless runner).

---

## Subagent Spawning & Parallel Delegation Directives
1. **Subagent Spawning Mandate**: Primary agent (Antigravity) SHOULD proactively spawn subagents using `invoke_subagent` whenever:
   - **Research & Exploration**: Deep codebase searches, multi-file inspections, or reading large datasheet PDFs require multiple lookup steps (delegate to `research` subagent).
   - **Parallel Build & Test Tasks**: Independent tasks can run concurrently (e.g. one subagent running ESP-IDF build verification while another performs LVGL UI visual diff regression or documentation updates).
   - **Multi-Module Refactoring**: Complex refactoring spans decoupled components or BSP modules.
2. **Subagent Execution Protocol**:
   - Provide clear, actionable prompts to spawned subagents.
   - Do NOT poll subagents in loops; rely on background notification messages.
   - Synthesize subagent findings and report conclusions cleanly to the user.

---

## ESP32-S3 BSP Development & Build Environment Standards
- **Source Paths**:
  - Headers: `C:\Users\Matt\Documents\GitHub\esp32-s3_bsp\components\esp32-s3_bsp\include\bsp\`
  - Source: `C:\Users\Matt\Documents\GitHub\esp32-s3_bsp\components\esp32-s3_bsp\src\`
  - Test/Build Target: `C:\Users\Matt\Documents\GitHub\esp32-s3_bsp\examples\Peripherals_Test_Suite\`
- **ESP-IDF Environment Auto-Initialization**:
  - Before executing builds, the server/agent MUST ensure `init_idf_environment` has run to export `IDF_PATH`, toolchains (`xtensa-esp32s3-elf-gcc`, `ninja`, `cmake`), and Python virtualenv variables into `os.environ`.
- **Build Isolation Directives**:
  - **BSP Testing & Validation**: ONLY run builds inside the `examples/Peripherals_Test_Suite` project (`esp32-s3_bsp/examples/Peripherals_Test_Suite`). Do NOT trigger builds directly at the BSP repository root.
  - **Main User Application**: Run builds directly inside the isolated main application project directory.
- **Pin Definitions**:
  - Peripheral pin mappings are fixed and defined in `pinout.h`. Always reference `bsp/pinout.h` macros instead of hardcoding GPIO numbers.
- **Initialization Order**:
  1. Power rails / PMIC enable (`bsp_power_*`)
  2. Peripheral bus (I2C / SPI / I2S / SDMMC)
  3. Device driver handle creation
  4. Application tasks / queues

---

## LVGL v9 UI Design & Virtualization Guidelines
- **Version Compliance**: Target LVGL v9 (v9.6.0 / v9.0.6). Do NOT mix v8 API functions (e.g. use `lv_button_create` instead of `lv_btn_create`, `lv_screen_active()` instead of `lv_scr_act()`).
- **Display Geometry & Format**:
  - Resolution: Default 200x200 (1.54" display target).
  - DPI: 188 DPI.
  - Color format: 1-bit monochrome (`LV_COLOR_FORMAT_I1`) or 32-bit `LV_COLOR_FORMAT_ARGB8888` depending on target mode.
- **Headless UI Snapshot Verification**:
  - Before committing UI code to firmware, pass candidate setup functions to `render_ui_snapshot` via the LVGL Virtualization MCP tool.
  - Visually inspect rendered base64 PNG output to confirm proper widget alignment, font sizing, padding, and border bounds.
- **Skill Reference**: Load and follow [.agents/skills/lvgl9-ui-virtualization/SKILL.md](file:///c:/Users/Matt/Documents/GitHub/assets/tool_harness/.agents/skills/lvgl9-ui-virtualization/SKILL.md) for pre-tested C code patterns (Cards, Buttons, Progress Arcs, Flex Containers) and tool execution recipes.

---

## MCP Server Logging & Transport Integrity
- **Physical Log Oversight**: All Python MCP servers MUST save physical logs in `Path.home() / ".mcp_logs" / "<server_name>.log"` (`C:\Users\Matt\.mcp_logs\`) for review by oversight.
- **Stdio Transport Purity**: All log handlers MUST write ONLY to physical log files and `sys.stderr`. `sys.stdout` MUST remain 100% pure JSON-RPC transport stream.

---

## Documentation & Datasheet Access Protocols
- Search datasheets and design notes using `search_docs_text` before implementing custom register read/writes or timing requirements.
- Use `render_pdf_page_to_image` to inspect visual pinout diagrams, schematic pages, or hardware timing charts when text parsing is ambiguous.

---

## Compiler Diagnostic & Self-Correction Loop
- Never declare success without compilation verification.
- If `trigger_idf_build` or the MSVC/GCC headless compiler returns errors, read the exact compiler diagnostics and fix signatures to match declared headers.
