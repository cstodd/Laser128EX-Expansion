"""Decode the graphics lookup table in the upper 4K of the Laser 128 video ROM (vt27-0706-0).

Table address (inferred) = $1000 | A11<<11 | data<<3 | slot, slot 0-7.
For each (half, slot) print which data bits the output depends on and a sample.
Usage: python3 -I videorom.py laser128-video-VT27-0706-0.bin
"""
import sys
d = open(sys.argv[1], 'rb').read()
def tab(h, m): return [d[0x1000 + h*0x800 + v*8 + m] for v in range(256)]
for h in (0, 1):
    for m in range(8):
        t = tab(h, m)
        deps = [b for b in range(8) if any(t[v] != t[v ^ (1 << b)] for v in range(256))]
        print(f"half{h} slot{m}: data bits {deps}; v=0..15:", " ".join(f"{x:02X}" for x in t[:16]))
