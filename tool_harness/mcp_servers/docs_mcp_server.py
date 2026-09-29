#!/usr/bin/env python3
"""
Hardware Assets, Datasheets & Project Documentation MCP Server.
Provides targeted search, page-level text extraction, PDF visual page rendering,
and dynamic hooks for adding/listing/removing asset directories at runtime.
"""

import os
import json
import base64
from pathlib import Path
from mcp.server.fastmcp import FastMCP
import fitz  # PyMuPDF

mcp = FastMCP("Project-Docs-Server")

HARNESS_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DOCS_ROOT = Path(os.environ.get("DOCS_ROOT", HARNESS_DIR / "docs")).resolve()
BSP_DOCS_ROOT = Path(r"C:\Users\Matt\Documents\GitHub\esp32-s3_bsp\docs").resolve()
CONFIG_FILE = HARNESS_DIR / "config" / "extra_asset_dirs.json"

# In-memory set for dynamically registered asset directories
_DYNAMIC_DIRS: set[Path] = set()


def _load_persisted_dynamic_dirs():
    """Loads persisted extra asset directories from config JSON file."""
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            for p in data.get("directories", []):
                path_obj = Path(p).resolve()
                if path_obj.exists():
                    _DYNAMIC_DIRS.add(path_obj)
        except Exception:
            pass


def _save_persisted_dynamic_dirs():
    """Saves dynamically added asset directories to config JSON file."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    paths_list = [str(p) for p in sorted(_DYNAMIC_DIRS)]
    CONFIG_FILE.write_text(json.dumps({"directories": paths_list}, indent=2), encoding="utf-8")


_load_persisted_dynamic_dirs()


def _get_docs_roots() -> list[Path]:
    roots = []
    # 1. Default Harness Docs
    if DEFAULT_DOCS_ROOT.exists():
        roots.append(DEFAULT_DOCS_ROOT)

    # 2. BSP Docs
    if BSP_DOCS_ROOT.exists() and BSP_DOCS_ROOT not in roots:
        roots.append(BSP_DOCS_ROOT)

    # 3. Environment Variable EXTRA_DOCS_DIRS / ASSETS_DIRS
    extra_env = os.environ.get("EXTRA_DOCS_DIRS") or os.environ.get("ASSETS_DIRS")
    if extra_env:
        for delimiter in (";", ":", ","):
            if delimiter in extra_env:
                parts = extra_env.split(delimiter)
                break
        else:
            parts = [extra_env]

        for p in parts:
            p_clean = p.strip()
            if p_clean:
                p_obj = Path(p_clean).resolve()
                if p_obj.exists() and p_obj not in roots:
                    roots.append(p_obj)

    # 4. Dynamically registered asset directories
    for dyn_path in sorted(_DYNAMIC_DIRS):
        if dyn_path.exists() and dyn_path not in roots:
            roots.append(dyn_path)

    if not roots:
        roots.append(DEFAULT_DOCS_ROOT)

    return roots


@mcp.tool()
def add_asset_directory(directory_path: str) -> dict:
    """Dynamically registers a new asset or documentation root directory at runtime.
    The directory will immediately be included in asset searches, PDF reading, and image rendering,
    and will persist across MCP server restarts.

    Args:
        directory_path: Absolute or relative file system path to the asset folder to include.
    """
    target = Path(directory_path).resolve()
    if not target.exists():
        return {"status": "error", "message": f"Directory '{directory_path}' does not exist on disk."}
    if not target.is_dir():
        return {"status": "error", "message": f"Path '{directory_path}' is a file, not a directory."}

    _DYNAMIC_DIRS.add(target)
    _save_persisted_dynamic_dirs()

    # Count assets inside newly added directory
    valid_exts = {".pdf", ".md", ".txt", ".png", ".jpg", ".jpeg", ".json", ".py"}
    asset_count = sum(1 for f in target.rglob("*") if f.is_file() and f.suffix.lower() in valid_exts)

    return {
        "status": "success",
        "message": f"Successfully added asset directory: {target}",
        "registered_directory": str(target),
        "discovered_assets": asset_count
    }


@mcp.tool()
def list_asset_directories() -> list[dict]:
    """Lists all currently active asset search directories, including default, environment-specified, and dynamically added folders."""
    roots = _get_docs_roots()
    valid_exts = {".pdf", ".md", ".txt", ".png", ".jpg", ".jpeg", ".json", ".py"}

    result = []
    for r in roots:
        is_dynamic = r in _DYNAMIC_DIRS
        is_default = (r == DEFAULT_DOCS_ROOT or r == BSP_DOCS_ROOT)
        count = sum(1 for f in r.rglob("*") if f.is_file() and f.suffix.lower() in valid_exts) if r.exists() else 0

        source_type = "default" if is_default else ("dynamic" if is_dynamic else "env_variable")
        result.append({
            "directory": str(r),
            "exists": r.exists(),
            "source": source_type,
            "asset_files_count": count
        })

    return result


@mcp.tool()
def remove_asset_directory(directory_path: str) -> dict:
    """Removes a dynamically registered asset directory from active searches."""
    target = Path(directory_path).resolve()
    if target in _DYNAMIC_DIRS:
        _DYNAMIC_DIRS.remove(target)
        _save_persisted_dynamic_dirs()
        return {"status": "success", "message": f"Removed asset directory: {target}"}

    return {"status": "error", "message": f"Directory '{directory_path}' was not in the dynamic registration list."}


@mcp.tool()
def list_available_docs() -> list[dict]:
    """Lists all available datasheets, markdown notes, schematics, and project documentation files across all registered asset directories."""
    valid_exts = {".pdf", ".md", ".txt", ".png", ".jpg", ".jpeg", ".json", ".py"}
    docs_list = []

    for root in _get_docs_roots():
        if not root.exists():
            continue
        for f in root.rglob("*"):
            if f.is_file() and f.suffix.lower() in valid_exts:
                try:
                    rel_path = str(f.relative_to(root))
                except ValueError:
                    rel_path = f.name
                docs_list.append({
                    "root": str(root),
                    "file": rel_path,
                    "extension": f.suffix.lower()
                })

    return docs_list


@mcp.tool()
def search_docs_text(keyword: str, max_results: int = 10) -> list[dict]:
    """Searches for register names, hex addresses, pin numbers, or keywords across all PDFs, Markdown, and TXT files across all registered asset directories."""
    results = []
    keyword_lower = keyword.lower()

    for root in _get_docs_roots():
        if not root.exists():
            continue

        # 1. Search Markdown & Text files
        for txt_file in root.rglob("*"):
            if txt_file.is_file() and txt_file.suffix.lower() in (".md", ".txt", ".json", ".py"):
                try:
                    content = txt_file.read_text(encoding="utf-8", errors="ignore")
                    if keyword_lower in content.lower():
                        lines = content.splitlines()
                        matches = [ln.strip() for ln in lines if keyword_lower in ln.lower()]
                        results.append({
                            "root": str(root),
                            "file": str(txt_file.relative_to(root)),
                            "page": 1,
                            "type": "text",
                            "snippet": " | ".join(matches[:3])
                        })
                        if len(results) >= max_results:
                            return results
                except Exception:
                    continue

        # 2. Search PDF files page-by-page
        for pdf_file in root.rglob("*.pdf"):
            if not pdf_file.is_file():
                continue
            try:
                doc = fitz.open(pdf_file)
                for page_idx in range(len(doc)):
                    page = doc[page_idx]
                    text = page.get_text()
                    if keyword_lower in text.lower():
                        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
                        match_context = [ln for ln in lines if keyword_lower in ln.lower()]

                        results.append({
                            "root": str(root),
                            "file": str(pdf_file.relative_to(root)),
                            "page": page_idx + 1,
                            "type": "pdf",
                            "snippet": " | ".join(match_context[:3])
                        })
                        if len(results) >= max_results:
                            return results
            except Exception:
                continue

    return results


@mcp.tool()
def read_doc_file(relative_path: str) -> str:
    """Reads the full text contents of a Markdown or TXT documentation file."""
    for root in _get_docs_roots():
        target = root / relative_path
        if not target.exists():
            matches = list(root.rglob(Path(relative_path).name))
            if matches:
                target = matches[0]

        if target.exists() and target.is_file():
            return f"/* === Document: {target.relative_to(root)} === */\n\n" + target.read_text(encoding="utf-8", errors="ignore")

    return f"Error: Document file '{relative_path}' not found across documentation roots."


@mcp.tool()
def read_pdf_page(pdf_relative_path: str, page_number: int) -> str:
    """Reads the complete text content of a specific page of a PDF datasheet or schematic document.
    Always call search_docs_text first to find the target page number.
    """
    for root in _get_docs_roots():
        pdf_path = root / pdf_relative_path
        if not pdf_path.exists():
            matches = list(root.rglob(Path(pdf_relative_path).name))
            if matches:
                pdf_path = matches[0]

        if pdf_path.exists() and pdf_path.is_file():
            try:
                doc = fitz.open(pdf_path)
                if page_number < 1 or page_number > len(doc):
                    return f"Page {page_number} out of range (Total pages: {len(doc)})."
                page = doc[page_number - 1]
                return f"--- {pdf_relative_path} (Page {page_number}/{len(doc)}) ---\n" + page.get_text()
            except Exception as exc:
                return f"Error opening PDF: {exc}"

    return f"Error: PDF file '{pdf_relative_path}' not found."


@mcp.tool()
def render_pdf_page_to_image(pdf_relative_path: str, page_number: int, dpi: int = 144) -> dict:
    """Renders a PDF page (schematic diagram, timing chart, pinout table) into a high-resolution PNG image
    encoded as base64 for visual/multimodal inspection.
    """
    for root in _get_docs_roots():
        pdf_path = root / pdf_relative_path
        if not pdf_path.exists():
            matches = list(root.rglob(Path(pdf_relative_path).name))
            if matches:
                pdf_path = matches[0]

        if pdf_path.exists() and pdf_path.is_file():
            try:
                doc = fitz.open(pdf_path)
                if page_number < 1 or page_number > len(doc):
                    return {"error": f"Page {page_number} out of range (Total pages: {len(doc)})."}

                page = doc[page_number - 1]
                pix = page.get_pixmap(dpi=dpi)
                img_bytes = pix.tobytes("png")
                b64_img = base64.b64encode(img_bytes).decode("utf-8")

                return {
                    "file": pdf_relative_path,
                    "page": page_number,
                    "image_png_base64": b64_img,
                    "message": f"Rendered page {page_number} at {dpi} DPI."
                }
            except Exception as exc:
                return {"error": f"Failed to render PDF page: {exc}"}

    return {"error": f"File '{pdf_relative_path}' not found."}


if __name__ == "__main__":
    mcp.run()
