# Command-Line Usage Examples

- Isolate just SHTC3 and SHT85 (without delta):
```Bash
python plot_sensors.py -c T_V8_000.CSV -s SHTC3 SHT85
```

- Isolate SHTC3, designate SHT85 as baseline, and plot the error (Δ):
```Bash
python plot_sensors.py -c T_V8_000.CSV -s SHTC3 -b SHT85 --diff
```

- Compare model averages across both Temperature and Humidity files:
```Bash
python plot_sensors.py -c T_V8_000.CSV -h H_V8_000.CSV -s SHTC3 -b SHT85 --diff --aggregate
```

- Compare multiple test models (e.g. SHTC3, BME280, AHT10) against SHT85:
```Bash
python plot_sensors.py -c T_V8_000.CSV -s SHTC3 BME280 AHT10 -b SHT85 --diff --aggregate
```
