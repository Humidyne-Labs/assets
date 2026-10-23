# Doxygen Documentation & Source Code Annotation Standards

This rule governs source code documentation across all public headers (`components/h1os/include/h1os/*.h`), internal subsystems, and driver source files.

## Documenting for Tools & Humans ("For Us and Them")

High-quality code documentation serves two equal masters:
1. **The Human Engineers:** Rapid comprehension of preconditions, hardware physics, and API contracts.
2. **The Automation Tooling:** Flawless automated generation of developer manuals via Doxygen and `moxygen` into `docs/api.md`.

---

## 1. Comment Block Standards

Use Javadoc-style comment blocks:

```c
/**
 * @brief Brief one-line summary of function purpose.
 *
 * @details Extended technical explanation detailing register manipulation,
 *          timings, or hardware constraints.
 *
 * @param[in]  config    Pointer to valid configuration struct. Must not be NULL.
 * @param[out] out_value Calculated telemetry value in engineering units.
 *
 * @return
 *   - ESP_OK: Operation completed successfully.
 *   - ESP_ERR_INVALID_ARG: Null pointer or parameter out of bounds.
 *   - ESP_ERR_TIMEOUT: Bus transaction timed out.
 *
 * @note Thread-safe. Acquires the shared I2C bus mutex.
 * @warning Must NOT be invoked from ISR context.
 */
esp_err_t sub_sensor_read_sample(const sensor_cfg_t *config, float *out_value);
```

---

## 2. Mandatory Doxygen Tags for Functions

Every public or cross-module function prototype must include:
- `@brief`: Concise, single-sentence purpose.
- `@param[in]`, `@param[out]`, `@param[in,out]`: Direction and description of each argument.
- `@return`: Exhaustive list of return values and error conditions.
- `@note` (when applicable): Concurrency, task affinity, or FreeRTOS context.
- `@warning` (when applicable): Hardware hazards, destructive operations, or pad latch implications.

---

## 3. Struct & Enum Annotations

Use trailing `/**< ... */` comments for members and enumerators:

```c
/**
 * @brief Persistent RTC Slow Memory state block.
 */
typedef struct {
    uint32_t magic;                    /**< Sentinel validation magic word (0x48314F53). */
    uint32_t boot_count;               /**< Total monotonic system boot cycles. */
    uint16_t last_vbat_mv;             /**< Last sampled battery terminal voltage in mV. */
    uint8_t  epd_partial_refresh_count;/**< Quota counter for panel DC bias clearing. */
} orch_persisted_state_t;

/**
 * @brief Audio worker command opcode.
 */
typedef enum {
    AUDIO_CMD_PLAY_TONE = 0, /**< Synthesize discrete frequency tone. */
    AUDIO_CMD_PLAY_CHIME,    /**< Synthesize multi-tone chime pattern. */
    AUDIO_CMD_PLAY_PCM,      /**< Stream raw 16-bit signed PCM audio frames. */
    AUDIO_CMD_STOP           /**< Gracefully ramp volume down to mute. */
} audio_cmd_type_t;
```

---

## 4. Header File Anatomy

All header files must begin with a standardized file header:

```c
/**
 * @file sub_audio.h
 * @brief Everest Semi ES8311 Codec & NS4168 Class-D Audio Subsystem Driver.
 * @copyright Copyright (c) 2026 Humidyne Labs / Humiditron
 * @license SPDX-License-Identifier: MIT
 */

#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"
```
