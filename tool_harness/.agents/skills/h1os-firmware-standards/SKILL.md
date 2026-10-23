---
name: h1os-firmware-standards
description: Authoritative engineering and coding standard for H1OS firmware. Use whenever writing, editing, refactoring, formatting, or reviewing C/C++ source code, drivers, headers, or CMake configurations for H1OS on ESP32-S3. Enforces the 3-layer safety hierarchy: Layer 1 automated style (.clang-format), Layer 2 core embedded safety rules (fixed-width types, FPU32 single precision, deterministic memory, checked returns, bounded stacks, non-blocking ISRs, inter-core volatile coherency), and Layer 3 compiler hardening.
---

# H1OS Firmware Engineering & Safety Standards Protocol

## 1. Core Architectural Philosophy
Firmware reliability fails when standards are theoretical documents that developers ignore. In H1OS, engineering discipline is enforced through a strict three-layer hierarchy:

1. **Layer 1: Mechanical Style** is delegated 100% to automated tooling (`.clang-format`). Braces, indentation, column limits, and whitespace are never debated in reviews.
2. **Layer 2: Embedded Safety Rules** govern architectural invariants: type discipline, single-precision FPU constraints, deterministic memory, and concurrency boundaries.
3. **Layer 3: Compiler Hardening** transforms best practices into automated build blockers via aggressive compiler flags (`-Werror`, `-Wdouble-promotion`, `-Wshadow`).

---

## 2. Layer 1: Automated Style & Formatting

### 2.1 Tooling & Execution
Never format code by hand. Use the repository tool:
```bash
# Format all component source and header files in-place
python tools/check_format.py

# Verify formatting compliance (CI / pre-commit check, exits non-zero on diff)
python tools/check_format.py --check
```

### 2.2 Formatting Invariants (`.clang-format`)
- **Language Standard:** C11 / C++17
- **Base Style:** LLVM with Linux-style function and block braces
- **Indentation:** 4 spaces (Tabs strictly forbidden)
- **Column Limit:** 100 characters
- **Pointer Alignment:** Right (`uint8_t *buffer`, `orch_persisted_state_t *st`)
- **Consecutive Alignment:** Local blocks only (`Consecutive`) to prevent multi-line git diff churn across blank lines
- **Include Blocks:** Regrouped and sorted case-sensitively

---

## 3. Layer 2: Core Embedded Safety Rules (The 10 Invariants)

### Rule 1: Type Discipline & Fixed Widths
- **Ban Naked Primitives:** Naked `int`, `short`, `long`, and `unsigned` are strictly prohibited. All variables and struct members must declare explicit bit-width from `<stdint.h>` (`uint8_t`, `int16_t`, `uint32_t`, `int64_t`).
- **Naked `char` Restriction:** Plain `char` is permitted exclusively for null-terminated ASCII string literals (`const char *str`). Binary byte buffers, payloads, and register bitfields must strictly use `uint8_t`.
- **System Exception:** Types mandated by ESP-IDF or FreeRTOS (`size_t`, `BaseType_t`, `TickType_t`, `esp_err_t`) are explicitly permitted where required by framework signatures.

### Rule 2: Single-Precision FPU Discipline (FPU32)
The ESP32-S3 contains a hardware IEEE 754 single-precision floating point unit (FPU32). Double-precision operations trigger software emulation routines that consume up to 50x more CPU cycles.
- **Literal Suffixes:** All floating-point numeric literals must carry the `f` suffix:
  ```c
  // PROHIBITED (triggers soft-float double emulation):
  float es = 6.112 * exp(17.625 * temp / (243.04 + temp));

  // MANDATORY (executes single-cycle hardware FPU instructions):
  float es = 6.112f * expf(17.625f * temp / (243.04f + temp));
  ```
- **Math Functions:** Always invoke single-precision `libm` variants: `expf()`, `logf()`, `powf()`, `fabsf()`.
- **Logging Exception:** In `ESP_LOG*` and `printf` variadic calls, standard C promotes `float` to `double`. Explicitly cast float arguments to `(double)` to satisfy `-Wdouble-promotion`.

### Rule 3: Deterministic Memory Allocation
- **Zero Runtime Dynamic Allocation:** Unbounded calls to `malloc()`, `calloc()`, `realloc()`, `free()`, or C++ `new`/`delete` are strictly banned inside FreeRTOS task loops, callbacks, and worker routines.
- **Initialization Pools:** Dynamic allocation is permitted exclusively during board bring-up (`app_main()` / `h1os_start()`) prior to task activation (e.g., allocating large display framebuffers in external PSRAM).
- **Persistent State:** Long-lived state must be allocated statically or placed in RTC Slow Memory (`RTC_DATA_ATTR`) for deep sleep survival.

### Rule 4: Guard-Clause Control Flow
- **Early Exit Pattern:** Avoid nested `if/else` conditional pyramids (arrow anti-pattern). Validate preconditions and error statuses immediately with guard clauses:
  ```c
  // MANDATORY:
  if (param == NULL) {
      return ESP_ERR_INVALID_ARG;
  }
  if (!s_initialized) {
      return ESP_ERR_INVALID_STATE;
  }
  ```

### Rule 5: Checked Return Codes (`[[nodiscard]]`)
- **Error Bubbling:** All functions returning `esp_err_t` or status codes must be evaluated by the caller. Driver initializations, I2C/SPI transactions, and FreeRTOS queue pushes must never have their returns silently ignored.
- **Explicit Ignoration:** If a return value is deliberately unhandled, it must be explicitly cast to `(void)` with an explanatory comment:
  ```c
  (void)esp_pm_lock_release(s_pm_lock); // Best-effort release before deep sleep
  ```

### Rule 6: Bounded Stack Usage
- **Ban Variable-Length Arrays (VLAs):** Runtime sizing (`uint8_t buffer[length];`) is strictly prohibited.
- **No Unbounded Recursion:** All algorithms must execute with deterministic call graph depth.
- **Large Stack Allocations:** Buffers larger than 128 bytes must never be allocated on a task stack. Use static memory pools or shared workspace buffers.

### Rule 7: RTOS & ISR Execution Boundaries
- **Non-blocking ISRs:** Never acquire mutexes, execute delay loops (`vTaskDelay`), or perform blocking bus transactions inside Interrupt Service Routines (ISRs).
- **Deferred Work:** Defer all hardware I/O from ISR context to a high-priority worker task via direct FreeRTOS task notifications or queues (`xQueueSendFromISR`).
- **Bounded Timeouts:** Operational tasks must never wait indefinitely (`portMAX_DELAY`) on external hardware interrupts without a watchdog kick or recovery timeout.

### Rule 8: Inter-Core & ULP Shared State
- **Volatile Semantics:** Any variable shared across the RV32IMC ULP coprocessor, Core 0 RTC Fast Wake Stub, and the dual-core Xtensa application must be qualified with `volatile`.
- **Memory Fencing:** Update flags must be committed using hardware memory barriers or atomic latch sequences before sleeping or releasing coprocessors.

### Rule 9: Defensive Design & Exhaustive Enums
- **Mandatory Default Labels:** Every `switch` statement must include an explicit `default:` label to trap undefined or corrupt enum states:
  ```c
  switch (flow) {
      case ORCH_FLOW_A_SAMPLE: ... break;
      case ORCH_FLOW_B_MAIN_WAKE: ... break;
      default:
          ESP_LOGE(TAG, "Unhandled flow: %d", (int)flow);
          assert(false);
          break;
  }
  ```

### Rule 10: Pointer Sanitization
- Public API interfaces accepting pointer arguments must validate inputs against `NULL` prior to dereferencing.

### Rule 11: Dynamic Frequency Scaling (DFS) & Turbo Blitz Invariants
- **80 MHz Quiescent Baseline:** The main dual-core Xtensa CPU cores are gated down to an 80 MHz baseline during interactive standby, input polling, FreeRTOS idle, and quiescent sensor acquisition to minimize thermal dissipation and current draw.
- **240 MHz LVGL Blitz:** During LVGL widget rendering, dirty rectangle calculation, font glyph rasterization, 1-bit monochrome pixel packing, and SSD1681 differential SPI frame transfer ("LVGL Blitz"), the CPU frequency must be bumped to 240 MHz via `sub_power_cpu_max_acquire()`. Upon completion of display flushing, the lock is released to drop back to 80 MHz immediately.
- **240 MHz Audio Playback Invariant:** During I2S audio initialization and tone/chime playback, `sub_power_cpu_max_acquire()` must be held. Without this clock lock, APB frequency droop during DFS drops the I2S MCLK/BCLK dividers, causing playback pitch to shift octaves lower and triggering DMA FIFO underruns.

---

## 4. Layer 3: Compiler Hardening (CMake)
The H1OS component build strictly enforces these safety policies at compile time via `${COMPONENT_LIB}` private compile options in `components/h1os/CMakeLists.txt`:

```cmake
target_compile_options(${COMPONENT_LIB} PRIVATE
    -Wall
    -Wextra
    -Werror
    -Wshadow
    -Wdouble-promotion
    -Wformat=2
    -Wno-format-nonliteral
    $<$<COMPILE_LANGUAGE:C>:-Wstrict-prototypes>
    -Wno-missing-field-initializers
)
```

| Flag | Purpose | Defect Prevented |
| :--- | :--- | :--- |
| `-Werror` | Treats all warnings as build failures | Zero tolerance for code drift |
| `-Wdouble-promotion` | Warns on implicit `float` to `double` promotion | Eliminates catastrophic soft-float CPU slowdowns on ESP32-S3 FPU32 |
| `-Wshadow` | Warns when a local variable shadows an outer variable | Prevents subtle variable shadowing bugs in nested loops/blocks |
| `-Wformat=2` | Enforces strict `printf`/`scanf` type and length checking | Traps stack corruption and formatting specifier mismatches |
| `-Wno-format-nonliteral` | Permits dynamic format strings for `strftime` | Allows runtime date/time format selection without false positives |
| `-Wstrict-prototypes` | Requires explicit `(void)` for empty parameter lists | Prevents un-prototyped C function calls |
| `-Wno-missing-field-initializers`| Allows standard `{0}` aggregate zero-initialization | Idiomatic struct clearing without false positives |

*(Note: `-Wundef` is intentionally omitted because ESP-IDF internal system headers evaluate uninitialized configuration macros directly).*

---

## 5. Documentation Architecture Hierarchy (Option 2: Three-Series Taxonomy)
When authoring or referencing documentation in `docs/architecture/`, adhere strictly to the 3-series taxonomy:
- **Series A (Silicon & Hardware):** `A0_system_governance.md` through `A7_sensor_psychrometrics.md` (HAL, hold domains, subsystems, orchestrator, ULP, sensors).
- **Series B (Developer & App Layer):** `B1_api_and_services.md`, `B2_state_machine.md`, `B3_firmware_standards.md` (Application interfaces, state machine, safety standards).
- **Series C (Operations & Governance):** `C1_benchmarks_and_verification.md` through `C4_changelog_policy.md` (Verification, lessons learned, roadmap, changelog).
