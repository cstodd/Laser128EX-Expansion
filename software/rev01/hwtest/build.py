#!/usr/bin/env python3
"""Build the hardware test programs and dist/LASERTEST.po (BRUN them from BASIC.SYSTEM)."""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
SW = os.path.dirname(HERE)
sys.path.insert(0, SW)
import mkdisk

OUT = os.path.join(HERE, 'build')
os.makedirs(OUT, exist_ok=True)
CFG = os.path.join(OUT, 'bin.cfg')
open(CFG, 'w').write('MEMORY { M: start = $6000, size = $3000, fill = no; }\n'
                     'SEGMENTS { BIN: load = M, type = rw; }\n')

def asm(src, name):
    obj = os.path.join(OUT, name + '.o')
    out = os.path.join(OUT, name)
    subprocess.check_call(['ca65', '-I', HERE, '-l', os.path.join(OUT, name + '.lst'), '-o', obj,
                           os.path.join(HERE, src)])
    subprocess.check_call(['ld65', '-C', CFG, '-o', out, obj])
    return open(out, 'rb').read()

irq = asm('irqtest.s', 'IRQ.TEST')
can = asm('lccanary.s', 'LC.CANARY')
files = [('IRQ.TEST', 0x06, 0x6000, irq), ('LC.CANARY', 0x06, 0x6000, can)]
img = mkdisk.build_image('LASERTEST', files)
back = mkdisk.read_image(img)
for n, t, a, d in files:
    assert back[n] == (t, a, d), n
    print('%-10s %5d bytes ok' % (n, len(d)))
dst = os.path.join(SW, 'dist', 'LASERTEST.po')
open(dst, 'wb').write(img)
print('wrote', dst)
