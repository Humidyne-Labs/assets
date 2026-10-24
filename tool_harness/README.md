# ESP32-S3 & H1OS Tool Harness

A specialized tool harness, agentic workflow rules, and Model Context Protocol (MCP) suite for AI-assisted embedded firmware development on **ESP32-S3**, **H1OS Operating System**, and **Waveshare 1.54" e-Paper**.

---

## 📁 Repository Directory Structure

```
tool_harness/
├── README.md                     # Complete user guide & tool harness documentation (this file)
├── sync_agents.bat               # Windows batch synchronization tool for .agents rules/skills
├── config/
│   └── mcp_config.json           # 3-Finger MCP server configuration for Antigravity / AI clients
├── tools/
│   └── test_gemini_api.py        # Fast Gemini API connection, latency & authentication tester
├── .agents/
│   ├── rules/                    # Authoritative execution rules & constraints (lowercase)
│   │   ├── arch.md               # Four-layer unidirectional architecture hierarchy
│   │   ├── coding.md             # Embedded C/C++ standards, hardware-first, pointer hygiene
│   │   ├── docs.md               # Documentation governance & living memory
│   │   ├── doxygen.md            # Doxygen formatting specifications
│   │   ├── gfm.md                # Strict GFM, CommonMark, and MathJax rules
│   │   ├── lexicon.md            # Engineering tone policy & prohibited phrasing
│   │   ├── lifecycle.md          # H1OS lifecycle, Flow A / Flow B, and sleep sequences
│   │   ├── lvgl.md               # LVGL 9 1-bit bilevel constraints (200x200, 188 DPI)
│   │   ├── master.md             # Master paired execution rules & two-strike protocol
│   │   ├── naming.md             # Gump naming rule & literal identifiers
│   │   └── science.md            # Empirical grounding & psychrometric invariants
│   └── skills/                   # On-demand operational skills
│       ├── clangd-lsp-mcp        # Semantic C/C++ code navigation via Clangd LSP
│       ├── esp-idf-codegen       # Conservative single-file C/C++ patching
│       ├── gfm                   # GFM authoring engine and MathJax specifications
│       ├── h1os-build            # Canonical ESP-IDF v6.1 profile build commands
│       ├── h1os-firmware-standards # 3-layer safety hierarchy & compiler hardening
│       ├── mcp-tool-harness      # 3-Finger MCP architecture & subagent orchestration
│       └── science-approval      # Interactive milestone approval & celebration widgets
└── _old/                         # Archived legacy MCP servers & tools (git-ignored)
```

---

## 🚀 The 3-Finger Architecture

The harness is engineered around a zero-hallucination, zero-token-burn **3-Finger Architecture** that replaces eager whole-repo LLM scanning with compiler-grade local tools:

```
                  ┌─────────────────────────────────────────┐
                  │          AI Agent (Antigravity)         │
                  └──────┬──────────────┬─────────────┬─────┘
                         │              │             │
        ┌────────────────┘              │             └────────────────┐
        ▼                               ▼                              ▼
  ┌───────────┐                   ┌───────────┐                  ┌───────────┐
  │  Finger 1 │                   │  Finger 2 │                  │  Finger 3 │
  │   Code    │                   │ Hardware  │                  │   Docs    │
  │ (clangd)  │                   │ (esp-idf) │                  │ (indexes) │
  └─────┬─────┘                   └─────┬─────┘                  └─────┬─────┘
        │                               │                              │
        ▼                               ▼                              ▼
 • Call hierarchies              • Native Ninja build           • Local Markdown
 • Exact definitions             • Direct flash via JTAG          datasheets
 • Reference lists               • Real-time monitor log        • Upstream Espressif
 • Struct layouts                  & panic backtraces             TRM & errata
```

### Finger 1: Semantic Code Intelligence (`clangd`)
* **Package:** `schuay/clangd-mcp` via `uvx --with "mcp<2" clangd-mcp`
* **Underlying Engine:** LLVM 18 (`C:\clang+llvm-18.1.8\bin\clangd.exe`) reading `compile_commands.json`
* **Tools:**
  - `get_callers`: Full incoming call tree for any function.
  - `get_callees`: Outgoing call hierarchy.
  - `get_definition`: Precise jump to declaration or definition.
  - `find_references`: Complete list of callers and usages.
  - `find_symbol`: Symbol name searches across the whole project.
  - `get_type_info`: Exact struct layout, size, and field types.

### Finger 2: Hardware & Build Execution (`esp-idf`)
* **Package:** Native ESP-IDF v6.1 CLI MCP server (`idf.py -C <project_dir> mcp-server`)
* **Environment:** Initialized via `C:\esp\v6.1\esp-idf\export.bat`
* **Capabilities:**
  - Fast, incremental Ninja compilation.
  - Direct flashing and hardware target interaction.
  - Live serial monitor captures (`monitor_read`, `monitor_boot`) directly in agent context without manual copy-paste.

### Finger 3: Documentation & Datasheets (`local-index` & `espressif-documentation`)
* **Local Indexer (`local-index`):** Runs `uvx code-index-mcp` on `H1OS/docs/` and local datasheet markdowns (`SHTC3`, `PCF85063A`, `ES8311`, `SSD1681`). Delivers pinpoint register tables and blueprint specs on demand.
* **Espressif Remote Docs (`espressif-documentation`):** Official TRM, hardware reference manuals, and silicon errata from `https://mcp.espressif.com/docs`.
* **Component Registry (`esp-component-registry`):** Official component search via `https://components.espressif.com/mcp`.

---

## ⚙️ Quick Start: Configuring MCP

To register the 3-Finger servers:

1. Open your global MCP configuration: `C:\Users\Matt\.gemini\config\mcp_config.json` (or active MCP client config).
2. Ensure the configuration matches [`config/mcp_config.json`](file:///c:/Users/Matt/Documents/GitHub/assets/tool_harness/config/mcp_config.json):

```json
{
  "mcpServers": {
    "clangd": {
      "command": "uvx",
      "args": [
        "--from", "git+https://github.com/schuay/clangd-mcp.git",
        "--with", "mcp<2",
        "clangd-mcp",
        "--clangd", "C:/clang+llvm-18.1.8/bin/clangd.exe",
        "--compile-commands-dir", "C:/Users/Matt/Documents/GitHub/H1OS/examples/H1OS/build_prod",
        "--workspace-dir", "C:/Users/Matt/Documents/GitHub/H1OS"
      ]
    },
    "esp-idf": {
      "command": "cmd.exe",
      "args": [
        "/c",
        "C:\\esp\\v6.1\\esp-idf\\export.bat > nul && idf.py -C C:/Users/Matt/Documents/GitHub/H1OS/examples/H1OS mcp-server"
      ]
    },
    "local-index": {
      "command": "uvx",
      "args": [
        "code-index-mcp",
        "--project-path", "C:/Users/Matt/Documents/GitHub/H1OS/docs"
      ]
    },
    "espressif-documentation": {
      "serverUrl": "https://mcp.espressif.com/docs"
    },
    "esp-component-registry": {
      "serverUrl": "https://components.espressif.com/mcp"
    }
  }
}
```

3. Restart your AI client session.

---

## 🎨 UI Development: Physical Constraints

All UI development for the **Waveshare 1.54" V2 e-Paper** is strictly governed by physical hardware constraints in [`.agents/rules/lvgl.md`](file:///c:/Users/Matt/Documents/GitHub/assets/tool_harness/.agents/rules/lvgl.md):

* **Resolution & Aspect:** 200 x 200 pixels (1:1 square, 188 DPI).
* **Color Depth:** 1-bit Monochrome (`LV_COLOR_FORMAT_I1`), pure black and white.
* **Opacity:** 100% (`LV_OPA_COVER`). Alpha blending and partial opacity are strictly prohibited.
* **Spatial Budget:** Header ($Y = 0..20\text{ px}$), Body ($Y = 22..148\text{ px}$), Footer ($Y = 150..200\text{ px}$).
* **Typography:** Minimum font height is **14 pixels** (smaller fonts bleed on e-Paper).
* **QR Codes:** Whole-factor integer scaling only ($\ge 3$ px per module).
* **Thread Boundary:** Wrap all mutations in `h1os_lvgl_lock()` / `h1os_lvgl_unlock()`.

---

## 🔄 Rules & Skills Synchronization

Run [`sync_agents.bat`](file:///c:/Users/Matt/Documents/GitHub/assets/tool_harness/sync_agents.bat) to push the `.agents` rules and skills bundle to `C:\Users\Matt\Documents\GitHub\H1OS`:

```cmd
sync_agents.bat
```
