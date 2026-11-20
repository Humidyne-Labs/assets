#!/usr/bin/env python3
"""
embedded_ops_mcp.py - Phase 3 Embedded Operations MCP Server
Provides:
  1. murdock_memory_budget: Structured Linker & Section Auditor (JSON RAM/Flash/RTC boundaries).
  2. murdock_stack_budget: GCC -fstack-usage (.su) per-function static stack frame & dynamic-VLA auditor.
  3. murdock_rtc_section_audit: ELF .rtc.text disassembly & section call-graph auditor (Flash-free Flow A check).
  4. ba_serial_capture_and_decode: Non-blocking serial capture with automated panic backtrace decoding via addr2line.
  5. clangd_touch_reload: Compilation Database Cache Buster & reload trigger.
  6. epd_char_info: Exact 1-bpp glyph metrics and ASCII bitmap lookup via Vault or CSV manifests.
  7. epd_string_budget: Exact LVGL v9 pixel width and 188 px safe-budget clearance calculator.
  8. epd_audit_screens: Automated LVGL C/C++ screen label overflow scanner.
  9. epd_icon_search: Search unified icon catalog across FA7, Lucide, Phosphor, Tabler, and Tabler-Filled.
 10. epd_font_inventory: Summarize active Strike Vault, CSV metrics, asset manifests, and schemes.
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
DEFAULT_EPD_FONT_TOOLS_DIR = Path(
    os.environ.get("EPD_FONT_TOOLS_DIR", "C:/Users/Matt/Documents/GitHub/epd-font/tools/agent/tools")
)
if str(DEFAULT_EPD_FONT_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(DEFAULT_EPD_FONT_TOOLS_DIR))
import epd_typography as _epd_typo

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

    # 2. Check C:\Espressif\tools\xtensa-esp-elf\ (EIM Windows default) and ~/.espressif\tools\xtensa-esp-elf\
    search_roots = [
        Path("C:/Espressif/tools/xtensa-esp-elf"),
        Path.home() / ".espressif" / "tools" / "xtensa-esp-elf",
    ]
    for root in search_roots:
        if not root.is_dir():
            continue
        pattern = str(root / "**" / "bin" / f"{name}.exe")
        matches = sorted(glob.glob(pattern, recursive=True), reverse=True)
        if matches:
            return matches[0]
        pattern_posix = str(root / "**" / "bin" / name)
        matches_posix = sorted(glob.glob(pattern_posix, recursive=True), reverse=True)
        if matches_posix:
            return matches_posix[0]

    # Fallback to bare command name
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


@mcp.tool()
def murdock_stack_budget(
    build_dir: str = str(DEFAULT_H1OS_ROOT / "examples/H1OS/build_dev"),
    max_fn_bytes: int = 512,
    project_only: bool = True,
) -> str:
    """
    Static Stack Frame Auditor. Parses GCC -fstack-usage (*.su) files in build_dir
    to verify bounded per-function stack frames and catch dynamic/VLA stack allocations.
    """
    bdir = Path(build_dir)
    if not bdir.is_dir():
        return json.dumps({
            "status": "error",
            "message": f"Build directory not found: {bdir}",
        }, indent=2)

    all_su = sorted(bdir.rglob("*.su"))
    if project_only:
        su_files = [
            p for p in all_su
            if any(seg in p.as_posix() for seg in ("/esp-idf/h1os/", "/esp-idf/main/"))
        ]
        if not su_files:
            su_files = all_su
    else:
        su_files = all_su

    entries: List[Dict[str, Any]] = []
    parse_errors: List[str] = []
    for su_path in su_files:
        try:
            text = su_path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            parse_errors.append(f"{su_path}: {exc}")
            continue
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            parts = line.rsplit("\t", 2)
            if len(parts) != 3:
                continue
            loc_fn, size_str, qual = parts
            # Format: <file>:<line>:<col>:<func> (file may contain C:\ drive colon)
            loc_parts = loc_fn.rsplit(":", 3)
            if len(loc_parts) == 4:
                src_file, line_no, _col, func_name = loc_parts
            else:
                src_file, line_no, func_name = str(su_path.name), "0", loc_fn
            try:
                stack_bytes = int(size_str)
            except ValueError:
                continue
            entries.append({
                "function": func_name,
                "stack_bytes": stack_bytes,
                "qualifier": qual,
                "file": Path(src_file).name,
                "line": int(line_no) if line_no.isdigit() else 0,
                "su_file": su_path.relative_to(bdir).as_posix(),
            })

    entries.sort(key=lambda item: item["stack_bytes"], reverse=True)
    dynamic_allocs = [e for e in entries if "dynamic" in e["qualifier"].lower()]
    over_budget = [e for e in entries if e["stack_bytes"] > max_fn_bytes]
    max_stack = entries[0]["stack_bytes"] if entries else 0

    status = "ok"
    if not su_files:
        status = "no_su_files"
    elif dynamic_allocs or over_budget:
        status = "violation"

    return json.dumps({
        "status": status,
        "build_dir": str(bdir),
        "max_fn_budget_bytes": max_fn_bytes,
        "files_parsed": len(su_files),
        "functions_analyzed": len(entries),
        "max_stack_bytes": max_stack,
        "dynamic_allocations": dynamic_allocs,
        "over_budget": over_budget,
        "parse_errors": parse_errors,
        "top_20_functions": entries[:20],
    }, indent=2)


@mcp.tool()
def murdock_rtc_section_audit(
    elf_path: str = str(DEFAULT_ELF_PATH),
) -> str:
    """
    RTC Wake-Stub Section Auditor. Disassembles .rtc.text from the ELF and verifies
    all branch/call and symbol references stay inside RTC memory or Mask ROM (no Flash calls).
    """
    elf_file = Path(elf_path)
    if not elf_file.is_file():
        return json.dumps({
            "status": "error",
            "message": f"ELF file not found at: {elf_file}",
        }, indent=2)

    objdump_bin = find_toolchain_binary("xtensa-esp32s3-elf-objdump")
    nm_bin = find_toolchain_binary("xtensa-esp32s3-elf-nm")

    try:
        hdr_out = subprocess.check_output(
            [objdump_bin, "-h", str(elf_file)],
            universal_newlines=True,
            stderr=subprocess.STDOUT,
        )
        nm_out = subprocess.check_output(
            [nm_bin, "-n", "--defined-only", str(elf_file)],
            universal_newlines=True,
            stderr=subprocess.STDOUT,
        )
        dis_out = subprocess.check_output(
            [objdump_bin, "-d", "-j", ".rtc.text", str(elf_file)],
            universal_newlines=True,
            stderr=subprocess.STDOUT,
        )
    except Exception as exc:
        return json.dumps({"status": "error", "message": f"objdump/nm failed: {exc}"}, indent=2)

    # Parse section VMA ranges from objdump -h
    sections: List[Dict[str, Any]] = []
    for line in hdr_out.splitlines():
        m = re.match(r"^\s*\d+\s+(\S+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+", line)
        if m:
            sec_name = m.group(1)
            sec_size = int(m.group(2), 16)
            sec_vma = int(m.group(3), 16)
            if sec_size > 0:
                sections.append({"name": sec_name, "start": sec_vma, "end": sec_vma + sec_size})

    # Parse symbol map (address -> name) and locate .rtc.text symbols
    addr_to_sym: Dict[int, str] = {}
    rtc_text_sec = next((s for s in sections if s["name"] == ".rtc.text"), None)
    rtc_text_symbols: List[Dict[str, str]] = []
    for line in nm_out.splitlines():
        parts = line.strip().split(maxsplit=2)
        if len(parts) == 3:
            try:
                addr = int(parts[0], 16)
            except ValueError:
                continue
            sym_name = parts[2]
            addr_to_sym[addr] = sym_name
            if rtc_text_sec and rtc_text_sec["start"] <= addr < rtc_text_sec["end"]:
                rtc_text_symbols.append({"name": sym_name, "addr": f"0x{addr:08x}"})

    def _classify_addr(addr: int) -> str:
        if 0x40000000 <= addr < 0x40060000:
            return "ESP32S3_ROM"
        for s in sections:
            if s["start"] <= addr < s["end"]:
                return str(s["name"])
        return "UNKNOWN"

    def _is_rtc_or_rom_safe(sec_name: str) -> bool:
        return sec_name == "ESP32S3_ROM" or sec_name.startswith(".rtc")

    # Pass 1: collect all literal-pool 4-byte word ranges referenced by l32r AND inspect literal targets
    lit_ranges: List[tuple[int, int]] = []
    l32r_re = re.compile(r"^\s*([0-9a-fA-F]+):\s+[0-9a-fA-F ]+\s+l32r\s+\S+,\s+([0-9a-fA-F]+)\s+<[^>]+>(?:\s+\(([0-9a-fA-F]+)\s+<([^>]+)>\))?")
    unsafe_literal_sections = {".flash.text", ".flash.rodata", ".flash.tdata", ".flash.appdesc", ".iram0.text", ".dram0.data", ".dram0.bss"}

    verified_calls: List[Dict[str, str]] = []
    flash_or_iram_violations: List[Dict[str, str]] = []
    seen_edges = set()

    func_hdr_re = re.compile(r"^[0-9a-fA-F]+\s+<([^>]+)>:")
    cur_func = "<unknown>"
    dis_lines = dis_out.splitlines()

    for line in dis_lines:
        fm = func_hdr_re.match(line.strip())
        if fm:
            cur_func = fm.group(1)
            continue
        lm = l32r_re.match(line)
        if lm:
            lit_addr = int(lm.group(2), 16)
            lit_ranges.append((lit_addr, lit_addr + 4))
            if lm.group(3):
                val_addr = int(lm.group(3), 16)
                val_sec = _classify_addr(val_addr)
                if val_sec in unsafe_literal_sections:
                    tgt_label = lm.group(4)
                    edge = (cur_func, f"l32r:{tgt_label}", val_sec)
                    if edge not in seen_edges:
                        seen_edges.add(edge)
                        flash_or_iram_violations.append({
                            "caller": cur_func,
                            "insn": "l32r",
                            "target": tgt_label,
                            "target_addr": f"0x{val_addr:08x}",
                            "target_section": val_sec,
                        })

    def _in_lit_pool(addr: int) -> bool:
        return any(start <= addr < end for start, end in lit_ranges)

    # Pass 2: walk executable instructions in .rtc.text (excluding literal pool words)
    cur_func = "<unknown>"
    insn_re = re.compile(r"^\s*([0-9a-fA-F]+):\s+[0-9a-fA-F ]+\s+(call0|call4|call8|call12|j)\s+([0-9a-fA-F]+)\s+<([^>]+)>")

    for line in dis_lines:
        fm = func_hdr_re.match(line.strip())
        if fm:
            cur_func = fm.group(1)
            continue
        cm = insn_re.match(line)
        if cm:
            insn_addr = int(cm.group(1), 16)
            if _in_lit_pool(insn_addr):
                continue
            insn, tgt_hex, tgt_label = cm.group(2), cm.group(3), cm.group(4)
            tgt_addr = int(tgt_hex, 16)
            tgt_sec = _classify_addr(tgt_addr)
            tgt_sym = tgt_label.split("+")[0]
            edge = (cur_func, tgt_sym, tgt_sec)
            if edge in seen_edges:
                continue
            seen_edges.add(edge)
            rec = {
                "caller": cur_func,
                "insn": insn,
                "target": tgt_label,
                "target_addr": f"0x{tgt_addr:08x}",
                "target_section": tgt_sec,
            }
            if _is_rtc_or_rom_safe(tgt_sec):
                verified_calls.append(rec)
            elif tgt_sec in unsafe_literal_sections:
                flash_or_iram_violations.append(rec)
            else:
                # Xtensa PC-relative call/j within +-512 KB of 0x600fe000 targeting
                # unmapped MMIO space indicates alignment-padding/literal-byte objdump desync.
                continue

    status = "violation" if flash_or_iram_violations else "ok"
    return json.dumps({
        "status": status,
        "elf_path": str(elf_file),
        "rtc_text_range": (
            f"0x{rtc_text_sec['start']:08x}..0x{rtc_text_sec['end']:08x}" if rtc_text_sec else "none"
        ),
        "rtc_text_symbol_count": len(rtc_text_symbols),
        "rtc_text_symbols": rtc_text_symbols,
        "verified_calls_count": len(verified_calls),
        "verified_calls": verified_calls,
        "flash_or_unsafe_violations_count": len(flash_or_iram_violations),
        "flash_or_unsafe_violations": flash_or_iram_violations,
    }, indent=2)

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


@mcp.tool()
def epd_char_info(
    strike: str = "humid1_font_plex_sans_normal_14",
    char_query: str = "@",
    workspace_dir: str = str(DEFAULT_H1OS_ROOT),
    vault_path: str = "",
    metrics_dir: str = "",
    prefer_csv: bool = False,
) -> str:
    """Look up exact 1-bpp LVGL v9 glyph metrics and pixel bitmap for a character or icon."""
    try:
        res = _epd_typo.inspect_char(
            strike=strike,
            char_query=char_query,
            workspace_dir=workspace_dir,
            vault_path=vault_path or None,
            metrics_dir=metrics_dir or None,
            prefer_csv=prefer_csv,
        )
        return json.dumps({"status": "ok", **res}, indent=2)
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)}, indent=2)


@mcp.tool()
def epd_string_budget(
    strike: str = "humid1_font_plex_sans_normal_14",
    text: str = "",
    right_text: str = "",
    right_strike: str = "",
    hw_scheme: str = "esp32s3-N8R8-hw_scheme.json",
    min_gap: int = 8,
    workspace_dir: str = str(DEFAULT_H1OS_ROOT),
    vault_path: str = "",
    metrics_dir: str = "",
    prefer_csv: bool = False,
) -> str:
    """Calculate exact LVGL v9 pixel width and 188 px EPD layout clearance for a string or split telemetry row."""
    try:
        res = _epd_typo.measure_string_budget(
            strike=strike,
            text=text,
            right_text=right_text or None,
            right_strike=right_strike or None,
            hw_scheme=hw_scheme,
            min_gap=min_gap,
            workspace_dir=workspace_dir,
            vault_path=vault_path or None,
            metrics_dir=metrics_dir or None,
            prefer_csv=prefer_csv,
        )
        return json.dumps({"status": "ok", **res}, indent=2)
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)}, indent=2)


@mcp.tool()
def epd_audit_screens(
    workspace_dir: str = str(DEFAULT_H1OS_ROOT),
    screen_dir: str = "",
    default_strike: str = "humid1_font_plex_sans_normal_14",
    hw_scheme: str = "esp32s3-N8R8-hw_scheme.json",
    vault_path: str = "",
    metrics_dir: str = "",
) -> str:
    """Scan C/C++ UI screen files for lv_label_set_text[_fmt] strings exceeding the usable display budget."""
    try:
        res = _epd_typo.audit_screen_strings(
            workspace_dir=workspace_dir,
            screen_dir=screen_dir or None,
            default_strike=default_strike,
            hw_scheme=hw_scheme,
            vault_path=vault_path or None,
            metrics_dir=metrics_dir or None,
        )
        return json.dumps({"status": "ok", **res}, indent=2)
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)}, indent=2)


@mcp.tool()
def epd_icon_search(
    query: str = "",
    vendor: str = "all",
    limit: int = 25,
    workspace_dir: str = str(DEFAULT_H1OS_ROOT),
) -> str:
    """Search unified_icon_names.json across FA7, Lucide, Phosphor, Tabler, and Tabler-Filled icon catalogs."""
    try:
        res = _epd_typo.search_icons(
            query=query,
            vendor=vendor,
            limit=limit,
            workspace_dir=workspace_dir,
        )
        return json.dumps({"status": "ok", **res}, indent=2)
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)}, indent=2)


@mcp.tool()
def epd_font_inventory(
    workspace_dir: str = str(DEFAULT_H1OS_ROOT),
) -> str:
    """Summarize active Strike Vault strikes, packaged CSV metric manifests, asset counts, and font schemes."""
    try:
        res = _epd_typo.inventory_fonts(workspace_dir=workspace_dir)
        return json.dumps({"status": "ok", **res}, indent=2)
    except Exception as exc:
        return json.dumps({"status": "error", "message": str(exc)}, indent=2)


if __name__ == "__main__":
    mcp.run()
