---
name: lvgl9-ui-virtualization
description: Guidelines, C code patterns, and headless rendering workflows for designing and snapshot-testing LVGL 9 UI widgets and layouts.
---

# LVGL v9 UI Virtualization & Headless Snapshot Skill

## Overview
This skill provides C code design patterns and headless rendering workflows for building LVGL v9 (v9.6.0) UI widgets and verifying them using the `lvgl-virtualization` (`render_ui_snapshot`) and `lvgl-diff` (`compare_ui_snapshots`) MCP tools.

## C Code Injection Architecture

When invoking `render_ui_snapshot(c_ui_code, width, height)`, the C snippet is injected directly into the headless host harness (`headless_harness.c`) inside `build_ui_candidate`:

```c
void build_ui_candidate(void) {
    lv_obj_t *scr = lv_screen_active();
    
    /* YOUR INJECTED C_UI_CODE EXECUTES HERE */
}
```

### Core Directives & Constraints:
1. **Pre-declared Screen Pointer**: The active screen pointer `scr` (`lv_obj_t *scr`) is pre-initialized. Target `scr` or child objects.
2. **No Boilerplate Required**: Do NOT include `main()`, `lv_init()`, or `#include "lvgl.h"`.
3. **LVGL v9 API Compliance**: Use LVGL v9 APIs (`lv_button_create`, `lv_label_create`, `lv_screen_active()`, `lv_color_hex()`, `lv_obj_set_style_*`). Do NOT use v8 deprecated names (`lv_btn_create`, `lv_scr_act`).

---

## Reference C UI Code Snippets

### 1. Dark Mode Card & Title Header
```c
// Set screen background color
lv_obj_set_style_bg_color(scr, lv_color_hex(0x1E1E2E), 0);

// Create container card
lv_obj_t *card = lv_obj_create(scr);
lv_obj_set_size(card, 180, 180);
lv_obj_center(card);
lv_obj_set_style_bg_color(card, lv_color_hex(0x282A36), 0);
lv_obj_set_style_border_color(card, lv_color_hex(0xBD93F9), 0);
lv_obj_set_style_border_width(card, 2, 0);
lv_obj_set_style_radius(card, 12, 0);

// Add title text
lv_obj_t *title = lv_label_create(card);
lv_label_set_text(title, "ESP32-S3 BSP");
lv_obj_set_style_text_color(title, lv_color_hex(0x50FA7B), 0);
lv_obj_align(title, LV_ALIGN_TOP_MID, 0, 10);
```

### 2. Action Button with Centered Label
```c
lv_obj_set_style_bg_color(scr, lv_color_hex(0x121212), 0);

lv_obj_t *card = lv_obj_create(scr);
lv_obj_set_size(card, 180, 180);
lv_obj_center(card);
lv_obj_set_style_bg_color(card, lv_color_hex(0x1E1E1E), 0);
lv_obj_set_style_border_color(card, lv_color_hex(0x333333), 0);

// Action button
lv_obj_t *btn = lv_button_create(card);
lv_obj_set_size(btn, 130, 36);
lv_obj_align(btn, LV_ALIGN_BOTTOM_MID, 0, -10);
lv_obj_set_style_bg_color(btn, lv_color_hex(0x2979FF), 0);
lv_obj_set_style_radius(btn, 18, 0);

lv_obj_t *btn_lbl = lv_label_create(btn);
lv_label_set_text(btn_lbl, "REBOOT");
lv_obj_set_style_text_color(btn_lbl, lv_color_hex(0xFFFFFF), 0);
lv_obj_center(btn_lbl);
```

### 3. Arc Progress Meter & Percentage Gauge
```c
lv_obj_set_style_bg_color(scr, lv_color_hex(0x0F172A), 0);

// Create Progress Arc
lv_obj_t *arc = lv_arc_create(scr);
lv_obj_set_size(arc, 150, 150);
lv_obj_center(arc);
lv_arc_set_rotation(arc, 135);
lv_arc_set_bg_angles(arc, 0, 270);
lv_arc_set_value(arc, 75);

// Style arc track & indicator
lv_obj_set_style_arc_color(arc, lv_color_hex(0x38BDF8), LV_PART_INDICATOR);
lv_obj_set_style_arc_width(arc, 12, LV_PART_INDICATOR);
lv_obj_set_style_arc_color(arc, lv_color_hex(0x334155), LV_PART_MAIN);
lv_obj_set_style_arc_width(arc, 12, LV_PART_MAIN);

// Centered percentage label
lv_obj_t *val_lbl = lv_label_create(arc);
lv_label_set_text(val_lbl, "75%");
lv_obj_set_style_text_color(val_lbl, lv_color_hex(0xF8FAFC), 0);
lv_obj_center(val_lbl);
```

### 4. Flex Row/Column Layout for Telemetry
```c
lv_obj_set_style_bg_color(scr, lv_color_hex(0x18181B), 0);

// Flex Container
lv_obj_t *cont = lv_obj_create(scr);
lv_obj_set_size(cont, 190, 190);
lv_obj_center(cont);
lv_obj_set_flex_flow(cont, LV_FLEX_FLOW_COLUMN);
lv_obj_set_flex_align(cont, LV_FLEX_ALIGN_START, LV_FLEX_ALIGN_CENTER, LV_FLEX_ALIGN_CENTER);

// Metric 1: Temperature
lv_obj_t *b1 = lv_obj_create(cont);
lv_obj_set_size(b1, 160, 45);
lv_obj_set_style_bg_color(b1, lv_color_hex(0x27272A), 0);
lv_obj_t *t1 = lv_label_create(b1);
lv_label_set_text(t1, "TEMP: 24.5 C");
lv_obj_set_style_text_color(t1, lv_color_hex(0xF43F5E), 0);
lv_obj_align(t1, LV_ALIGN_LEFT_MID, 5, 0);
```

---

## MCP Tool Invocation Recipes

### 1. Rendering UI Snapshots (`render_ui_snapshot`)
```python
result = call_mcp_tool(
    ServerName="lvgl-virtualization",
    ToolName="render_ui_snapshot",
    Arguments={
        "c_ui_code": "lv_obj_t *lbl = lv_label_create(scr); lv_label_set_text(lbl, 'LVGL 9'); lv_obj_center(lbl);",
        "width": 200,
        "height": 200
    }
)
```

### 2. Computing Visual Regression & SSIM Heatmaps (`compare_ui_snapshots`)
```python
diff_res = call_mcp_tool(
    ServerName="lvgl-diff",
    ToolName="compare_ui_snapshots",
    Arguments={
        "baseline_code": "lv_obj_t *b = lv_button_create(scr); lv_label_set_text(lv_label_create(b), 'Save');",
        "candidate_code": "lv_obj_t *b = lv_button_create(scr); lv_label_set_text(lv_label_create(b), 'Commit');",
        "width": 200,
        "height": 200
    }
)
```
