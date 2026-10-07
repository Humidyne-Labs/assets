# Master Rule: Application Lifecycle & Peripheral Orchestration Architecture

## 1. Primary Directive
`bsp_app_start()` is the **MANDATORY single entry point** and main orchestrator for all application logic in firmware built on the ESP32-S3 e-Paper BSP.

Direct low-level peripheral initialization, manual reset reason checking (`esp_reset_reason()`), raw GPIO wake mask configuration, or manual NVS scratchpad management in `app_main()` is **PROHIBITED**. All application initialization, state transitions, hardware profiling, and sleep stand-downs MUST be driven through the `bsp_app_lifecycle_t` event framework.

---

## 2. Hardware Peripheral Initialization Flow

When `bsp_app_start(&lifecycle)` is called, the lifecycle engine automatically executes a 4-phase initialization pipeline:

```
+-------------------------------------------------------------------------------+
| PHASE 1: RTC Slow Memory & Persistence Initialization                         |
| - Calls bsp_rtc_mem_init()                                                    |
| - Validates RTC magic signature (BSP_RTC_MEM_MAGIC)                           |
| - Restores boot_count, sleep_counts, last_sleep_duration, and app_stage       |
+-------------------------------------------------------------------------------+
                                       |
                                       v
+-------------------------------------------------------------------------------+
| PHASE 2: Reset Reason & Wake Source Inspection                                |
| - Inspects esp_reset_reason() (ESP_RST_DEEPSLEEP vs Cold Boot)                |
| - Inspects esp_sleep_get_wakeup_cause() (EXT1, TIMER, GPIO, etc.)             |
| - Decodes EXT1 mask: checks for BOOT (GPIO0) and POWER (GPIO14) buttons       |
| - Populates immutable, structured bsp_wake_context_t struct                   |
+-------------------------------------------------------------------------------+
                                       |
                                       v
+-------------------------------------------------------------------------------+
| PHASE 3: Dynamic Hardware Profile Execution (bsp_init_mode)                   |
| - Cold Boot (BSP_INIT_MODE_FULL):                                             |
|   1. Power PMIC / Rail Enable (bsp_power_init)                                |
|   2. Peripheral Bus Init (I2C, SPI)                                           |
|   3. E-Paper Display Init (bsp_display_init) & LVGL (bsp_lvgl_init)           |
|   4. Sensors, RTC, Audio, Buttons Init                                        |
|   5. Cold boot splash screen & audio chime execution                          |
| - Wake Resume (BSP_INIT_MODE_FAST / MIN):                                     |
|   1. Restores display frame buffer directly from RTC Slow Memory              |
|   2. Skips OTP full panel refresh to avoid screen flicker/flashing            |
|   3. Re-initializes required buses and hardware peripherals in FAST mode      |
+-------------------------------------------------------------------------------+
                                       |
                                       v
+-------------------------------------------------------------------------------+
| PHASE 4: Application Event Dispatching                                        |
| - Cold Boot  --> Dispatches on_cold_boot(user_data)                           |
| - Wake Resume --> Dispatches on_wake(ctx, user_data) with bsp_wake_context_t  |
+-------------------------------------------------------------------------------+
```

---

## 3. Persistent State Machine Engine (`app_stage` & Scratchpad)

Application state MUST be tracked across deep sleep cycles using the lifecycle persistence functions rather than NVS writes (to prevent flash wear):

* **Stage Tracking (`uint8_t`)**:
  - `bsp_lifecycle_set_stage(uint8_t stage)`: Writes stage code (0..255) to RTC Slow Memory.
  - `bsp_lifecycle_get_stage()`: Reads active stage code.
  - `ctx->app_stage`: Accessible directly inside the `on_wake` callback context.

* **Custom Struct State Scratchpad (Max 31 Bytes)**:
  - `bsp_lifecycle_save_state(const void *data, size_t len)`: Persists application context structs (e.g. sensor telemetry, state counters, target thresholds).
  - `bsp_lifecycle_load_state(void *out_data, size_t len)`: Restores custom struct state on wake.

---

## 4. Sleep Stand-Down & Clean Shutdown Protocol

* **Entering Sleep**:
  Applications MUST enter sleep via `bsp_lifecycle_enter_sleep(&sleep_cfg)`:
  1. Automatically triggers visual sleep splash (`BSP_SPLASH_SLEEP`) and audio chime (`BSP_CHIME_SLEEP`).
  2. Automatically invokes the application's registered `on_before_sleep` callback for resource cleanup.
  3. Saves the active LVGL display buffer to RTC Slow Memory.
  4. Configures hardware RTC countdown alarms / EXT1 button wake sources and enters low-power sleep.

* **System Power Off**:
  Applications MUST shutdown via `bsp_lifecycle_power_off()`:
  1. Invokes the application's registered `on_shutdown` callback.
  2. Safely de-initializes peripherals and drops the PMIC power latch (`BAT_CTRL`).

---

## 5. Complete C Implementation Reference Guide

```c
#include <stdio.h>
#include "esp_log.h"
#include "nvs_flash.h"
#include "esp_event.h"
#include "bsp/bsp.h"
#include "bsp/bsp_lifecycle.h"

static const char *TAG = "main_app";

// Application State Codes
typedef enum {
    APP_STAGE_INITIAL_SETUP = 0,
    APP_STAGE_SENSOR_READ   = 1,
    APP_STAGE_DISPLAY_SHOW  = 2,
} app_stage_t;

// Custom State Scratchpad (Max 31 bytes)
typedef struct {
    float    last_temp;
    uint32_t sample_count;
} app_state_data_t;

/**
 * @brief Cold Boot Callback (Executed on initial power-on or hard reset)
 */
static void app_on_cold_boot(void *user_data)
{
    ESP_LOGI(TAG, "=== COLD BOOT: Initializing Application State ===");
    
    // Set initial stage to STAGE 0
    bsp_lifecycle_set_stage(APP_STAGE_INITIAL_SETUP);

    app_state_data_t state = { .last_temp = 0.0f, .sample_count = 0 };
    bsp_lifecycle_save_state(&state, sizeof(state));

    // Render Initial UI
    bsp_lvgl_lock();
    lv_obj_t *scr = lv_screen_active();
    lv_obj_clean(scr);
    lv_obj_t *lbl = lv_label_create(scr);
    lv_label_set_text(lbl, "SYSTEM COLD BOOT");
    lv_obj_center(lbl);
    bsp_lvgl_unlock();

    // Advance stage and enter deep sleep for 10 seconds
    bsp_lifecycle_set_stage(APP_STAGE_SENSOR_READ);
    
    bsp_sleep_config_t sleep_cfg = BSP_SLEEP_CONFIG_DEFAULT();
    sleep_cfg.mode = BSP_SLEEP_MODE_DEEP;
    sleep_cfg.duration_sec = 10;
    sleep_cfg.wake_sources = BSP_WAKE_SOURCE_TIMER | BSP_WAKE_SOURCE_BUTTON_BOOT;

    bsp_lifecycle_enter_sleep(&sleep_cfg);
}

/**
 * @brief Resume Wake Callback (Executed on Deep / Light Sleep resume)
 */
static void app_on_wake(const bsp_wake_context_t *ctx, void *user_data)
{
    ESP_LOGI(TAG, "=== WAKE RESUME: Boot Count = %lu, Stage = %u ===", 
             (unsigned long)ctx->boot_count, ctx->app_stage);

    app_state_data_t state = {0};
    bsp_lifecycle_load_state(&state, sizeof(state));
    state.sample_count++;

    if (ctx->woke_from_button && ctx->wake_button == BSP_BUTTON_BOOT) {
        ESP_LOGI(TAG, "Woke up from BOOT button click!");
    }

    switch (ctx->app_stage) {
    case APP_STAGE_SENSOR_READ: {
        float temp = 0.0f, humidity = 0.0f;
        if (bsp_sensors_read_sht4x(&temp, &humidity) == ESP_OK) {
            state.last_temp = temp;
            ESP_LOGI(TAG, "Sampled Temp: %.2f C", temp);
        }
        bsp_lifecycle_save_state(&state, sizeof(state));
        bsp_lifecycle_set_stage(APP_STAGE_DISPLAY_SHOW);
        break;
    }

    case APP_STAGE_DISPLAY_SHOW: {
        bsp_lvgl_lock();
        lv_obj_t *scr = lv_screen_active();
        lv_obj_clean(scr);
        lv_obj_t *lbl = lv_label_create(scr);
        lv_label_set_text_fmt(lbl, "TEMP: %.1f C\nCOUNT: %lu", state.last_temp, (unsigned long)state.sample_count);
        lv_obj_center(lbl);
        bsp_lvgl_unlock();

        bsp_lifecycle_set_stage(APP_STAGE_SENSOR_READ);
        break;
    }

    default:
        bsp_lifecycle_set_stage(APP_STAGE_SENSOR_READ);
        break;
    }

    // Enter next 30s sleep cycle
    bsp_sleep_config_t sleep_cfg = BSP_SLEEP_CONFIG_DEFAULT();
    sleep_cfg.mode = BSP_SLEEP_MODE_DEEP;
    sleep_cfg.duration_sec = 30;
    sleep_cfg.wake_sources = BSP_WAKE_SOURCE_TIMER | BSP_WAKE_SOURCE_BUTTON_BOOT;

    bsp_lifecycle_enter_sleep(&sleep_cfg);
}

/**
 * @brief Cleanup hook executed prior to entering sleep
 */
static void app_on_before_sleep(bsp_sleep_mode_t mode, uint32_t duration_sec, void *user_data)
{
    ESP_LOGI(TAG, "Cleaning up resources before sleep (%u sec)...", (unsigned)duration_sec);
}

/**
 * @brief Shutdown hook executed prior to power off
 */
static void app_on_shutdown(void *user_data)
{
    ESP_LOGI(TAG, "Executing system shutdown cleanup...");
}

void app_main(void)
{
    // Mandatory NVS & Event Loop Init
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);
    ESP_ERROR_CHECK(esp_event_loop_create_default());

    // Configure Lifecycle Engine
    bsp_app_lifecycle_t lifecycle = {
        .on_cold_boot    = app_on_cold_boot,
        .on_wake         = app_on_wake,
        .on_before_sleep = app_on_before_sleep,
        .on_shutdown     = app_on_shutdown,
        .user_data       = NULL,
    };

    // Start Main Application Lifecycle Orchestrator
    ESP_ERROR_CHECK(bsp_app_start(&lifecycle));
}
```
