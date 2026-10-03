# Action Plan: Decoupled MCU-Guided Thermal & Humidity Calibration Module (`bsp_sensor_cal`)

## Executive Summary
To address thermal self-heating caused by the ESP32-S3 SoC on a compact 53mm × 40mm 4–6 layer PCB without altering the core Sensirion SHTC3 driver (`bsp_sensors.h`/`c`), we will introduce a decoupled higher-level calibration & compensation module: **`bsp_sensor_cal.h`** and **`bsp_sensor_cal.c`**.

Additionally, to facilitate hardware bench testing, a self-contained, independent telemetry loop test (`run_thermal_comp_loop_test()`) will be added to `examples/Peripherals_Test_Suite/main/main.c`. It can be toggled via a single `#define ENABLE_THERMAL_LOOP_TEST` macro at the top of `main.c`, allowing continuous live monitoring during testing and easy disabling prior to code commits.

> [!IMPORTANT]
> **Deactivated / Bypass Behavior Confirmation**:
> When thermal compensation is deactivated (either via `bsp_sensor_cal_enable(false)` at runtime or `CONFIG_BSP_THERMAL_COMPENSATION_DEFAULT=n` in Kconfig), **all output readings stem 100% directly from the raw, uncalibrated SHTC3 sensor data**:
> - `data.temperature_c` = `data.raw_temperature_c` (Raw SHTC3 Temp)
> - `data.humidity_percent` = `data.raw_humidity_percent` (Raw SHTC3 Humidity)
> - `data.thermal_offset_c` = `0.0f`
> - `data.compensated` = `false`
> - Direct calls to `bsp_shtc3_read()` in `bsp_sensors.h` ALWAYS return pure raw hardware measurements.

---

## Architectural Principles & Board Specifications

### 1. Board Profile & PCB Stackup
- **Dimensions**: 53 mm × 40 mm
- **Layer Count**: 4 to 6 layers with solid internal copper ground ($GND$) and power ($3V3$) planes.
- **Thermal Conductance**: The internal copper planes provide effective heat spreading ($R_{\theta,\text{pcb}}$ is lower than 2-layer designs). Heat produced by the ESP32-S3 SoC at 240 MHz conducts rapidly to the SHTC3 footprint.
- **Calibrated Coupling Ratio ($K$)**:
  $$K = \frac{R_{\theta,\text{amb}}}{R_{\theta,\text{pcb}}} \approx \mathbf{0.380}$$
  (Adjustable dynamically via `bsp_sensor_cal_set_k(float k)` or Kconfig).

### 2. Decoupled Modular Architecture
```mermaid
flowchart TD
    subgraph Hardware Layer
        S3_HW["ESP32-S3 Internal Temp Sensor (TSENS)"]
        SHTC_HW["Sensirion SHTC3 I2C Sensor (0x70)"]
    end

    subgraph Core BSP Layer (Untouched)
        BSP_SENS["bsp_sensors.h / bsp_sensors.c\n(Pure SHTC3 Driver: bsp_shtc3_read)"]
    end

    subgraph Calibration & Compensation Layer (NEW)
        BSP_CAL["bsp_sensor_cal.h / bsp_sensor_cal.c\n- MCU Die Temp Driver (TSENS)\n- Thermal EMA Filter (Alpha = 0.05)\n- Two-Node Thermal Divider (K = 0.38)\n- Magnus Vapor Pressure RH Equalizer"]
    end

    subgraph Application & Test Suite
        LOOP_TEST["Independent Loop Test\n(run_thermal_comp_loop_test)"]
        APP["Application Telemetry"]
    end

    SHTC_HW --> BSP_SENS
    BSP_SENS --> BSP_CAL
    S3_HW --> BSP_CAL
    BSP_CAL --> LOOP_TEST
    BSP_CAL --> APP
```

---

## Mathematical Models & Bypass Logic

### 1. Two-Node PCB Thermal Divider (When Enabled)
At steady-state equilibrium, the temperature of true ambient air ($T_{\text{amb}}$) is derived from raw SHTC3 temperature ($T_{\text{raw}}$) and filtered MCU die temperature ($T_{\text{die,filt}}$):

$$T_{\text{amb}} = T_{\text{raw}} - K \cdot \max(0, T_{\text{die,filt}} - T_{\text{raw}})$$

**When Deactivated**:
$$T_{\text{amb}} = T_{\text{raw}} \quad \text{and} \quad \Delta T_{\text{offset}} = 0.0^\circ\text{C}$$

### 2. Thermal Mass EMA Low-Pass Filter
The ESP32-S3 silicon die junction changes temperature within milliseconds during CPU bursts, whereas the 53mm × 40mm 4-6 layer PCB ground plane has a thermal time constant $\tau \approx 60\text{--}180\text{ s}$. Raw MCU die readings pass through an Exponential Moving Average (EMA) filter:

$$T_{\text{die,filt}} = \alpha \cdot T_{\text{die,raw}} + (1 - \alpha) \cdot T_{\text{die,filt\_prev}}$$

Default filter weight: $\alpha = 0.050f$.

### 3. Magnus-Tetens Relative Humidity Equalization (When Enabled)
PCB heat elevates sensor temperature without adding moisture mass. To restore true relative humidity ($RH_{\text{amb}}$), vapor pressure $e$ is calculated at raw sensor conditions and equalized against saturation vapor pressure $e_s$ at $T_{\text{amb}}$:

$$\gamma = \frac{17.62 \cdot T_{\text{raw}}}{243.12 + T_{\text{raw}}} + \ln\left(\frac{RH_{\text{raw}}}{100.0}\right)$$

$$e = 6.112 \cdot \exp(\gamma) \quad \text{(Vapor Pressure in hPa)}$$

$$e_s(T_{\text{amb}}) = 6.112 \cdot \exp\left(\frac{17.62 \cdot T_{\text{amb}}}{243.12 + T_{\text{amb}}}\right) \quad \text{(Saturation Vapor Pressure at Ambient)}$$

$$RH_{\text{amb}} = \min\left(100.0, \max\left(0.0, \frac{e}{e_s(T_{\text{amb}})} \cdot 100.0\right)\right)$$

**When Deactivated**:
$$RH_{\text{amb}} = RH_{\text{raw}}$$

---

## Data Structures & API Specification

### `bsp_sensor_cal_data_t` Struct (`bsp_sensor_cal.h`)
Extends standard telemetry without modifying `bsp_shtc3_data_t`:

```c
typedef struct {
    // 1. Telemetry Metrics (Compensated when enabled, Raw SHTC3 when deactivated)
    float temperature_c;        ///< Temperature in Celsius (°C)
    float temperature_f;        ///< Temperature in Fahrenheit (°F)
    float temperature_k;        ///< Temperature in Kelvin (K)
    float humidity_percent;     ///< Relative Humidity (%RH)
    float dew_point_c;          ///< Dew Point in Celsius (°C)
    float dew_point_f;          ///< Dew Point in Fahrenheit (°F)
    float dew_point_k;          ///< Dew Point in Kelvin (K)
    float absolute_humidity_g;  ///< Absolute Humidity (g/m³)

    // 2. Raw Sensor Telemetry & Calibration Diagnostic Metadata
    float raw_temperature_c;    ///< Pure Uncompensated Raw SHTC3 Temperature (°C)
    float raw_humidity_percent; ///< Pure Uncompensated Raw SHTC3 Relative Humidity (%RH)
    float die_temp_c;           ///< Filtered ESP32-S3 MCU Junction Temperature (°C)
    float thermal_offset_c;     ///< Applied Thermal Offset (°C) (0.0°C when deactivated)
    bool  compensated;          ///< True if thermal compensation was active, false if bypassed
    bool  valid;                ///< True if SHTC3 CRC verified
} bsp_sensor_cal_data_t;
```

### Public API Declarations (`bsp_sensor_cal.h`)
```c
/**
 * @brief Initialize Thermal Calibration Subsystem & MCU Temp Sensor
 * @return esp_err_t ESP_OK on success
 */
esp_err_t bsp_sensor_cal_init(void);

/**
 * @brief Read Calibrated & Compensated Environmental Telemetry
 * Reads raw SHTC3 sensor data via bsp_shtc3_read(), queries MCU die temp,
 * applies thermal divider & Magnus RH formula (if enabled), and populates out_data.
 * If compensation is deactivated, out_data fields reflect 100% raw SHTC3 values.
 * @param[out] out_data Target struct to receive metrics
 * @return esp_err_t ESP_OK on success
 */
esp_err_t bsp_sensor_cal_read(bsp_sensor_cal_data_t *out_data);

/**
 * @brief Read Raw ESP32-S3 MCU Junction Temperature
 * @param[out] out_die_temp Pointer to receive die temperature in °C
 * @return esp_err_t ESP_OK on success
 */
esp_err_t bsp_mcu_temp_read(float *out_die_temp);

/**
 * @brief Set Board Thermal Coupling Constant (K)
 * @param[in] k Ratio R_amb / R_pcb (default 0.380f)
 */
void bsp_sensor_cal_set_k(float k);

/**
 * @brief Get Active Board Thermal Coupling Constant (K)
 * @return float Active K value
 */
float bsp_sensor_cal_get_k(void);

/**
 * @brief Enable or Disable Dynamic Thermal Compensation
 * @param[in] enable true to apply compensation, false to return raw uncalibrated SHTC3 values
 */
void bsp_sensor_cal_enable(bool enable);

/**
 * @brief Check if Dynamic Compensation is Enabled
 * @return bool true if enabled
 */
bool bsp_sensor_cal_is_enabled(void);
```

---

## Standalone Hardware Loop Test Design (`examples/Peripherals_Test_Suite/main/main.c`)

To facilitate hardware bench validation without affecting normal test suite execution:
- At the top of `main.c`, define:
  ```c
  #define ENABLE_THERMAL_LOOP_TEST 0  // Set to 1 for continuous loop testing, 0 for normal test suite
  ```
- Implement `run_thermal_comp_loop_test()`:
  ```c
  static void run_thermal_comp_loop_test(void)
  {
      ESP_LOGI(TAG, "==========================================================================================");
      ESP_LOGI(TAG, "  STARTING STANDALONE SHTC3 THERMAL & HUMIDITY COMPENSATION LOOP TEST");
      ESP_LOGI(TAG, "==========================================================================================");
      
      bsp_sensor_cal_init();
      uint32_t iteration = 0;

      while (1) {
          bsp_sensor_cal_data_t data;
          if (bsp_sensor_cal_read(&data) == ESP_OK) {
              ESP_LOGI(TAG, "[#%04lu] SHTC3 Raw: %5.2f°C / %5.2f%% RH | MCU Die: %5.2f°C | Offset: %5.2f°C || Output: %5.2f°C / %5.2f%% RH (%s)",
                       (unsigned long)++iteration,
                       data.raw_temperature_c, data.raw_humidity_percent,
                       data.die_temp_c, data.thermal_offset_c,
                       data.temperature_c, data.humidity_percent,
                       data.compensated ? "COMPENSATED" : "RAW_BYPASS");
          } else {
              ESP_LOGE(TAG, "[#%04lu] Telemetry read error", (unsigned long)++iteration);
          }
          vTaskDelay(pdMS_TO_TICKS(1000));
      }
  }
  ```

---

## Detailed Action Plan

### Step 1: Kconfig Additions
**Target File**: `components/esp32-s3_bsp/Kconfig`
- Add Kconfig menu options:
  - `CONFIG_BSP_THERMAL_COMPENSATION_DEFAULT` (bool, default `y`)
  - `CONFIG_BSP_THERMAL_DIVIDER_K_X1000` (int, range 0..2000, default `380` -> $K = 0.380$)
  - `CONFIG_BSP_THERMAL_EMA_ALPHA_X1000` (int, range 1..1000, default `50` -> $\alpha = 0.050$)

### Step 2: Build System Registration
**Target Files**: `components/esp32-s3_bsp/CMakeLists.txt`, `components/esp32-s3_bsp/include/bsp/bsp.h`
- Add `"src/bsp_sensor_cal.c"` to `bsp_srcs` in `CMakeLists.txt`.
- Add `esp_driver_tsens` to `bsp_requires` in `CMakeLists.txt`.
- Include `#include "bsp/bsp_sensor_cal.h"` in `bsp.h`.

### Step 3: Implement `bsp_sensor_cal.h` and `bsp_sensor_cal.c`
**Target Files**: `components/esp32-s3_bsp/include/bsp/bsp_sensor_cal.h`, `components/esp32-s3_bsp/src/bsp_sensor_cal.c`
- Implement MCU TSENS driver initialization (`driver/temperature_sensor.h`).
- Implement EMA low-pass filtering for $T_{\text{die,filt}}$.
- Wrap `bsp_shtc3_read()` without modifying its implementation or function signature.
- Implement two-node thermal divider math and Magnus-Tetens vapor pressure humidity correction when enabled.
- Return 100% raw uncalibrated SHTC3 data when deactivated.

### Step 4: Standalone Test Routine Integration & Verification
**Target File**: `examples/Peripherals_Test_Suite/main/main.c`
- Add `#define ENABLE_THERMAL_LOOP_TEST 0` switch.
- Implement `run_thermal_comp_loop_test()`.
- Integrate single-pass calibrated read in step 10 of main test suite, and loop test entry when macro is toggled to `1`.
- Build & verify with `idf.py build` in `examples/Peripherals_Test_Suite`.

---

## Acceptance Criteria
1. **Zero Modifications to Core SHTC3 Driver**: `bsp_sensors.h` and `bsp_sensors.c` remain untouched.
2. **Pure Raw Output When Deactivated**: When compensation is disabled via runtime API or Kconfig, readings equal 100% raw uncalibrated SHTC3 data.
3. **Easy Independent Loop Testing**: Toggling `#define ENABLE_THERMAL_LOOP_TEST 1` launches a clean continuous telemetry loop.
4. **Clean ESP-IDF v6 Compilation**: `peripherals_test_suite.bin` compiles cleanly with 0 errors.
