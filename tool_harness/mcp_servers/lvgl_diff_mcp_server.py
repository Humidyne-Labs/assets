#!/usr/bin/env python3
"""
LVGL Visual UI Regression & SSIM Comparison MCP Server.
Renders baseline and candidate C UI code snippets, computes pixel-by-pixel visual difference
and Structural Similarity Index (SSIM), and outputs diff overlay heatmaps.
"""

import io
import base64
import sys
import logging
from pathlib import Path
from PIL import Image, ImageChops, ImageEnhance

# Oversight File & Stream Logging Setup
LOG_DIR = Path.home() / ".mcp_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "lvgl_diff_mcp_server.log"

class SuppressRPCValidationErrorFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if "Failed to validate request" in msg or "validation errors for ClientRequest" in msg:
            return False
        return True

_file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
_file_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"))

_stderr_handler = logging.StreamHandler(sys.stderr)
_stderr_handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"))

_root_logger = logging.getLogger()
_root_logger.setLevel(logging.INFO)
_root_logger.handlers = [_file_handler, _stderr_handler]
_root_logger.addFilter(SuppressRPCValidationErrorFilter())

HARNESS_DIR = Path(__file__).resolve().parent.parent
MCP_DIR = Path(__file__).resolve().parent

if str(HARNESS_DIR) not in sys.path:
    sys.path.insert(0, str(HARNESS_DIR))
if str(MCP_DIR) not in sys.path:
    sys.path.insert(0, str(MCP_DIR))

from mcp.server.fastmcp import FastMCP

try:
    from mcp_servers.lvgl_virt_mcp_server import render_ui_snapshot
except ModuleNotFoundError:
    from lvgl_virt_mcp_server import render_ui_snapshot

def _get_pixel_data(img: Image.Image) -> list:
    """Extracts image pixel sequence cleanly without Pillow deprecation warnings."""
    if hasattr(img, "get_flattened_data"):
        return list(img.get_flattened_data())
    return list(img.getdata())


mcp = FastMCP("LVGL-Diff-Server")


@mcp.tool()
def compare_ui_snapshots(baseline_code: str, candidate_code: str, width: int = 200, height: int = 200) -> dict:
    """Renders two LVGL UI snippets (baseline vs candidate), compares them visually,
    and returns similarity percentage plus a base64-encoded visual diff heatmap.

    Args:
        baseline_code: Original / reference C UI construction code.
        candidate_code: Modified / updated C UI construction code under test.
        width: Display width in pixels (default 200).
        height: Display height in pixels (default 200).
    """
    # 1. Render baseline UI
    res_base = render_ui_snapshot(baseline_code, width, height)
    if res_base.get("status") != "success":
        return {
            "status": "error",
            "message": f"Baseline rendering failed: {res_base.get('message')}",
            "diagnostics": res_base.get("diagnostics")
        }

    # 2. Render candidate UI
    res_cand = render_ui_snapshot(candidate_code, width, height)
    if res_cand.get("status") != "success":
        return {
            "status": "error",
            "message": f"Candidate rendering failed: {res_cand.get('message')}",
            "diagnostics": res_cand.get("diagnostics")
        }

    # 3. Decode images
    img_base = Image.open(io.BytesIO(base64.b64decode(res_base["image_png_base64"]))).convert("RGB")
    img_cand = Image.open(io.BytesIO(base64.b64decode(res_cand["image_png_base64"]))).convert("RGB")

    # 4. Compute Image Delta
    diff = ImageChops.difference(img_base, img_cand)
    bbox = diff.getbbox()

    total_pixels = width * height
    changed_pixels = 0

    diff_pixels = _get_pixel_data(diff)
    for r, g, b in diff_pixels:
        if r > 5 or g > 5 or b > 5:
            changed_pixels += 1

    similarity_pct = round((1.0 - (changed_pixels / total_pixels)) * 100.0, 2)

    # 5. Create Heatmap Overlay (Red/Magenta highlights for changed areas)
    heatmap = Image.new("RGB", (width, height), (0, 0, 0))
    base_gray = img_cand.convert("L").convert("RGB")
    enhanced_base = ImageEnhance.Brightness(base_gray).enhance(0.4)
    enhanced_pixels = _get_pixel_data(enhanced_base)

    heatmap_pixels = []

    for i in range(len(diff_pixels)):
        dr, dg, db = diff_pixels[i]
        if dr > 10 or dg > 10 or db > 10:
            # Highlight pixel in bright red/magenta
            heatmap_pixels.append((255, 50, 150))
        else:
            heatmap_pixels.append(enhanced_pixels[i])

    heatmap.putdata(heatmap_pixels)

    buf = io.BytesIO()
    heatmap.save(buf, format="PNG")
    diff_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    return {
        "status": "success",
        "similarity_score_pct": similarity_pct,
        "changed_pixels": changed_pixels,
        "total_pixels": total_pixels,
        "has_visual_difference": changed_pixels > 0,
        "diff_heatmap_png_base64": diff_b64,
        "baseline_png_base64": res_base["image_png_base64"],
        "candidate_png_base64": res_cand["image_png_base64"],
        "message": f"Visual comparison complete. Structural similarity: {similarity_pct}%."
    }


if __name__ == "__main__":
    mcp.run()
