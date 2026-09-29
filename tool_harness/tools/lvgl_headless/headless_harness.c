/* ***************************************************************************
 * LVGL v9 Headless UI Snapshot Generator Harness
 * Compiles natively on Host (MSVC / GCC / Clang) to render UI candidate blocks
 * into a full 200x200 (or custom resolution) PNG image framebuffer.
 * ************************************************************************* */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include "lvgl.h"

#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"

// Display geometry definitions
#ifndef DISP_HOR_RES
#define DISP_HOR_RES 200
#endif

#ifndef DISP_VER_RES
#define DISP_VER_RES 200
#endif

#ifndef LV_DPI_DEF
#define LV_DPI_DEF 188
#endif

static const char *OUTPUT_FILENAME = "ui_snapshot.png";

// Raw pixel buffer for screen capture (ARGB8888 = 4 bytes per pixel)
static uint8_t g_screen_capture[DISP_HOR_RES * DISP_VER_RES * 4];

// Flush callback: captures rendered dirty regions into full-frame capture buffer
static void headless_flush_cb(lv_display_t *disp, const lv_area_t *area, uint8_t *px_map) {
    int32_t width  = lv_area_get_width(area);
    int32_t height = lv_area_get_height(area);

    for (int32_t y = 0; y < height; y++) {
        int32_t dst_y = area->y1 + y;
        int32_t dst_x = area->x1;

        if (dst_y >= DISP_VER_RES || dst_x >= DISP_HOR_RES) continue;

        uint32_t *src_row = (uint32_t *)(px_map + (y * width * 4));
        uint32_t *dst_row = (uint32_t *)(g_screen_capture + ((dst_y * DISP_HOR_RES + dst_x) * 4));

        for (int32_t x = 0; x < width && (dst_x + x) < DISP_HOR_RES; x++) {
            dst_row[x] = src_row[x];
        }
    }

    lv_display_flush_ready(disp);
}

// Candidate UI construction function (injected dynamically by render_ui_snapshot tool)
// USER_CODE_MARKER_START
void build_ui_candidate(void) {
    lv_obj_t *scr = lv_screen_active();
    lv_obj_set_style_bg_color(scr, lv_color_hex(0x1E1E2E), 0);

    lv_obj_t *card = lv_obj_create(scr);
    lv_obj_set_size(card, 180, 180);
    lv_obj_center(card);
    lv_obj_set_style_bg_color(card, lv_color_hex(0x282A36), 0);
    lv_obj_set_style_border_color(card, lv_color_hex(0xBD93F9), 0);
    lv_obj_set_style_border_width(card, 2, 0);

    lv_obj_t *title = lv_label_create(card);
    lv_label_set_text(title, "LVGL 9 Headless");
    lv_obj_set_style_text_color(title, lv_color_hex(0xF8F8F2), 0);
    lv_obj_align(title, LV_ALIGN_TOP_MID, 0, 10);
}
// USER_CODE_MARKER_END

int main(void) {
    // Initialize core LVGL
    lv_init();

    // Allocate draw buffer (ARGB8888)
    const size_t buf_size = DISP_HOR_RES * DISP_VER_RES * 4;
    uint8_t *draw_buf = (uint8_t *)malloc(buf_size);
    if (!draw_buf) {
        fprintf(stderr, "Fatal: Out of memory allocating draw buffer.\n");
        return 1;
    }

    // Register virtual display
    lv_display_t *disp = lv_display_create(DISP_HOR_RES, DISP_VER_RES);
    lv_display_set_dpi(disp, LV_DPI_DEF);
    lv_display_set_color_format(disp, LV_COLOR_FORMAT_ARGB8888);
    lv_display_set_buffers(disp, draw_buf, NULL, buf_size, LV_DISPLAY_RENDER_MODE_FULL);
    lv_display_set_flush_cb(disp, headless_flush_cb);

    // Build the candidate UI
    build_ui_candidate();

    // Advance tick and force draw update
    lv_tick_inc(10);
    lv_refr_now(disp);

    // Convert ARGB8888 -> RGBA for PNG export
    for (size_t i = 0; i < sizeof(g_screen_capture); i += 4) {
        uint8_t b = g_screen_capture[i + 0];
        uint8_t r = g_screen_capture[i + 2];
        g_screen_capture[i + 0] = r;
        g_screen_capture[i + 2] = b;
        g_screen_capture[i + 3] = 0xFF;
    }

    int ret = stbi_write_png(OUTPUT_FILENAME, DISP_HOR_RES, DISP_VER_RES, 4, g_screen_capture, DISP_HOR_RES * 4);
    if (ret) {
        printf("[OK] Framebuffer exported cleanly to: %s\n", OUTPUT_FILENAME);
    } else {
        fprintf(stderr, "[ERROR] Failed to encode PNG snapshot.\n");
    }

    free(draw_buf);
    return ret ? 0 : 1;
}
