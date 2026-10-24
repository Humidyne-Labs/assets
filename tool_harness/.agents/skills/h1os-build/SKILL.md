---
name: h1os-build
description: Authoritative build instructions, environment configuration, and execution commands for H1OS and ESP32-S3 firmware. Eliminates exploratory tool searching by providing the exact Espressif v6.1 profile script, paths, and build targets.
---

# H1OS & ESP32-S3 Firmware Build Guide

This skill defines the canonical build procedures, paths, and environment activation for **H1OS** on ESP32-S3.

> [!IMPORTANT]
> **Strict Agent Directive: Zero Exploratory Searching**
> Do not spend turns searching for `idf.py`, python virtual environments, or export scripts. All tooling is located at the exact fixed paths specified below.

---

## 1. Environment & Path Specifications

- **Target Chip:** ESP32-S3 (`esp32s3`)
- **ESP-IDF Version:** v6.1 (`C:\esp\v6.1\esp-idf`)
- **Host Tools Root:** `C:\Espressif\tools`
- **Active Python Virtualenv:** `C:\Espressif\tools\python\v6.1\venv`
- **Canonical Profile Script:** `C:\Espressif\tools\Microsoft.v6.1.PowerShell_profile.ps1`
- **Project Working Directory:** `c:\Users\Matt\Documents\GitHub\H1OS\examples\H1OS`

> [!WARNING]
> On Windows, running `idf.py` requires access to `C:\Espressif\tools`. In AI agent terminals, commands running ESP-IDF builds MUST set `BypassSandbox: true`.

---

## 2. Canonical One-Liner Commands

All commands must be executed in `c:\Users\Matt\Documents\GitHub\H1OS\examples\H1OS` using PowerShell:

### Production Build (Default)
Compiles `bootloader.bin`, `ulp_h1os.bin`, and `h1os.bin` into `build_prod`:
```powershell
& "C:\Espressif\tools\Microsoft.v6.1.PowerShell_profile.ps1"; idf.py -B build_prod build
```

### Development Build
Compiles with debug symbols into `build_dev`:
```powershell
& "C:\Espressif\tools\Microsoft.v6.1.PowerShell_profile.ps1"; idf.py -B build_dev build
```

### Reconfigure / CMake Refresh
Forces a clean CMake re-generation without wiping compiled object caches, applying the exact preset configs:
```powershell
# Development profile (debug symbols, dev sdkconfig):
& "C:\Espressif\tools\Microsoft.v6.1.PowerShell_profile.ps1"; idf.py -B build_dev --preset dev reconfigure

# Production profile (size-optimized, production sdkconfig):
& "C:\Espressif\tools\Microsoft.v6.1.PowerShell_profile.ps1"; idf.py -B build_prod --preset prod reconfigure
```

### Firmware Memory Size Breakdown
Reports DRAM, IRAM, DIRAM, and Flash footprint:
```powershell
& "C:\Espressif\tools\Microsoft.v6.1.PowerShell_profile.ps1"; idf.py -B build_prod size
```

### Comprehensive Size Diagnostic (`inspect_size.py` v2.2.0)
Generates deep per-component, per-file, binary header breakdown and partition headroom summary without triggering Ninja builds (instant, 0% CPU):
```powershell
# Instant direct inspection (default - parses map/bin artifacts without rebuilding):
& "C:\Espressif\tools\Microsoft.v6.1.PowerShell_profile.ps1"; python inspect_size.py -B build_prod

# From project root tools/:
& "C:\Espressif\tools\Microsoft.v6.1.PowerShell_profile.ps1"; python tools/inspect_size.py -B examples/H1OS/build_prod

# Optional: Force a full firmware rebuild before measuring:
& "C:\Espressif\tools\Microsoft.v6.1.PowerShell_profile.ps1"; python inspect_size.py -B build_prod --rebuild
```

### Full Clean
Purges build artifacts if switching major SDK or toolchain versions:
```powershell
& "C:\Espressif\tools\Microsoft.v6.1.PowerShell_profile.ps1"; idf.py -B build_prod fullclean
```

### Flash Firmware to Device
Flashes the bootloader, partition table, and application over USB-Serial:
```powershell
& "C:\Espressif\tools\Microsoft.v6.1.PowerShell_profile.ps1"; idf.py -B build_prod flash
```

---

## 3. Directory Invariants

| Directory | Purpose |
| :--- | :--- |
| `c:\Users\Matt\Documents\GitHub\H1OS\examples\H1OS` | **Main CMake project root**. All `idf.py` commands run from here. |
| `c:\Users\Matt\Documents\GitHub\H1OS\components\h1os` | **Core H1OS component library** (HAL, subsystems, state, lifecycle, ULP). |
| `c:\Users\Matt\Documents\GitHub\H1OS\examples\H1OS\build_prod` | **Production build output** (`h1os.bin`, `ulp_h1os.bin`, `bootloader.bin`). |
| `c:\Users\Matt\Documents\GitHub\H1OS\examples\H1OS\build_dev` | **Development build output**. |
