# Master Rule: H1OS Application Lifecycle & Peripheral Orchestration Architecture

## 1. Primary Directive
`h1os_start()` (or `h1os_init()`) is the **MANDATORY single entry point** and lifecycle orchestrator for all application firmware on H1OS.

Direct low-level peripheral initialization, manual reset reason checking (`esp_reset_reason()`), raw GPIO wake mask configuration, manual NVS scratchpad management, or bypassing the 4-layer boundary hierarchy in `app_main()` is **PROHIBITED**. All application initialization, state transitions, hardware profiling, flow arbitration, and sleep stand-downs MUST be driven through the declarative `h1os_lifecycle_t` event framework.

---

## 2. Four-Layer Unidirectional Hierarchy

Firmware strictly adheres to a 4-layer control and dependency hierarchy:

```
+-------------------------------------------------------------------------------+
| LAYER 4: APPLICATION & UI ENGINE (h1os.h, h1os_lvgl.h, h1os_time.h)           |
| - Declarative lifecycle hooks: on_boot, on_wake, on_sleep, on_shutdown        |
| - Decoupled LVGL v9 presentation task pinned to Core 1                        |
+-------------------------------------------------------------------------------+
                                       |
                                       v
+-------------------------------------------------------------------------------+
| LAYER 3: SYSTEM ORCHESTRATION PIPELINE (orch_flow, orch_state, orch_math)     |
| - Flow Arbiter: Flow A (Headless Telemetry) vs Flow B (Interactive Session)   |
| - Persistent RTC Slow Memory (<512B Tri-Node sliding ring buffer)             |
| - Thermodynamic math invariants (Magnus vapor pressure, dew point, EWMA)      |
| - ULP-RISC-V Reactive Coprocessor Monitor (sleep-gated)                       |
+-------------------------------------------------------------------------------+
                                       |
                                       v
+-------------------------------------------------------------------------------+
| LAYER 2: HARDWARE SUBSYSTEM MANAGERS (sub_display, sub_sensor, sub_rtc, ...)  |
| - Encapsulated drivers: sub_power, sub_audio, sub_sdcard, sub_nvs             |
| - Invariant: Zero inter-subsystem cross-talk (orchestrated solely by Layer 3) |
+-------------------------------------------------------------------------------+
                                       |
                                       v
+-------------------------------------------------------------------------------+
| LAYER 1: HARDWARE ABSTRACTION LAYER (hal_io, hal_spi, hal_i2c, hal_flash)     |
| - Pure C hardware primitives: Pad holds, latch release, DMA SPI, I2C master   |
| - hal_types.h: Shared fixed-width types, error codes, and pinout constants    |
+-------------------------------------------------------------------------------+
```

### Invariant Rules of Layer Separation:
1. **Unidirectional Control:** Upper layers call lower layers. Lower layers **NEVER** include, call, or signal higher layers.
2. **Zero Cross-Talk in Layer 2:** Subsystems never communicate directly (e.g. `sub_display` never calls `sub_power`; `sub_sensor` never queries battery voltage). Layer 3 Orchestrator coordinates all multi-subsystem tasks.
3. **Bootloader Power Latching:** Power latch (`GPIO 17 BAT_CTRL = 1`) is latched strictly in the 2nd-stage bootloader hook (`h1os_boot_hook`) within 25 ms. Runtime HAL preserves RTC sleep pad holds and exposes `hal_io_release_power_latch()` for orderly power-down.
4. **ULP Sleep-Gating Rule:** The ULP-RISC-V Coprocessor is active **only** while the dual-core Xtensa CPU is in deep sleep. Once Flow B wakes, ULP execution is suspended to prevent bus contention.

---

## 3. Dual Execution Flows: Flow A vs. Flow B

H1OS firmware operates in two mutually exclusive execution paradigms:

### Flow A: Headless Sensor Telemetry Sprint (<10 ms, Target <4 ms)
* **Execution Domain:** Fast RTC wake stub (`orch_wake_stub`) on Core 0 running at 80 MHz. Core 1 is gated off, Flash SPI is unpowered.
* **Operation:** 
  1. Wakes on periodic internal RTC timer.
  2. Samples SHTC3 environmental sensor in normal mode (`0x7866`) and MCU die TSENS.
  3. Executes integer fixed-point Magnus psychrometric invariant calculation (`orch_math`): computes true water vapor pressure ($e$), dew point ($T_{\text{dew}}$), and EWMA slope.
  4. Appends telemetry record to 32-slot ring buffer in RTC Slow Memory (`orch_state`).
  5. Re-arms periodic RTC timer and returns immediately to deep sleep.
* **Thermal Invariant:** Zero self-heating. CPU flash and high-power rails remain unpowered during Flow A to preserve ambient thermal integrity.

### Flow B: Interactive User Session & UI Presentation
* **Execution Domain:** Dual-core Xtensa LX7 FreeRTOS SMP with 240 MHz Turbo power lock during initial blit, dropping via Dynamic Frequency Scaling (DFS) to 80 MHz during idle interaction.
* **Operation:**
  1. Triggered by user button tap (GPIO 0 or 18) or hardware RTC alarm (GPIO 5).
  2. Bootloader latches power and boots FreeRTOS SMP.
  3. Spawns decoupled LVGL v9 presentation task pinned to Core 1.
  4. Dispatches `on_wake(ctx, user_data)` with populated immutable `h1os_wake_context_t`.
  5. Manages user navigation, cycling telemetry views, or executing acoustic chimes.
  6. Tracks developer-configurable inactivity timer (default: 30 seconds). Upon timeout or explicit sleep request, initiates the coordinated sleep stand-down sequence.

---

## 4. Coordinated Sleep Stand-Down Sequence

Applications MUST transition to sleep via `h1os_sleep()` or `h1os_shutdown()` to trigger the deterministic 8-step shutdown sequence:

1. **Invoke Pre-Sleep Hook:** Execute application's registered `on_sleep` callback for custom resource cleanup.
2. **Drain UI Engine:** Drain LVGL draw buffers and signal the Core 1 presentation task to halt cleanly.
3. **Wait for Display Bus:** Poll SSD1681 `BUSY` signal release at 80 MHz CPU frequency.
4. **Microcapsule Settling Delay:** Wait mandatory 250 ms physical settling delay for electrophoretic ink microcapsules.
5. **Flash Frame Sync:** If the active frame was marked dirty, commit 5000-byte 1-bit buffer to SPI Flash partition `epd_frame` (`orch_display_sync`).
6. **Peripheral Isolation:** Stand down audio codec (`sub_audio` software standby) and isolate I2C/SPI buses.
7. **Configure Sleep Triggers:** Program ULP-RISC-V wake monitor, RTC countdown timer, and button edge wakeup pads (`GPIO 0` / `GPIO 18`).
8. **Assert Pad Holds & Sleep:** Enable RTC pad hold on `BAT_CTRL` (GPIO 17) and enter hardware deep sleep (`esp_deep_sleep_start()`).

---

## 5. Declarative C Implementation Pattern

```c
#include "esp_log.h"
#include "h1os/h1os.h"
#include "h1os/h1os_lvgl.h"

static const char *TAG = "app_main";

static void app_on_boot(void *user_data)
{
    ESP_LOGI(TAG, "Cold boot initialized. Building initial LVGL screen...");
    // Build initial UI widgets on active LVGL screen
}

static void app_on_wake(const h1os_wake_context_t *ctx, void *user_data)
{
    ESP_LOGI(TAG, "Interactive Flow B wake: boot_count=%lu, cause=0x%lx",
             (unsigned long)ctx->boot_count, (unsigned long)ctx->wakeup_causes);
    
    if (ctx->woke_from_button) {
        ESP_LOGI(TAG, "Woke via button %u. Refreshing display view...", ctx->wake_button);
    }
}

static void app_on_sleep(void *user_data)
{
    ESP_LOGI(TAG, "Entering unattended sleep. Releasing user resources...");
}

void app_main(void)
{
    const h1os_lifecycle_t lifecycle = {
        .on_boot     = app_on_boot,
        .on_wake     = app_on_wake,
        .on_sleep    = app_on_sleep,
        .on_shutdown = NULL,
        .user_data   = NULL,
    };

    const h1os_config_t config = {
        .inactivity_timeout_sec = 30,
        .flow_a_period_sec      = 60,
        .enable_audio           = true,
    };

    ESP_ERROR_CHECK(h1os_init(&config));
    ESP_ERROR_CHECK(h1os_start(&lifecycle));
}
```
