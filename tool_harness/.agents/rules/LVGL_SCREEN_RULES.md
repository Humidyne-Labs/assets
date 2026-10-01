# Predefined Rules for LVGL Screen Generation (1.54" 200x200 Monochrome e-Paper)

## 1. Hardware & Display Specifications
- **Display Resolution**: 200 x 200 pixels (1:1 square aspect ratio).
- **Pixel Density (DPI)**: 188 DPI (1 pixel ≈ 0.135 mm).
- **Color Format**: 1-bit Monochrome (`LV_COLOR_FORMAT_I1`). Pure black (`lv_color_black()`) and pure white (`lv_color_white()`).
- **Minimum Readable Font Size**: 14pt (≥ 14 px font height, e.g. `LV_FONT_MONTSERRAT_14`). Never use 8pt, 10pt, or 12pt text for body or labels.

---

## 2. Screen Layout & Spatial Budget (200 px Vertical Height)
- **Header Region (Y = 0 to 20 px)**:
  - Height: 20 px (or 22 px max).
  - Background: White with a 1 px solid black bottom border (`LV_BORDER_SIDE_BOTTOM`).
  - Title Font: 14pt bold / ALL CAPS, centered horizontally (`LV_ALIGN_CENTER`).
- **Body / Main Content Region (Y = 22 to 148 px)**:
  - Total Available Height: ~126 px.
  - Used for centered telemetry cards, gauge arcs, status icons, or QR codes.
- **Footer / Action Region (Y = 150 to 200 px)**:
  - Total Available Height: 50 px.
  - Position primary info label (e.g. `PAIRING PIN: xxxx`) at `Y = 150`.
  - Position secondary hint label (e.g. `Scan in App | Hold Boot: Reset`) at `Y = 170`.
  - Maintain a minimum 4 px vertical clearance between stacked labels.

---

## 3. Typography & Text Styling
- **Minimum Size Mandate**: Minimum font height is 14 px.
- **Contrast**: Text color MUST be `lv_color_black()` on white backgrounds, or `lv_color_white()` on black container boxes.
- **Horizontal Bounds**: Keep text labels centered (`LV_ALIGN_TOP_MID` or `LV_ALIGN_CENTER`) or padded by at least 4 px from left/right screen edges.

---

## 4. QR Code Generation & Whole-Factor Scaling Rules
- **Whole-Factor Scaling Mandate**: QR code canvases MUST be dimensioned using exact integer multiples of total modules:
  $$\text{Canvas Size} = (\text{Base Modules} + 8 \text{ Quiet Zone}) \times \text{Scale Factor}$$
- **Minimum Scale Factor**: Module scale factor MUST be ≥ 3 px per module on 188 DPI e-Paper to prevent ink capsule bleeding.
- **Standard Dimensioning**:
  - For standard ~75 byte JSON provisioning payloads (Version 4/5 = 41 total modules with quiet zone):
    - Scale 3x = **123 x 123 px** canvas.
    - Scale 4x = **164 x 164 px** canvas.
  - Always use `bsp_prov_calc_qr_code_size(pop, max_boundary, 3)` or `bsp_prov_render_qr_code(scr, target_size, pop)` to auto-snap canvas size.

---

## 5. 1-Bit E-Paper Visual Styling Rules
- **No Gray Opacity**: Set opacity to 100% (`LV_OPA_COVER`). Never use alpha blending or partial opacity (`LV_OPA_50`).
- **Borders & Radii**: Use 1 px solid black borders (`lv_color_black()`). Prefer sharp corners (`radius = 0`) or subtle corners (`radius = 2..4 px`).
- **Thread Safety**: Wrap all LVGL UI creation, modification, and screen cleaning calls between `bsp_lvgl_lock()` and `bsp_lvgl_unlock()`.

---

## 6. Template Code Structure

```c
void ui_render_standard_screen(const char *title_text, const char *main_info, const char *hint_text)
{
    bsp_lvgl_lock();

    lv_obj_t *scr = lv_screen_active();
    lv_obj_clean(scr);
    lv_obj_set_style_bg_color(scr, lv_color_white(), 0);

    // 1. Header (200x20 px)
    lv_obj_t *header = lv_obj_create(scr);
    lv_obj_set_size(header, 200, 20);
    lv_obj_align(header, LV_ALIGN_TOP_MID, 0, 0);
    lv_obj_set_style_bg_color(header, lv_color_white(), 0);
    lv_obj_set_style_border_color(header, lv_color_black(), 0);
    lv_obj_set_style_border_width(header, 1, 0);
    lv_obj_set_style_border_side(header, LV_BORDER_SIDE_BOTTOM, 0);
    lv_obj_set_style_radius(header, 0, 0);
    lv_obj_set_style_pad_all(header, 1, 0);

    lv_obj_t *lbl_title = lv_label_create(header);
    lv_label_set_text(lbl_title, title_text ? title_text : "STATUS");
    lv_obj_set_style_text_color(lbl_title, lv_color_black(), 0);
    lv_obj_align(lbl_title, LV_ALIGN_CENTER, 0, 0);

    // 2. Main Body Content (Y = 22..148)
    lv_obj_t *lbl_main = lv_label_create(scr);
    lv_label_set_text(lbl_main, main_info ? main_info : "READY");
    lv_obj_set_style_text_color(lbl_main, lv_color_black(), 0);
    lv_obj_align(lbl_main, LV_ALIGN_CENTER, 0, -10);

    // 3. Footer Hints (Y = 150..170)
    lv_obj_t *lbl_hint = lv_label_create(scr);
    lv_label_set_text(lbl_hint, hint_text ? hint_text : "Press BOOT to continue");
    lv_obj_set_style_text_color(lbl_hint, lv_color_black(), 0);
    lv_obj_align(lbl_hint, LV_ALIGN_TOP_MID, 0, 160);

    bsp_lvgl_unlock();
}
```
