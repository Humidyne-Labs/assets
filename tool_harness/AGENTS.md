# H1OS Master Engineering Specification & Agent Invariants

This file constitutes the authoritative, always-active engineering and behavioral specification for autonomous agents and firmware developers working on **H1OS** on ESP32-S3.

---

## 1. Core Directives & Architectural Invariants

1. **Zero Guesswork Policy (Code & Silicon):** NEVER guess or extrapolate function signatures, struct members, enums, peripheral pins, or configuration options. Use compiler-backed semantic code intelligence (`get_definition`, `find_references`, `get_type_info`, `get_callers`, `get_callees`) and authoritative headers (`h1os.h`, `hal_types.h`, `sub_*.h`, `orch_*.h`).
2. **Empirical Ground Truth & No Made-Up Numbers ("Sherlock Ohming vs. Fact"):**
   - **Never Fabricate Metrics:** Ballpark, baseline, or operational figures (e.g., deep sleep current, wake latency, quiescent power draw, thermal conduction rates) MUST be explicitly cited from an authoritative manufacturer datasheet or verified on physical test instruments (oscilloscope, DMM, power profiler). If a figure was neither measured on physical hardware nor read directly in official documentation, it is **NOT a valid engineering metric**. Presenting unmeasured estimates as factual quantities is strictly prohibited.
   - **Hypothesis vs. Fact Boundary ("Sherlock Ohming"):** Observed circuit behavior may strongly support an electrical deduction (e.g., parasitic reverse-powering via unpowered ESD clamping diodes, open-drain bus leakage), but without instrumented oscilloscope verification or explicit schematic evidence, it remains a **hypothesis**, NOT established fact. Deducing physical mechanisms is valuable engineering, but it MUST be explicitly labeled as an *unverified hypothesis / speculative deduction*, never asserted as empirical ground truth.
3. **Four-Layer Unidirectional Boundary Hierarchy:**
   - **Layer 1: HAL (`hal_*`)**: Stateless primitives directly manipulating registers and ESP-IDF peripheral drivers. Zero application state, zero psychrometric math.
   - **Layer 2: Peripheral Subsystems (`sub_*`)**: Encapsulated device drivers (`sub_display`, `sub_sensor`, `sub_rtc`, `sub_power`, `sub_audio`, `sub_nvs`, `sub_sdcard`). Layer 2 subsystems **NEVER** communicate directly with one another.
   - **Layer 3: Orchestrator & ULP (`orch_*`)**: Flow arbiter (Flow A vs Flow B), persistent RTC state (`orch_state`), thermodynamic invariant math (`orch_math`), and the ULP-RISC-V coprocessor monitor.
   - **Layer 4: Application Lifecycle (`h1os_*`)**: Declarative lifecycle (`h1os_start`, `h1os_sleep`), Core 1 LVGL v9 UI engine (`h1os_lvgl.h`), time sync (`h1os_time.h`).
   - *Hierarchy Rule:* Upper layers call lower layers; lower layers **NEVER** call upper layers or cross-talk.
4. **Hardware-First Mandate ("Use the Hardware"):**
   - **Dual-Core Affinity:** Core 0 handles system, radio, and headless Flow A bursts; Core 1 is dedicated strictly to the LVGL v9 presentation task.
   - **Power Latching:** `BAT_CTRL` (GPIO 17) is asserted in `h1os_boot_hook` within 25 ms and held across deep sleep via RTC pad hold.
   - **Zero-Heat Sensing:** Never poll the SHTC3 during active CPU operation. SHTC3 sampling is restricted to headless Flow A sample bursts (<10 ms at 80 MHz) or the ULP coprocessor to prevent PCB self-heating bias.
   - **Never Busy-Wait:** Polling in `while()` loops during idle states is prohibited; block on FreeRTOS notifications, semaphores, or hardware interrupts.
5. **Compiler Diagnostics & Two-Strike Resolution Protocol:**
   - Always verify compilation with the canonical ESP-IDF profile (`C:\Espressif\tools\Microsoft.v6.1.PowerShell_profile.ps1`).
   - If a build fails, isolate the exact diagnostic line and propose one targeted fix. If it fails a second time, **STOP IMMEDIATELY**, state the diagnostic verbatim, and request confirmation.

---

## 2. Engineering Nomenclature & Technical Lexicon Policy

Strictly adhere to professional **Embedded Systems Hardware and Software Engineering** standards. Informal jargon, military slang, pop-culture metaphors, and ideological commentary are strictly prohibited.

### Enforcement Scope & Zero-Judgment Boundary
1. **Mandatory Repository Scope:** This policy applies unconditionally to all content stored, persisted, or committed to the repository—including source code (`.c`, `.h`), inline comments, git commit messages, git tags, pull request descriptions, documentation (`docs/`, `*.md`), and test ledgers.
2. **Interactive Chat Exemption:** Conversational brainstorming, rapid hypothesis exploration, casual dialog, and informal banter in interactive user chat are exempt from strict lexicon gating (zero-judgment zone). However, any text written to disk, committed to Git, or added as a project artifact MUST strictly conform to the engineering lexicon.

### Required Engineering Vocabulary Mapping
| Prohibited Jargon / Slang | Required Engineering Term | Technical Context |
| :--- | :--- | :--- |
| **stand-down / stand down** | **sleep transition / power down / suspend** | Transitioning the SoC or peripherals into deep sleep or low-power state. |
| **sentinel / sentry / bouncer** | **monitor / supervisor / watchdog** | Coprocessor, task, or interrupt handler overseeing events or state. |
| **tripwire** | **threshold / limit trigger / brownout detector** | Voltage, thermal, or timer boundary triggering a state transition. |
| **sprint / sortie / mission** | **sample / sample burst / measurement pass** | Ultra-fast sensor acquisition pulse before thermal conduction. |
| **recon / reconnaissance** | **probing / polling / scanning / telemetry query** | Checking bus lines, I2C discovery, or sensor interrogation. |
| **payload** | **data buffer / telemetry frame / sample packet** | Sensor reading struct, ring buffer element, or network transmission. |
| **scaffold purge / purge** | **removal / erase / clear / refactoring / pruning** | Deleting obsolete code, wiping configuration, or clearing caches. |
| **neutralize** | **clear / discharge / de-energize / reset** | Clearing display RAM, resetting DC bias, or de-asserting GPIO rails. |
| **kill / terminate (non-POSIX)**| **halt / disable / abort / power cut** | Graceful shutdown or gate de-assertion. |
| **fallback / fall back** | **default / recovery mode / safe state** | Fault handling logic. |
| **doctrine / dogma** | **standard / architecture / principle / specification**| Non-technical, cultish, or ideological framing. |
| **bones / muscle / vanity** | **contracts / subsystems / presentation layer** | Anatomical slang / informal construction metaphors. |

### The Tone & Professionalism Clause
1. **Eliminate Hostile / Adversarial Phrasing:** Prohibit violent idioms (*"nuke"*, *"blow away"*, *"destroy"*, *"wipe out"*, *"strangle"*). Use standard engineering terms (*"reset"*, *"erase"*, *"clear"*, *"abort"*).
2. **No Manifesto-Style Prose:** Maintain a neutral, matter-of-fact, dispassionate tone focused purely on empirical measurement, circuit schematics, system architecture, and API contracts.
3. **No Pop-Culture or Whimsical Lore:** Prohibit superheroes, movie quotes, religious/theological terms, and fantasy metaphors (*"magic"*, *"pixie dust"*, *"dragons"*). Note: *daemon* is permitted strictly in POSIX service context.
4. **No Ordnance or Ordnance Disposal Terminology:** Strictly prohibit all terms and analogies related to military ordnance, demolition, or ordnance disposal.
5. **No Pharmacological References:** Strictly prohibit all pharmacological, medicinal, and toxicological references.

---

## 3. Application Lifecycle & Dual Execution Flows

`h1os_start()` (or `h1os_init()`) is the **MANDATORY single entry point** and lifecycle orchestrator. All state transitions, flow arbitration, and sleep transitions must be driven through `h1os_lifecycle_t`.

### Dual Execution Flows
1. **Flow A (Headless Telemetry Burst):**
   - Execution: Core 0 fast RTC wake stub (`orch_wake_stub`) at 80 MHz (<10 ms, target <4 ms). Core 1 gated off, Flash unpowered.
   - Execution Sequence: Wake on periodic RTC timer $\rightarrow$ sample SHTC3 and MCU die TSENS $\rightarrow$ compute fixed-point psychrometric invariants (Magnus $e$, $T_{\text{dew}}$, EWMA) $\rightarrow$ commit to RTC Slow Memory (`orch_state`) $\rightarrow$ return to deep sleep.
   - Thermal Invariant: Zero PCB self-heating. High-power rails remain unpowered.
2. **Flow B (Interactive User Session):**
   - Execution: Dual-core FreeRTOS SMP with 240 MHz Turbo lock during screen blits, dropping via DFS to 80 MHz during idle interaction.
   - Trigger: User button press (`GPIO 0` / `GPIO 18`) or hardware RTC alarm (`GPIO 5`).
   - Execution Sequence: Bootloader latches power $\rightarrow$ boot FreeRTOS $\rightarrow$ spawn Core 1 LVGL v9 task $\rightarrow$ dispatch `on_wake(ctx)` $\rightarrow$ run interactive session $\rightarrow$ track 30s inactivity timer $\rightarrow$ initiate coordinated sleep transition sequence.

### Deterministic Sleep Transition Sequence
1. Invoke pre-sleep application callback (`on_sleep`).
2. Signal Core 1 LVGL presentation task to drain buffers and halt cleanly.
3. Poll SSD1681 display `BUSY` signal release at 80 MHz.
4. Wait mandatory **250 ms physical settling delay** for electrophoretic ink microcapsules.
5. If frame marked dirty, commit 5,000-byte 1-bit buffer to SPI Flash partition `epd_frame`.
6. Suspend audio codec (`sub_audio` software standby) and isolate I2C/SPI buses.
7. Configure sleep triggers (ULP monitor, RTC timer, button edge wake pads `GPIO 0` / `GPIO 18`).
8. Assert RTC pad hold on `BAT_CTRL` (GPIO 17) and enter hardware deep sleep (`esp_deep_sleep_start()`).

---

## 4. LVGL v9 Bilevel UI & E-Paper Constraints

All UI code targets the Waveshare ESP32-S3 ePaper 1.54" V2 panel (SSD1681 driver):
* **Geometry:** 200 x 200 pixels (1:1 square aspect ratio), 188 DPI.
* **Usable Margins & Maximum Width:** $X = 6\text{ px}$ to $194\text{ px}$. Maximum string width is strictly **$\le 188.0\text{ px}$**.
* **Color Depth:** 1-bit Monochrome (`LV_COLOR_FORMAT_I1`), pure black and pure white. Draw buffer: exactly 5,000 bytes.
* **100% Opacity Mandate:** Opacity must always be `LV_OPA_COVER` (100%). Alpha blending, partial opacity (`LV_OPA_50`), and pseudo-random dithering are strictly prohibited.
* **Typography:** Minimum font height is **14 pixels** (e.g. `H1OS_FONT_14`). Fonts <14 px blur into illegibility during differential updates.
* **Proportional Font Rules:** Montserrat font metrics are proportional with 4-bit fractional advance widths and class kerning. Never use multiple spaces for alignment; use dual column labels or single-space padding.
* **Layout Grid (200 px Total):** Header ($Y = 0..20\text{ px}$ with 1 px bottom border), Body ($Y = 22..148\text{ px}$), Footer ($Y = 150..200\text{ px}$).
* **Thread Safety:** Wrap all UI mutations in `h1os_lvgl_lock()` / `h1os_lvgl_unlock()`.
* **Font Validation Tools:** Verify all strings against layout boundaries using `python tools/check_string_width.py --audit-screens` and CSV metrics in `tools/fonts/`.

---

## 5. Embedded C/C++ Coding Standards & Safety

1. **Memory Safety & Pointer Hygiene:**
   - Initialize all pointers to `NULL`. Set pointers to `NULL` immediately after `free()`.
   - Validate pointers at all subsystem boundaries (`if (ptr == NULL) return ESP_ERR_INVALID_ARG;`).
   - Check return values on all ESP-IDF and FreeRTOS calls (`ESP_ERROR_CHECK()` or deterministic propagation).
2. **Single-Responsibility Functions:** If a function performs more than one distinct task, split it into 2 or 3 smaller helper functions. Modularity and testability strictly supersede negligible call overhead.
3. **The Gump Naming Rule:** Name identifiers literally by what they physically do:
   `[Layer/Module Prefix] _ [Physical Target/Peripheral] _ [Literal Action]`
   *(e.g., `orch_flow_sample_sensors()`, `hal_io_release_power_latch()`, `sub_display_clear_to_white()`)*.
4. **Visual Block Alignment ("Pretty Code"):** Format struct definitions, constants, and function argument lists into clean, columnar blocks for rapid vertical scanning.

---

## 6. Empirical Science & Mathematical Grounding

* **Math Precedes Code:** Never implement heuristic curve-fitting or synthetic sensor scaling when physical governing equations exist.
* **August-Roche-Magnus Psychrometrics:** True water vapor pressure ($e$) and dew point ($T_{\text{dew}}$) are thermodynamic invariants unaffected by PCB self-heating. Compute using August-Roche-Magnus formulations.
* **LiPo State of Charge (SoC):** Compute battery percentage using the empirical 13-point Open-Circuit Voltage (OCV) lookup curve rather than linear voltage approximations.
* **Integer Fixed-Point Math:** Because the ULP-RISC-V coprocessor lacks hardware FPU, compute in centi-degrees ($1^\circ\text{C} = 100$) and centi-percent RH.

---

## 7. Release Governance & Pre-Merge Checklist

Direct commits to `main` are strictly prohibited. Before merging any branch into `main`:
1. **Zero-Warning Build:** Verify compilation passes with 0 warnings/errors via `idf.py -B build_dev build`.
2. **Mandatory `sdkconfig` Removal Invariant:** Always remove root `examples/H1OS/sdkconfig` and `sdkconfig.old` before reconfiguring or switching presets (`--preset dev` vs `--preset prod`).
3. **Synchronize 4 Version Strings:** Update `h1os_version.h`, `idf_component.yml`, `README.md`, and `CHANGELOG.md`.
4. **Regenerate API Documentation:** Run `doxygen Doxyfile; moxygen --flavor github -a -o docs/api.md docs/doxygen/xml`.
5. **Touch Changelog:** Record changes in `CHANGELOG.md` under Keep a Changelog categories (`Added`, `Changed`, `Fixed & Hardened`, `Removed`).
6. **Tag Release:** Push annotated tag `vX.Y.Z-tag` to remote.


---

## 8. Documentation Governance, Living Memory & Architecture Index ("Documentation is Law")

> *"Documentation is memory and history reflective of progress and hard lessons learned. We document the weeds so we can find flowers next time."*

### The Documentation Laws
1. **Synchronous Updates:** Documentation is never an afterthought. When APIs, state machines, hardware pinouts, or peripheral configurations change, corresponding documentation in [`docs/`](docs/) MUST be updated in the exact same commit.
2. **Failure Analysis & Living Errata:** Document design dead-ends, silicon hardware limitations, and discarded workarounds in [`docs/architecture/C2_lessons_learned.md`](docs/architecture/C2_lessons_learned.md) and [`ERRATA.md`](ERRATA.md). Never erase historical technical rationale—distill it so future engineers avoid repeating discarded experiments.
3. **Open-Source Hardware (OSHW) & Attribution:** Maintain clear board schematics, pinout tables ([`docs/pinout.md`](docs/pinout.md)), and appropriate SPDX license identifiers (`SPDX-License-Identifier: MIT` or `CC-BY-4.0`) across all code and documentation files. Always credit upstream algorithms, font authors, and drivers.

### Authoritative Architecture Index ([`docs/architecture/`](docs/architecture/))
Cross-reference the canonical system blueprint documents before modifying architecture:

| Category | Authoritative Architecture Document | Core Scope |
| :--- | :--- | :--- |
| **System Governance** | [`A0_system_governance.md`](docs/architecture/A0_system_governance.md) | Architectural standards, module ownership, and layer compliance. |
| **Master Blueprint** | [`A1_master_blueprint.md`](docs/architecture/A1_master_blueprint.md) | High-level system topology and hardware block diagrams. |
| **HAL Layer** | [`A2_hal.md`](docs/architecture/A2_hal.md) | Stateless Layer 1 drivers, register maps, and peripheral abstractions. |
| **Power & Sleep** | [`A3_gpio_hold_and_sleep.md`](docs/architecture/A3_gpio_hold_and_sleep.md) | RTC pad hold states, latching circuit, and power rail sequencing. |
| **Subsystems** | [`A4_subsystems.md`](docs/architecture/A4_subsystems.md) | Layer 2 encapsulated drivers (display, audio, sensor, RTC, NVS, SD). |
| **Orchestrator** | [`A5_orchestrator.md`](docs/architecture/A5_orchestrator.md) | Layer 3 flow arbiter (Flow A vs Flow B) and RTC Slow Memory ring buffer. |
| **ULP Coprocessor** | [`A6_ulp_coprocessor.md`](docs/architecture/A6_ulp_coprocessor.md) | ULP-RISC-V environmental monitor, memory layout, and sleep gating. |
| **Psychrometrics** | [`A7_sensor_psychrometrics.md`](docs/architecture/A7_sensor_psychrometrics.md) | Thermodynamic invariants, August-Roche-Magnus math, and TSENS. |
| **Battery & Power** | [`A8_battery_and_power_management.md`](docs/architecture/A8_battery_and_power_management.md) | 13-point LiPo OCV lookup curve and dynamic power management. |
| **Application API** | [`B1_api_and_services.md`](docs/architecture/B1_api_and_services.md) | Layer 4 declarative lifecycle, hooks, and services. |
| **State Machine** | [`B2_state_machine.md`](docs/architecture/B2_state_machine.md) | Deterministic state transitions, sleep sequences, and wake handling. |
| **Firmware Standards** | [`B3_firmware_standards.md`](docs/architecture/B3_firmware_standards.md) | Coding style, safety hierarchy, pointer hygiene, and formatting. |
| **Verification** | [`C1_benchmarks_and_verification.md`](docs/architecture/C1_benchmarks_and_verification.md) | Timing benchmarks, memory budgets, and power profile metrics. |
| **Lessons Learned** | [`C2_lessons_learned.md`](docs/architecture/C2_lessons_learned.md) | Historical errata, failed trials, and discarded hardware workarounds. |
| **Changelog Policy** | [`C4_changelog_policy.md`](docs/architecture/C4_changelog_policy.md) | Keep a Changelog formatting rules and release procedures. |


---

## 9. MCP Tool Harness: Scope, Architecture & Strategic Planning

The 3-Finger MCP tool suite equips the agent with compiler-grade AST intelligence, binary memory profiling, hardware telemetry SQL, and formal mathematical solvers. Using the right tool eliminates guesswork, prevents token burn, and guarantees physical correctness.

### 1. Semantic Code Intelligence (`clangd`)
* **Available Tools:** `find_symbol`, `get_definition`, `find_references`, `get_type_info`, `get_callers`, `get_callees`, `list_file_symbols`.
* **Purpose & Application:** AST-accurate C/C++ semantic navigation backed by LLVM 18 and `compile_commands.json`. Resolves active `#ifdef` configurations, struct layouts, type hierarchies, and full incoming/outgoing call graphs.
* **Why Preferred Over `grep`:**
  - `grep` is syntactic and blind: it returns false positives in comments, string literals, inactive `#if 0` blocks, and similarly named variables across unrelated files.
  - `clangd` is semantic and exact: `get_definition` jumps straight to the true compiler definition; `find_references` lists exact call sites; `get_type_info` provides precise struct packing and byte offsets.
* **Workflow Example:**
  - ❌ *Bad:* Running `grep -r "sensor_fail_count"` across all files, reading 50 lines of context per match.
  - ✅ *Good:* Calling `get_definition` on `orch_sensor_err_t` to verify enum values, then `find_references` on `sensor_fail_count` to map every assignment in `orch_wake_stub.c`.

### 2. Embedded Diagnostics & Memory Budgets (`embedded-ops`)
* **Available Tools:** `murdock_memory_budget`, `ba_serial_capture_and_decode`, `clangd_touch_reload`.
* **Purpose & Application:** Binary inspection and runtime verification.
  - `murdock_memory_budget`: Evaluates compiled `h1os.elf` using `xtensa-esp32s3-elf-size` and `nm` to return structured JSON byte counts for DRAM, DIRAM, RTC Slow, and Flash partition headroom.
  - `ba_serial_capture_and_decode`: Captures serial boot sequences and automatically runs `xtensa-esp32s3-elf-addr2line` to decode panic backtraces to `file:line (function)`.
  - `clangd_touch_reload`: Busts clangd AST cache after CMake reconfigures without restarting sessions.
* **Why Preferred Over Host Text Dumps:** Eliminates manual calculation of linker map addresses; immediately catches RTC Slow SRAM overflow (>4 KB) before hardware deployment.

### 3. Telemetry & Tabular Analytics (`duckdb`)
* **Available Tools:** `query`.
* **Purpose & Application:** High-performance in-memory SQL analytics directly against disk CSV and Parquet files without database imports or file-locking conflicts.
* **Why Preferred Over Ad-Hoc Scripts:**
  - Allows instant multi-file aggregation (e.g., font metric audits, temperature delta queries over 10-hour chamber tests) in a single turn without writing throwaway Python parsing scripts.
* **Workflow Example:**
  - ❌ *Bad:* Writing a 40-line Python script to load `char_widths_montserrat_14.csv`, sort by width, and print the top 5 widest characters.
  - ✅ *Good:* Executing `SELECT char, width_px FROM 'tools/fonts/char_widths_montserrat_14.csv' ORDER BY width_px DESC LIMIT 5;` via DuckDB.

### 4. Mathematical Grounding & Formal Verification (`science`)
* **Available Tools:** `derive_fixed_point_polynomial`, `solve_z3_assertions`, `fit_thermal_rc`, `eval_symbolic_math`.
* **Purpose & Application:**
  - `derive_fixed_point_polynomial`: Derives Chebyshev/Padé minimax polynomial approximations for FPU-less ULP RISC-V in Q16.16/Q8.24 with Horner evaluation C code and error bounds.
  - `solve_z3_assertions`: Formal SMT verification proving freedom from race conditions and GPIO latch deadlocks.
  - `fit_thermal_rc`: Empirical curve-fitting of sensor thermal step responses ($\tau$).
* **Why Preferred Over Heuristic Guessing:** Produces mathematically optimal, cycle-efficient fixed-point approximations rather than trial-and-error lookup tables.

### 5. Documentation & Technical Reference (`local-index` & `espressif-documentation`)
* **Available Tools:** `search_code_advanced`, `find_files`, `get_file_summary`, `search_espressif_sources`.
* **Purpose & Application:** Precision search across repository architecture docs, IC datasheets (SHTC3, PCF85063A, ES8311, SSD1681), and Espressif Technical Reference Manuals.
* **Tool Quirk:** `local-index/search_code_advanced` strictly requires argument `pattern: str` (do not pass `query`).
