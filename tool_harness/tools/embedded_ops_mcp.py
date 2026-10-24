#!/usr/bin/env python3
"""
embedded_ops_mcp.py - Phase 3 Embedded Operations MCP Server
Provides:
  1. murdock_memory_budget: Structured Linker & Section Auditor (JSON RAM/Flash/RTC boundaries).
  2. ba_serial_capture_and_decode: Non-blocking serial capture with automated panic backtrace decoding via addr2line.
  3. clangd_touch_reload: Compilation Database Cache Buster & reload trigger.
"""

import os
import sys
import time
import glob
import json
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("embedded-ops")

DEFAULT_H1OS_ROOT = Path("C:/Users/Matt/Documents/GitHub/H1OS")
DEFAULT_ELF_PATH = DEFAULT_H1OS_ROOT / "examples/H1OS/build_dev/h1os.elf"

def find_toolchain_binary(name: str) -> str:
    """Find xtensa toolchain binary on PATH or standard Espressif tool directory."""
    # 1. Check PATH
    for path_dir in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(path_dir) / f"{name}.exe"
        if candidate.is_file():
            return str(candidate)
        candidate_no_ext = Path(path_dir) / name
        if candidate_no_ext.is_file():
            return str(candidate_no_ext)

    # 2. Check ~/.espressif/tools/xtensa-esp-elf/
    home = Path.home()
    pattern = str(home / ".espressif/tools/xtensa-esp-elf/**/bin" / f"{name}.exe")
    matches = glob.glob(pattern, recursive=True)
    if matches:
        return matches[0]

    # Fallback to name
    return name

@mcp.tool()
def murdock_memory_budget(
    elf_path: str = str(DEFAULT_ELF_PATH),
    app_partition_max_bytes: int = 3145728 # 3.0 MB
) -> str:
    """
    Structured Linker & Section Auditor. Runs xtensa-esp32s3-elf-size and nm
    to return a deterministic JSON payload for single-turn RAM/Flash/RTC boundary assertions.
    """
    elf_file = Path(elf_path)
    if not elf_file.is_file():
        return json.dumps({
            "status": "error",
            "message": f"ELF file not found at: {elf_file}"
        }, indent=2)

    size_bin = find_toolchain_binary("xtensa-esp32s3-elf-size")
    nm_bin = find_toolchain_binary("xtensa-esp32s3-elf-nm")

    # 1. Run size -A
    try:
        size_output = subprocess.check_output(
            [size_bin, "-A", str(elf_file)],
            universal_newlines=True,
            stderr=subprocess.STDOUT
        )
    except Exception as e:
        return json.dumps({"status": "error", "message": f"size execution failed: {e}"}, indent=2)

    sections: Dict[str, int] = {}
    for line in size_output.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and parts[1].isdigit():
            sections[parts[0]] = int(parts[1])

    # ESP32-S3 Physical Memory Limits
    DIRAM_TOTAL = 341760   # 333.75 KB internal DRAM/IRAM pool
    RTC_FAST_TOTAL = 8192  # 8.0 KB
    RTC_SLOW_TOTAL = 4096  # 4.0 KB

    # Calculate sections
    rtc_fast_used = (
        sections.get(".rtc.text", 0) +
        sections.get(".rtc.force_fast", 0) +
        sections.get(".rtc_reserved", 0)
    )
    rtc_slow_used = (
        sections.get(".rtc.data", 0) +
        sections.get(".rtc_noinit", 0) +
        sections.get(".rtc.force_slow", 0)
    )
    rtc_total_headroom = (RTC_FAST_TOTAL - rtc_fast_used) + (RTC_SLOW_TOTAL - rtc_slow_used)

    dram_used = sections.get(".dram0.data", 0) + sections.get(".dram0.bss", 0)
    iram_overflow = max(0, sections.get(".iram0.text", 0) - 16384)
    diram_used = dram_used + iram_overflow
    diram_free = max(0, DIRAM_TOTAL - diram_used)

    flash_app_used = (
        sections.get(".flash.text", 0) +
        sections.get(".flash.rodata", 0) +
        sections.get(".flash.appdesc", 0) +
        sections.get(".flash.tdata", 0)
    )
    flash_headroom_bytes = max(0, app_partition_max_bytes - flash_app_used)
    flash_headroom_pct = round((flash_headroom_bytes / app_partition_max_bytes) * 100.0, 2)

    # 2. Run nm --size-sort -S -C
    top_rtc_symbols = []
    top_bss_symbols = []
    try:
        nm_output = subprocess.check_output(
            [nm_bin, "-S", "-C", "--size-sort", str(elf_file)],
            universal_newlines=True,
            stderr=subprocess.DEVNULL
        )
        for line in nm_output.splitlines():
            parts = line.strip().split(maxsplit=3)
            if len(parts) >= 4:
                addr, size_hex, sym_type, sym_name = parts[0], parts[1], parts[2], parts[3]
                try:
                    sym_size = int(size_hex, 16)
                except ValueError:
                    continue

                # Categorize
                if sym_type.lower() in ("b", "d") and ("rtc" in sym_name.lower() or addr.startswith("5000") or addr.startswith("600f")):
                    top_rtc_symbols.append({"name": sym_name, "size": sym_size, "type": sym_type})
                elif sym_type.lower() == "b":
                    top_bss_symbols.append({"name": sym_name, "size": sym_size, "type": sym_type})
    except Exception:
        pass

    # Sort descending
    top_rtc_symbols.sort(key=lambda s: s["size"], reverse=True)
    top_bss_symbols.sort(key=lambda s: s["size"], reverse=True)

    result = {
        "status": "ok",
        "elf_path": str(elf_file),
        "dram_used_bytes": dram_used,
        "diram_free_bytes": diram_free,
        "diram_used_pct": round((diram_used / DIRAM_TOTAL) * 100.0, 1),
        "rtc_fast_used_bytes": rtc_fast_used,
        "rtc_fast_free_bytes": max(0, RTC_FAST_TOTAL - rtc_fast_used),
        "rtc_slow_used_bytes": rtc_slow_used,
        "rtc_slow_free_bytes": max(0, RTC_SLOW_TOTAL - rtc_slow_used),
        "rtc_total_headroom_bytes": rtc_total_headroom,
        "flash_app_used_bytes": flash_app_used,
        "flash_app_headroom_bytes": flash_headroom_bytes,
        "flash_app_headroom_pct": flash_headroom_pct,
        "top_rtc_symbols": top_rtc_symbols[:10],
        "top_bss_symbols": top_bss_symbols[:10]
    }
    return json.dumps(result, indent=2)

def decode_backtrace_addresses(addr_list: List[str], elf_path: str) -> List[Dict[str, str]]:
    """Decode raw hex PC addresses to file:line (function) using addr2line."""
    if not addr_list:
        return []
    addr2line_bin = find_toolchain_binary("xtensa-esp32s3-elf-addr2line")
    cmd = [addr2line_bin, "-pfiaC", "-e", elf_path] + addr_list
    try:
        output = subprocess.check_output(cmd, universal_newlines=True, stderr=subprocess.STDOUT)
        frames = []
        for line in output.splitlines():
            line_str = line.strip()
            if line_str:
                frames.append({"frame": line_str})
        return frames
    except Exception as e:
        return [{"error": f"addr2line failed: {e}"}]

@mcp.tool()
def ba_serial_capture_and_decode(
    port: str = "COM3",
    baud: int = 115200,
    duration_sec: float = 8.0,
    wait_for_pattern: str = "",
    reset_on_connect: bool = False,
    elf_path: str = str(DEFAULT_ELF_PATH),
    raw_log_input: str = ""
) -> str:
    """
    USB-JTAG Serial Capture & Automated Panic Backtrace Decoder.
    Captures live output from target COM port (or parses raw_log_input)
    and resolves any Guru Meditation or abort() PC stack addresses using addr2line.
    """
    captured_text = ""

    if raw_log_input:
        captured_text = raw_log_input
    else:
        try:
            import serial
            ser = serial.Serial(port, baudrate=baud, timeout=0.2)
            if reset_on_connect:
                ser.setDTR(False)
                ser.setRTS(True)
                time.sleep(0.1)
                ser.setRTS(False)

            start_time = time.time()
            buffer = []
            while (time.time() - start_time) < duration_sec:
                line = ser.readline()
                if line:
                    decoded = line.decode("utf-8", errors="replace")
                    buffer.append(decoded)
                    if wait_for_pattern and wait_for_pattern in "".join(buffer):
                        break
            ser.close()
            captured_text = "".join(buffer)
        except Exception as e:
            if not raw_log_input:
                return json.dumps({
                    "status": "error",
                    "port": port,
                    "message": f"Serial port connection failed: {e}. Provide raw_log_input to decode offline logs."
                }, indent=2)

    # Strip ANSI terminal escape sequences
    clean_text = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", captured_text)

    # Scan for ESP32 backtraces:
    # Pattern 1: 0x42001234:0x3fc95678 (PC:SP pairs)
    # Pattern 2: Backtrace: 0x40375a1b:0x3fca01e0 0x42008b14:0x3fca0210 ...
    # Pattern 3: PC: 0x42001234 or PC : 0x42001234
    pc_addresses = []

    # Find Backtrace lines
    bt_matches = re.findall(r"Backtrace:(.*?)(?:\r?\n|$)", clean_text)
    for bt in bt_matches:
        pairs = re.findall(r"(0x4[02][0-9a-fA-F]{6}):0x3[fc][0-9a-fA-F]{6}", bt)
        for pc in pairs:
            if pc not in pc_addresses:
                pc_addresses.append(pc)

    # Also find standalone PC: 0x4...
    direct_pc = re.findall(r"PC\s*:\s*(0x4[02][0-9a-fA-F]{6})", clean_text)
    for pc in direct_pc:
        if pc not in pc_addresses:
            pc_addresses.append(pc)

    # Decode stack frames if addresses found
    decoded_frames = []
    if pc_addresses and Path(elf_path).is_file():
        decoded_frames = decode_backtrace_addresses(pc_addresses, elf_path)

    has_panic = "Guru Meditation Error" in clean_text or "abort() was called" in clean_text or len(pc_addresses) > 0

    return json.dumps({
        "status": "ok",
        "has_panic": has_panic,
        "addresses_found": pc_addresses,
        "stack_frames": decoded_frames,
        "log_preview": clean_text[-2000:] if len(clean_text) > 2000 else clean_text
    }, indent=2)

@mcp.tool()
def clangd_touch_reload(
    workspace_dir: str = str(DEFAULT_H1OS_ROOT),
    probe_header: str = "components/h1os/include/h1os/h1os.h"
) -> str:
    """
    Compilation Database Cache Buster.
    Updates modification timestamps (touch) on compile_commands.json, .clangd,
    and a key probe header to force clangd to re-index without restarting the session.
    """
    root = Path(workspace_dir)
    touched = []

    files_to_touch = [
        root / "compile_commands.json",
        root / ".clangd",
        root / "examples/H1OS/.clangd",
        root / "examples/H1OS/build_dev/compile_commands.json",
        root / probe_header
    ]

    for f in files_to_touch:
        if f.is_file():
            try:
                f.touch(exist_ok=True)
                touched.append(str(f))
            except Exception:
                pass

    return json.dumps({
        "status": "ok",
        "message": "Touched compilation database and probe files to trigger clangd re-index.",
        "touched_files": touched
    }, indent=2)

if __name__ == "__main__":
    mcp.run()
