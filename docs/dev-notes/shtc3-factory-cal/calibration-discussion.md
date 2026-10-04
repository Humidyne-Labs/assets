# Sensor Stability and Factory Calibration Discussion

### Inital Unit Test
Within the last 24 hours, I captured a series of basic, ambient, environmental, readings with the SHTC3 sensor. Data observation resulted in the following conclusions, "sensors broke", "codes f-ed", "dev kits broke", "my pants are missing". 

### Data Observations
During basic runtime testing the SHTC3 consistently output readings with a delta far beyond standard operating tolerance. I was observing relitive humidity readings 20% below ambient, temperature readings 15°F above ambient.

### Code Audit
After carful review of the code I've determined that the BSP is error free (in this regard). The algorithm used for converting raw values to standard SI temperature and relitive humidity, is infact the same algorithm outlined in the specification sheet provided by the manufacturer.

### Hardware Inspection
Observing the unpowered hardware under a binocular microscope (10-20x magnification) has revealed no obvious error in manufacturing or defective pertaining to the SHTC3. I can concluded the sensor and development kit are in perfect working order.

### Research on the WWW
I was able to find a dataset that compared the SHTC3 to an array of other environmental sensors of the same class. The data set showed the factory calibration was accurate, and the sensor was able to produce results within the standard operating tolerance with no calibration mechanism in place.

![sensor_plot](sensor_plot_after-dark.png)


### Preliminary Conclusion and Hypothesis
The unit under test is performing outside the standard error margin. The physical placement of the SHTC3 is near the board edge, away from the boost converter and main microcontroller unit. A thermal relief is present on the board layout, providing further isolation from heat and noise associated with general runtime.

- My sensor 'could' be defective.
- The manufacturing process 'could' have introduced contamination that accumulate on the surface of the sensing element.
- The sensor 'could' be getting too hot under normal operating conditions. The MCU clock speed is 240Mhz, all periferals enabled, current draw was unmeasured, assumed to be "normal" per operating spec.

### Low Power Testing
A new test will be performed in order to observe the effects of 'low power' mode. The unit under test will be placed in a sealed box with a humidification source. Environmental conditions are as follows, environmental temperature 73-75°F, environmental relitive humidity 70% non fluctuating. The unit under test will 'deep sleep' for 60 seconds, publish a reading to the display and resume 'deep sleep'. 

This will hopefully minimize heat disappation and produce a more 'normal' environmental reading. One additional, calibrated, sensor will be added to the enclosure to provide a frame of reference. It is my hope that the observed delta will be within the acceptable margin of error per the device spec. 

*The duration of the test is directly dependent on the duration of today's nap*. Recommend test duration is 2-4 human hours.

---

[Source of Independent 3rd Party Dataset](https://wiki.liutyi.info/display/ARDUINO/v8+Sensors+Board)
   
---

# Results of Controlled Environmental Test

- Klaro Valet Hygrometer: ***70.0% RH***, 23.50°C, ***74.30°F***, Die-tmp NA°C,   NA°F
- Humid1-OS   Hygrometer: ***54.8% RH***, 27.39°C, ***81.30°F***, Die-tmp 24.8°C, ***76.64°F***

### Test Observations
The delta between the two units measures 15.2%RH, and 7°F, 3.89°C. This is well beyond the specifications margin of error. The ESP32's internal thermistor was more accurate than the dedicated temperature sensor.

- Estimated test duration 1.5-2 human hours.

![results-image](results-10-03-26.png)
   
   
# Thermal Imaging Results

According the thermal recordings, the SHTC3 package (or *SHIT-C3*, as I've come to call it) is at an idle temperature of [27.6C | 81.68F]. The board is in fact being "***thermally soaked***", **NOT** by alot, but by a few degrees Fahrenheit [3.7C | 6.67F], the measured temperature of the SHTC3 during time of capture was about [27.78-28.33C | 82-83F] (ambient was 23.8C | 74.84F). The offending part being the audio codec, measured at [30.2C | 86.36F]. 

> I can safely state, that the audio codec, has increased the board temperature by about 6 degrees Fahrenheit during run time. #Facts! 

### Questions

- Is 6 degrees Fahrenheit offset large enough to cause instability in the SHTC3?
> I'm reading a temperature delta of 7F during run time testing, and relative humidity delta of 15.2%, again during run time.
- Will disabling the codec cause more I2C issues? 
> I leave the codec powered on due to an undetermined conflict and or initialization issue with the I2C bus. When I'm not terminating power to the codec, the issues are not observed, I2C functions as intended. 


### Conclusion Time!

I can ***NOT*** "definitely" say that a positive temperature offset of the board is ***directly*** causing the instability observed in the SHTC3.

- I now ***suspect*** the instability issue maybe related to a higher than ambient board temperature. I would need to actually test the sensor when the board is at ambient temperature to confirm any suspicion or correlation.
- This is also why the sudo temperature calibration function produced no meaningful results. The ESP32 die temperature reading is a reflection of the board temperature, which is also equal to the SHTC3 temperature during run time testing; ultimately producing a "source temperature" of zero.

> hmm...... interesting ```*beep boop*```
