#!/usr/bin/env python3
"""
LVGL UI Virtualization & Headless Snapshot MCP Server.
Compiles C UI widget snippets into a native host binary, executes LVGL 9 frame rendering,
and exports a base64-encoded PNG image for multimodal visual layout inspection.
"""

import os
import sys
import base64
import subprocess
import shutil
from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("LVGL-Virtualization-Server")

HARNESS_DIR = Path(__file__).resolve().parent.parent
DEFAULT_LVGL_ROOT = Path(os.environ.get("LVGL_ROOT", HARNESS_DIR / "lvgl-9.6.0")).resolve()
TEMPLATE_HARNESS = HARNESS_DIR / "tools" / "lvgl_headless" / "headless_harness.c"
STB_HEADER = HARNESS_DIR / "tools" / "lvgl_headless" / "stb_image_write.h"
MSVC_VCVARS = r"C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"


def _get_lvgl_root() -> Path:
    if DEFAULT_LVGL_ROOT.exists():
        return DEFAULT_LVGL_ROOT
    candidates = list(HARNESS_DIR.glob("lvgl-9*")) + list(HARNESS_DIR.glob("lvgl*"))
    if candidates:
        return candidates[0]
    return DEFAULT_LVGL_ROOT


def _get_lvgl_c_files(lvgl_root: Path) -> list[Path]:
    src_dir = lvgl_root / "src"
    if not src_dir.exists():
        return list(lvgl_root.rglob("*.c"))
    
    # Filter out test/demo/benchmark files inside src if any
    c_files = []
    for f in src_dir.rglob("*.c"):
        # Exclude drivers or tests that require missing third-party libs
        parts = [p.lower() for p in f.parts]
        if any(x in parts for x in ("win32", "sdl", "wayland", "x11", "drm", "nema", "vg_lite", "thorvg", "libjpeg", "libpng", "ffmpeg", "freetype")):
            continue
        c_files.append(f)
    return c_files


@mcp.tool()
def render_ui_snapshot(c_ui_code: str, width: int = 200, height: int = 200) -> dict:
    """Compiles and renders a snippet of LVGL 9 C code into a PNG layout snapshot.
    
    Args:
        c_ui_code: Raw C code block to place inside the setup function (e.g. creating labels, buttons, cards).
        width: Display width in pixels (default 200).
        height: Display height in pixels (default 200).
        
    Returns:
        dict containing 'status', 'image_png_base64', and compiler/runtime messages.
    """
    lvgl_root = _get_lvgl_root()
    if not lvgl_root.exists():
        return {"status": "error", "message": f"LVGL root not found at {lvgl_root}"}

    if not TEMPLATE_HARNESS.exists():
        return {"status": "error", "message": f"Headless harness template not found at {TEMPLATE_HARNESS}"}

    work_dir = HARNESS_DIR / "tools" / "lvgl_headless" / "_build"
    work_dir.mkdir(parents=True, exist_ok=True)

    # Ensure stb_image_write.h is in work_dir
    if STB_HEADER.exists():
        shutil.copy(STB_HEADER, work_dir / "stb_image_write.h")

    # Prepare injected source code
    template_content = TEMPLATE_HARNESS.read_text(encoding="utf-8")
    
    # Replace dimension macros if requested
    custom_template = f"#define DISP_HOR_RES {width}\n#define DISP_VER_RES {height}\n" + template_content
    
    # Inject user code into build_ui_candidate body
    marker_start = "// USER_CODE_MARKER_START"
    marker_end = "// USER_CODE_MARKER_END"
    
    injected_func = f"""
void build_ui_candidate(void) {{
    lv_obj_t *scr = lv_screen_active();
{c_ui_code}
}}
"""
    if marker_start in custom_template and marker_end in custom_template:
        before = custom_template.split(marker_start)[0]
        after = custom_template.split(marker_end)[1]
        final_src = before + injected_func + after
    else:
        final_src = custom_template.replace("build_ui_candidate(void) {", f"build_ui_candidate(void) {{\n{c_ui_code}\n//")

    src_file = work_dir / "harness_gen.c"
    src_file.write_text(final_src, encoding="utf-8")

    lvgl_c_files = _get_lvgl_c_files(lvgl_root)
    runner_exe = work_dir / "runner.exe"
    png_path = work_dir / "ui_snapshot.png"

    if png_path.exists():
        png_path.unlink()

    # 1. Attempt MSVC build if on Windows and vcvars64 exists
    compiled_ok = False
    build_log = ""

    if sys.platform == "win32" and os.path.exists(MSVC_VCVARS):
        rsp_file = work_dir / "compile_files.rsp"
        rsp_content = f"/nologo /O2 /utf-8 /DLV_CONF_SKIP /DISP_HOR_RES={width} /DISP_VER_RES={height} /I\"{work_dir}\" /I\"{lvgl_root}\" /I\"{lvgl_root / 'src'}\" /Fe:\"{runner_exe}\" \"{src_file}\"\n"
        rsp_content += "\n".join(f'"{f}"' for f in lvgl_c_files)
        rsp_file.write_text(rsp_content, encoding="utf-8")

        bat_file = work_dir / "build.bat"
        bat_content = f'@echo off\ncall "{MSVC_VCVARS}" >nul\ncl @"compile_files.rsp"\n'
        bat_file.write_text(bat_content, encoding="utf-8")

        res = subprocess.run([str(bat_file)], cwd=work_dir, capture_output=True, text=True)
        compiled_ok = (res.returncode == 0 and runner_exe.exists())
        build_log = res.stdout + "\n" + res.stderr
    else:
        # Fallback to GCC / Clang
        compile_cmd = [
            "gcc", "-O2", "-std=c11", "-DLV_CONF_SKIP",
            f"-DDISP_HOR_RES={width}", f"-DDISP_VER_RES={height}",
            str(src_file),
            "-I", str(work_dir),
            "-I", str(lvgl_root),
            "-I", str(lvgl_root / "src"),
            "-lm",
            "-o", str(runner_exe)
        ]
        compile_cmd.extend([str(f) for f in lvgl_c_files])
        res = subprocess.run(compile_cmd, cwd=work_dir, capture_output=True, text=True)
        compiled_ok = (res.returncode == 0 and runner_exe.exists())
        build_log = res.stdout + "\n" + res.stderr

    if not compiled_ok:
        # Filter compiler error lines
        error_lines = [ln for ln in build_log.splitlines() if "error" in ln.lower() or "fatal" in ln.lower()]
        summary_errors = "\n".join(error_lines[:25]) if error_lines else build_log[-1500:]
        return {
            "status": "compile_error",
            "diagnostics": summary_errors,
            "message": "Compilation failed. Review diagnostics and fix C UI code."
        }

    # 2. Execute runner binary
    run_res = subprocess.run([str(runner_exe)], cwd=work_dir, capture_output=True, text=True)

    if run_res.returncode != 0 or not png_path.exists():
        return {
            "status": "runtime_error",
            "diagnostics": run_res.stderr or run_res.stdout,
            "message": "Runner binary execution failed or image was not generated."
        }

    # 3. Read rendered PNG and encode base64
    png_bytes = png_path.read_bytes()
    png_b64 = base64.b64encode(png_bytes).decode("utf-8")

    return {
        "status": "success",
        "image_png_base64": png_b64,
        "resolution": f"{width}x{height}",
        "message": f"UI layout rendered successfully at {width}x{height} resolution."
    }


if __name__ == "__main__":
    mcp.run()
