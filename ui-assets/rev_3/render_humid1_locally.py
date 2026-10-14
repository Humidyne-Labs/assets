#!/usr/bin/env python3
"""
HUMID1 E-Class Device — Local Offline Image Renderer
Renders the pixel-perfect 200x200 bi-tonal splash screen with zero compression.

Outputs generated in current directory:
  1. humid1_cyber_wave.bmp       (200x200, 1-bit monochrome BMP, hardware-ready)
  2. humid1_cyber_wave.png       (200x200, lossless 1:1 PNG)
  3. humid1_cyber_wave_4x.png    (800x800, nearest-neighbor integer scaled preview for desktop)

Requirements:
  pip install pillow
"""

import os
import sys
from PIL import Image

WIDTH = 200
HEIGHT = 200
BUFFER_SIZE = WIDTH * HEIGHT // 8 # 5,000 bytes

# Exact 5,000-byte lossless bitstream (1=White, 0=Black, MSB first)
# Refined design: Edge-to-edge Arduboy Bayer dither wave, 8-bit icons,
# bold HUMID1, E-CLASS DEVICE pill, and enlarged "TELEMETRY // SYS ACTIVE"
BITMAP_HEX = (
    "fffffffffffffffffffffffffffefefeeeeeeeeaaaaaaaaaaa55d5dddddddddd"
    "d55555555555555555555555555554444000c000000000000000000000000000"
    "0000000000000000000002555575757575555555555555555555555555555551"
    "11100000dbffffffffffffffffffffeeeeeeeeeeeeeeaaaaaaaaaaaa8a55dddd"
    "dddddddd5d5555555555555555555555555544440400cfffffffffffffffffbb"
    "bbbbababaaaaaaaaaaaaaaaaaaaaa25557777777575555555555555555555555"
    "5555111111000000dffffffffffffffffffffeeeeeeeeeeaeaeaaaaaaaaaaaaa"
    "aaddddfdfdfdddddd5d555555555555555555555555444444040dfffffffffff"
    "fffffffbbbbabaaaaaaaaaaaaaaaaaaaaaaaaa55777777777775555555555555"
    "555555555151111111100000dfffffffffffffffffffeeeeeeaaaaaaaaaaaaaa"
    "aaaaaaaaaadddfdfffdfdddddd5555555555555555555555454444444400dff0"
    "00000000000000000000000000000000000000000002aa577000000000000000"
    "00000000000000000000000000000000dff31fffffffffffffffffffffffffff"
    "fffffffffffffc62aaddf2000000000000000000000000000000000000000000"
    "2040dff07fffffffffffffffffffffffffffffffffffffffff00aa5770ffffff"
    "ffffffffffffffffffffffffffffffffffff8010dff0ffffffffffffffffffff"
    "ffffffffffffffffffffff80aadfe2ffffffffffffffffffffffffffffffffff"
    "ffffffffa040dff2fffffffffff9ffffffffffffffffffffffffffffffa0aa57"
    "72fffffffffff1ffffffffffffffffffffffffffffffa001dff2fffffffffffd"
    "ff87c3ffffffffffffffffffffffffa0aa5552fef2f679b07dff1399ffffffff"
    "ffffe18cffcf3cffa0009bb2fef2f679b63dff39bfffffffffffffe1843f8618"
    "7fa0aa5552fef2f631b73de37987ffffffffffffefb59ff6cb3fa000cee2fe02"
    "f6b5b7bfe379e3ffffffffffffe1b5d8e4c33fa0aa5552fe02f685b7bfff3939"
    "ffffffffffffef85dfccc33fa0009bb2fef2f685b73fff1399ffffffffffffef"
    "bd9f9edb7fa0aa5552fef266cdb63fff8783ffffffffffffe1bc3f86187fa000"
    "cef2fef30ecdb07fffffffffffffffffffffffffffffffa0aa5552ffffffffff"
    "ffffffffffffffffffffffffffffffffa0409bb2ffffffffffffffffffffffff"
    "ffffffffffffffffffa0aa5552ffffffffffffffffffffffffffffffffffffff"
    "ffffa000cfe2ffffffffffffffffffffffffffffffffffffffffffa0aa5552ff"
    "ffffffffffffffffffffffffffffffffffffffffa0409bb2f000000000000000"
    "00000000000000000000000007a0aa5552ffffffffffffffffffffffffffffff"
    "ffffffffffffa001def2ffffffffffffffffffffffffffffffffffffffffffa0"
    "aa5552ffffffffffffffffffffffffffffffffffffffffffa0409bb2ffffffff"
    "ffffffffffffffffffffffffffffffffffa0aa5552ffffffffffffffffffffff"
    "ffffffffffffffffffffa011cfe2ffffffffffffffffffffffffffffffffffff"
    "ffffffa0aa5552ffffffffffffffffffffffffffffffffffffffffffa0409bb2"
    "ffffffffffffffffffffffffffffffffffffffffffa0aa5552ffffffffffffff"
    "ffffffffffffffffffffffffffffa011def2ffffffffffffffc07fffffffffff"
    "ffffffffffffffa0aa5552ffffffffffffff9f3fffffffffffffffffffffffff"
    "a0519bb2ffffffffffffff3f9fffffffffefffffffffffffffa0aa5552ffffff"
    "ffffffff3b9fffffffffc7ffffffffffffffa011cee2ffffffffffffff3b97ff"
    "ffffff83ffffffffffffffa0aa5552ffffffffffffff3b9fffffffff39ffffff"
    "ffffffffa0519bb2ffffffffffffff3b97ffffffff39ffffffffffffffa0aa55"
    "52ffffffffffffff3b9ffffffffe7cffffffffffffffa011cef2ffffffffffff"
    "ff3b97fffffffe7cffffffffffffffa0aa5552ffffffffffffff3b9ffffffffc"
    "fe7fffffffffffffa0519bb2ffffffffffffff3b97fffffffcee7fffffffffff"
    "ffa0aa5552ffffffffffffff3b9ffffffff9c73fffffffffffffa051cee2ffff"
    "ffffffffff3b97fff7fff9833fffffffffffffa0aa5552ffffffffffffff3b9f"
    "fff7fff3839fffffffffffffa0518ba2ffffffffffffff3b97fff7fff3019fff"
    "ffffffffffa0aa5552ffffffffffffff3b9fffe3ffe701cfffffffffffffa051"
    "cee2ffffffffffffff3b97ffe3ffe600cfffffffffffffa0ea5552ffffffffff"
    "ffff3b9ffe003fe600cfffffffffffffa0519ab2fffffffffffffe7bcfffe1ff"
    "e600cfffffffffffffa0aa5552fffffffffffffcf1e7ffe3ffe701cfffffffff"
    "ffffa051cee2fffffffffffffce0e7fff7fff3839fffffffffffffa0aa5552ff"
    "fffffffffffcc067fff7fff3c79fffffffffffffa0518aa2fffffffffffffcc0"
    "67fff7fff9ff3fffffffffffffa0aa5552fffffffffffffcc067fffffffcfe7f"
    "ffffffffffffa051cee2fffffffffffffce0e7fffffffe7cffffffffffffffa0"
    "ea5552fffffffffffffe71cfffffffff01ffffffffffffffa0518aa2ffffffff"
    "ffffff3f9fffffffffffffffffffffffffa0ba5552ffffffffffffff9f3fffff"
    "ffffffffffffffffffffa0518ea2ffffffffffffffc07fffffffffffffffffff"
    "ffffffa0ea5552ffffffffffffffffffffffffffffffffffffffffffa0518aa2"
    "ffffffffffffffffffffffffffffffffffffffffffa0ab5552ffffffffffffff"
    "ffffffffffffffffffffffffffffa0518aa2ffffffffffffffffffffffffffff"
    "ffffffffffffffa0ea5552ffffffffffffffffffffffffffffffffffffffffff"
    "a0518aa2ffffffffffffffffffffffffffffffffffffffffffa0bb5552ffffff"
    "ffffffffffffffffffffffffffffffffffffa0518aa2ffffffffffffffffffff"
    "ffffffffffffffffffffffa0ea5552ffffffffffffffffffffffffffffffffff"
    "ffffffffa0519bb2ffffffffffffffffffffffffffffffffffffffffffa0fb55"
    "52ffffffffffffffffffffffffffffffffffffffffffa07bdff2ffffffffffff"
    "ffffffffffffffffffffffffffffffa0fb5552ffffffffffffffffffffffffff"
    "ffffffffffffffffa0fb9bb2ffffffffffffffffffffffffffffffffffffffff"
    "ffa0fb5552ffffffffffffffffffffffffffffffffffffffffffa0fbcee2ffff"
    "ffffffffffffffffffffffffffff1fffffffffa0fb5552ffffffffffffffffff"
    "fffffffffffffc1fffffffffa0fb8ba2fffffffffffffffffffffffffffffffc"
    "1fffffffffa0fb5552fffffffffffffffffffffffffffffffd1fffffffffa07b"
    "cee2ffffffffffffffffffffffffffffffff1fffffffffa0fb5552ffffffffe0"
    "fe0e0fc080ff01c1800fff1fffffffffa0fb8aa2ffffffffe0fe0e0fc080ff01"
    "c18003ff1fffffffffa0fb5552ffffffffe0fe0e0fc0807f01c18001ff1fffff"
    "ffffa0fb8aa2ffffffffe0fe0e0fc0807e01c18000ff1fffffffffa0fb5552ff"
    "ffffffe0fe0e0fc0807e01c183807f1fffffffffa0fb8aa2ffffffffe0fe0e0f"
    "c0803c01c183f07f1fffffffffa0fb1512ffffffffe0fe0e0fc0803c01c183f0"
    "3fffffffffffa07b8aa2ffffffffe0000e0fc0801c01c183f83fffffffffffa0"
    "fb5552ffffffffe0000e0fc0821801c183f83fffffffffffa0fb8aa2ffffffff"
    "e0000e0fc0821841c183f83fffffffffffa0fb1112ffffffffe0000e0fc08200"
    "41c183f83fffffffffffa0fb8aa2ffffffffe0000e0fc08300c1c183f03fffff"
    "ffffffa0fb4542ffffffffe0fe0e0fc08300c1c183f03fffffffffffa0fb8aa2"
    "ffffffffe0fe0e07c18300c1c183f07fffffffffffa0fb1112ffffffffe0fe0f"
    "03818381c1c183807fffffffffffa07b8aa2ffffffffe0fe0f00018381c1c180"
    "00ffffffffffffa0fb4442ffffffffe0fe0f800383c1c1c18001ffffffffffff"
    "a0fb8aa2ffffffffe0fe0fc00783c3c1c18003ffffffffffffa0fb1012ffffff"
    "ffe0fe0fe01f83c3c1c1800fffffffffffffa0f38aa2ffffffffffffffffffff"
    "ffffffffffffffffffffffa0fb4442ffffffffffffffffffffffffffffffffff"
    "ffffffffa0fb8aa2ffffffffffffffffffffffffffffffffffffffffffa0fb00"
    "02ffffffffffffffffffffffffffffffffffffffffffa0738aa2ffffffffffff"
    "ffffffffffffffffffffffffffffffa0fb4042ffff8000000000000000000000"
    "000000000001ffffa0fb8aa2ffff0000000000000000000000000000000000ff"
    "ffa0fb0002fffe00000000000000000000000000000000007fffa0738aa2fffe"
    "00000000000000000000000000000000007fffa0fb0002fffe00000000000000"
    "000000000000000000007fffa0db0a22fffe00f8007c180381e0780f83e38c30"
    "f83e007fffa0fb0002fffe00f800fe180783f0fc0fc3e18c31fc3e007fffa073"
    "8aa2fffe00c000c61807c330cc0cc3019c318c30007fffa0fb0002fffe00f870"
    "c01806c3e0f80ce3e1d831803e007fffa0d90222fffe00f870c0180ec1f07c0c"
    "e3e0d831803e007fffa0fb0002fffe00c000c6180fe6318c0cc300f8318c3000"
    "7fffa0738a82fffe00f800fe1f0c63f0fc0fc3e0f031fc3e007fffa0fb0002ff"
    "fe00f8007c1f1c63e0f80f83e07030f83e007fffa0d90222fffe000000000000"
    "00000000000000000000007fffa0fb0002fffe00000000000000000000000000"
    "000000007fffa05188a2fffe00000000000000000000000000000000007fffa0"
    "fb0002fffe00000000000000000000000000000000007fffa0d90222fffe0000"
    "0000000000000000000000000000007fffa0fb0002fffe000000000000000000"
    "00000000000000007fffa0518882ffff00000000000000000000000000000000"
    "00ffffa0fb0002ffff8000000000000000000000000000000001ffffa0510202"
    "ffffffffffffffffffffffffffffffffffffffffffa0bb0002ffffffffffffff"
    "ffffffffffffffffffffffffffffa0518882ffffffffffffffffffffffffffff"
    "ffffffffffffffa0fb0002ffffffffffffffffffffffffffffffffffffffffff"
    "a0510022ffffffffffffffffffffffffffffffffffffffffffa0bb0002ffffff"
    "ffffffffffffffffffffffffffffffffffffa0518882ffffffffffffffffffff"
    "ffffffffffffffffffffffa0eb0002ffffffffffffffffffffffffffffffffff"
    "ffffffffa0510002ffffffffffffffffffffffffffffffffffffffffffa0bb00"
    "02ffffffffffffffffffffffffffffffffffffffffffa0118882ffffffffffff"
    "ffffffffffffffffffffffffffffffa0aa0002ffffffffffffffffffffffffff"
    "ffffffffffffffffa0510022ffffffffffffffffffffffffffffffffffffffff"
    "ffa0aa0002ffffffffffffffffffffffffffffffffffffffffffa0118882ffff"
    "ffffffffffffffffffffffffffffffffffffffa0aa0002ffc041be0cf304041b"
    "df99f0dee1fcf86029e60fffa0410002fff9dfbefcf37f9d899f99e64cccf871"
    "3ceceeffffa0aa0002fff9dfbefc637f9dcdbfbbefeddff8739cecceffffa011"
    "8882fff9c1be0d6b079dcc3fbbe1e1c3f977fcecce0fffa0aa0002fff9c1be0d"
    "0b079c1e7f33f8f3f1f337fcee5e0fffa0400022fff9dfbefd0b7f9d9e7f33ce"
    "739cf0339cee1effffa0aa0002fff9dfbefd9b7f9d9e7f77e673ccf3b13cee1e"
    "ffffa0108882fff9c1820d9b079dce7f77e0f3c1e7987cef3e0fffa0aa0002ff"
    "fffffffffffffffffe67ffffffffffffffffffffa0400002ffffffffffffffff"
    "ffffffffffffffffffffffffffa0aa0002ffffffffffffffffffffffffffffff"
    "ffffffffffffa0008882ffffffffffffffffffffffffffffffffffffffffffa0"
    "aa0002ffffffffffffffffffffffffffffffffffffffffffa0400022ffffffff"
    "ffffffffffffffffffffffffffffffffffa0aa0002ffffffffffffffffffffff"
    "ffffffffffffffffffffa0008882ffffffffffffffffffffffffffffffffffff"
    "ffffffa0aa0002ffffffffffffffffffffffffffffffffffffffffffa0000222"
    "ffffffffffffffffffffffffffffffffffffffffffa0aa0002ffffffffffffff"
    "ffffffffffffffffffffffffffffa00088a2ffffffffffffffffffffffffffff"
    "ffffffffffffffa0aa0002ffffffffffffffffffffffffffffffffffffffffff"
    "a0000222ffffffffffffffffffffffffffffffffffffffffffa0a20002ffffff"
    "ffffffffffffffffffffffffffffffffffffa0008a80ffffffffffffffffffff"
    "ffffffffffffffffffffff80aa0000ffffffffffffffffffffffffffffffffff"
    "ffffffff800002207fffffffffffffffffffffffffffffffffffffffff002200"
    "0200000000000000000000000000000000000000000020008aa31fffffffffff"
    "fffffffffffffffffffffffffffffc60aa000000000000000000000000000000"
    "0000000000000000000002a00000000000000000000000000000000000000000"
    "000022000000000000000000000000000000000000000000000000008aaa0000"
    "0000000000000000000000000000000000000000880000000000000000000000"
    "00000000000000000000000000000a2aaaaaaaabbfffffffffffffffbbaaaaaa"
    "aaaa222222222200000111155555577777777755555555551100000000000000"
    "8aaaaaaaaeeffffffffffffffffffeeeeaaaaaaaaaa8a8888800444455555555"
    "ddddfffffdddd5555555544440000000000082aaaaaaaabbffffffffffffffff"
    "fbbaaaaaaaaaa222222222000011115555555577777777755555555110000000"
    "0000000088aaaaaaaeefffffffffffffffffeeeeaaaaaaaaaa88888888000000"
    "00000000000000000000000000000000000000000000aaaaaaaaabbbbfffffff"
    "ffffffffbbaaaaaaaaaa22220202020001111555555557777777775555555511"
    "1000000000000000"
)

def render_local():
    raw_bytes = bytes.fromhex(BITMAP_HEX)
    if len(raw_bytes) != BUFFER_SIZE:
        print(f"[ERROR] Corrupted bitstream: expected {BUFFER_SIZE} bytes, got {len(raw_bytes)}", file=sys.stderr)
        sys.exit(1)

    # 1. Construct 1-bit native 200x200 image
    img = Image.new("1", (WIDTH, HEIGHT))
    byte_idx = 0
    bit_idx = 7
    for y in range(HEIGHT):
        for x in range(WIDTH):
            bit = (raw_bytes[byte_idx] >> bit_idx) & 1
            img.putpixel((x, y), bit)
            if bit_idx == 0:
                bit_idx = 7
                byte_idx += 1
            else:
                bit_idx -= 1

    # 2. Save 1-bit Monochrome BMP
    bmp_filename = "humid1_cyber_wave.bmp"
    img.save(bmp_filename)

    # 3. Save 1:1 Lossless PNG
    png_filename = "humid1_cyber_wave.png"
    img.save(png_filename)

    # 4. Save 4x integer-scaled preview (800x800) with nearest-neighbor scaling
    # so pixels stay razor sharp on high-resolution computer monitors
    rgb_im = img.convert("RGB")
    preview_4x = rgb_im.resize((WIDTH * 4, HEIGHT * 4), Image.NEAREST)
    preview_filename = "humid1_cyber_wave_4x.png"
    preview_4x.save(preview_filename)

    print("=" * 60)
    print("  HUMID1 E-CLASS DEVICE // LOCAL RENDER COMPLETE")
    print("=" * 60)
    print(f"  [+] 1-Bit BMP (Hardware): {os.path.abspath(bmp_filename)} ({os.path.getsize(bmp_filename)} bytes)")
    print(f"  [+] Lossless PNG (1:1):   {os.path.abspath(png_filename)} ({os.path.getsize(png_filename)} bytes)")
    print(f"  [+] Desktop Preview (4x): {os.path.abspath(preview_filename)} ({os.path.getsize(preview_filename)} bytes)")
    print("=" * 60)

if __name__ == "__main__":
    render_local()