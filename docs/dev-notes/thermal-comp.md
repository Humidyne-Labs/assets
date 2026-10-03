Yes. In embedded thermal engineering, this is modeled as a **two-node thermal divider** (the thermal equivalent of a resistive voltage divider).

Because the ESP32-S3 die is the primary heat source and the SHTC3 sits on the same PCB, the heat flux flows down a gradient:

$$\text{ESP32-S3 Die } (T_{\text{die}}) \xrightarrow{\;R_{\theta,\text{pcb}}\;} \text{SHTC3 } (T_{\text{shtc}}) \xrightarrow{\;R_{\theta,\text{amb}}\;} \text{Ambient Air } (T_{\text{amb}})$$

---

### The Thermal Divider Equation

At steady-state equilibrium, the conductive heat flux traveling through the PCB copper to the sensor equals the convective heat flux leaving the sensor into the surrounding air:

$$Q = \frac{T_{\text{die}} - T_{\text{shtc}}}{R_{\theta,\text{pcb}}} = \frac{T_{\text{shtc}} - T_{\text{amb}}}{R_{\theta,\text{amb}}}$$

Solving directly for $T_{\text{amb}}$ eliminates the need to guess power dissipation:

$$T_{\text{amb}} = T_{\text{shtc}} - K \cdot (T_{\text{die}} - T_{\text{shtc}})$$

where $K$ is a dimensionless thermal coupling constant specific to your board geometry:

$$K = \frac{R_{\theta,\text{amb}}}{R_{\theta,\text{pcb}}}$$

* **If the MCU is cold** ($T_{\text{die}} \approx T_{\text{shtc}}$): No heat flux flows; $T_{\text{amb}} = T_{\text{shtc}}$.
* **If the MCU throttles up or down**: As $T_{\text{die}}$ climbs, the gradient $(T_{\text{die}} - T_{\text{shtc}})$ widens proportionally, allowing dynamic compensation.

---

### Estimating $K$ for Your Board

Using your environment baseline:

* $T_{\text{amb}} = 23.30^\circ\text{C}$
* $T_{\text{shtc}} = 31.43^\circ\text{C}$
* Assume typical ESP32-S3 junction temperature at 240 MHz idle/light load: $T_{\text{die}} \approx 52^\circ\text{C}$ to $55^\circ\text{C}$

$$K = \frac{T_{\text{shtc}} - T_{\text{amb}}}{T_{\text{die}} - T_{\text{shtc}}} = \frac{31.43 - 23.30}{53.0 - 31.43} = \frac{8.13}{21.57} \approx \mathbf{0.377}$$

Once $K$ is calibrated with a single two-point check, your firmware can compute the dynamic offset on the fly.

---

### ESP-IDF v5 Driver Implementation

The ESP32-S3 has a dedicated internal temperature sensor peripheral managed via `driver/temperature_sensor.h`.

```c
#include "driver/temperature_sensor.h"
#include "esp_log.h"
#include <math.h>

static const char *TAG = "THERMAL_COMP";
static temperature_sensor_handle_t s_temp_sensor = NULL;

// Layout constant: Calibrate this once against known room ambient
#define THERMAL_DIVIDER_K   0.38f

void init_onboard_temp_sensor(void) {
    temperature_sensor_config_t temp_sensor_config = TEMPERATURE_SENSOR_CONFIG_DEFAULT(20, 100);
    ESP_ERROR_CHECK(temperature_sensor_install(&temp_sensor_config, &s_temp_sensor));
    ESP_ERROR_CHECK(temperature_sensor_enable(s_temp_sensor));
    ESP_LOGI(TAG, "ESP32-S3 internal temperature sensor initialized.");
}

bool read_compensated_environment(float raw_shtc_t, float raw_shtc_rh, 
                                  float *comp_t, float *comp_rh, float *die_t) {
    if (!s_temp_sensor) return false;

    // 1. Read internal S3 junction temperature
    if (temperature_sensor_get_celsius(s_temp_sensor, die_t) != ESP_OK) {
        return false;
    }

    // 2. Solve thermal divider for true ambient temperature
    // Guard against negative delta if board was just powered on in a hot room
    float delta_die = *die_t - raw_shtc_t;
    if (delta_die < 0.0f) delta_die = 0.0f;

    *comp_t = raw_shtc_t - (THERMAL_DIVIDER_K * delta_die);

    // 3. Compensate Relative Humidity via Magnus-Tetens formula
    const float b = 17.62f;
    const float c = 243.12f;

    // Actual vapor pressure (e) from raw sensor condition
    float gamma = (b * raw_shtc_t) / (c + raw_shtc_t) + logf(raw_shtc_rh / 100.0f);
    float e = 6.112f * expf(gamma);

    // Saturation vapor pressure (es) at true ambient temperature
    float es_amb = 6.112f * expf((b * (*comp_t)) / (c + (*comp_t)));

    // Corrected RH
    float rh = (e / es_amb) * 100.0f;
    *comp_rh = (rh > 100.0f) ? 100.0f : ((rh < 0.0f) ? 0.0f : rh);

    return true;
}

```

---

### Engineering Caveats to Account For

1. **Thermal Time Constant Mismatch ($\tau$):**
* The ESP32-S3 silicon junction has negligible thermal mass—its die temperature changes in **milliseconds** when a task runs.
* The PCB substrate (FR4 and copper ground plane) has a large thermal capacitance—heat takes **60 to 180 seconds** to soak across to the SHTC3.
* *Mitigation:* Pass `*die_t` through an Exponential Moving Average (EMA) or low-pass filter (e.g., $\alpha = 0.05$) so fast CPU spikes don't cause instantaneous dips in your compensated ambient temperature.


2. **Factory Offset of the S3 Internal Sensor:**
* The internal temperature sensor on the ESP32-S3 has an uncalibrated accuracy of roughly $\pm 3^\circ\text{C}$.
* However, because the thermal divider relies on the *difference* $(T_{\text{die}} - T_{\text{shtc}})$, any fixed offset in the internal sensor simply shifts the empirically measured value of $K$.


3. **External Influences on $R_{\theta,\text{amb}}$:**
* Airflow alters convective resistance ($R_{\theta,\text{amb}}$). If the board is placed inside a sealed enclosure versus exposed to open air, $K$ will shift. Calibrate $K$ in the physical casing the device will ultimately live in.