#!/usr/bin/env python3
"""Build the Laser 128 clock software with ca65/ld65 (cc65 package).

Outputs in build/:
  body10.bin / body11.bin  driver body linked at $1000 / $1100 (relocation source)
  reltab.bin, body.inc     relocation offsets (high bytes that differ) and sizes
  stub.bin                 ProDOS clock-slot stub, linked at $D742 (<= 125 bytes)
  CLOCK.SYSTEM             ProDOS SYS file ($2000)
  CLOCK.MAIN               BIN file ($6000), BRUN from STARTUP
  CLOCK.SET                BIN file ($6000), BLOAD + CALL 24576 from SET.CLOCK
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(HERE, 'build')


def cfg(name, seg, start, size):
    p = os.path.join(B, name + '.cfg')
    with open(p, 'w') as f:
        f.write('MEMORY { M: start = $%04X, size = $%04X, fill = no; }\n'
                'SEGMENTS { %s: load = M, type = rw; }\n' % (start, size, seg))
    return p


def run(*a):
    r = subprocess.run(a, cwd=HERE, capture_output=True, text=True)
    if r.returncode:
        sys.exit('%s\n%s%s' % (' '.join(a), r.stdout, r.stderr))


def asm(src, obj, out, config, defines=()):
    run('ca65', '-I', '.', '-I', 'build', *defines, '-o', os.path.join(B, obj), src)
    run('ld65', '-C', config, '-o', os.path.join(B, out), os.path.join(B, obj))
    return open(os.path.join(B, out), 'rb').read()


def main():
    os.makedirs(B, exist_ok=True)
    b10 = asm('clkbody.s', 'b10.o', 'body10.bin', cfg('b10', 'BODY', 0x1000, 0x200))
    b11 = asm('clkbody.s', 'b11.o', 'body11.bin', cfg('b11', 'BODY', 0x1100, 0x200))
    assert len(b10) == len(b11) <= 511, 'body must fit in 511 bytes (last byte = checksum): %d' % len(b10)
    rel = [i for i in range(len(b10)) if b10[i] != b11[i]]
    assert all(b11[i] - b10[i] == 1 for i in rel), 'unexpected relocation difference'
    open(os.path.join(B, 'reltab.bin'), 'wb').write(b''.join(bytes([i & 255, i >> 8]) for i in rel))
    open(os.path.join(B, 'body.inc'), 'w').write('BODYLEN = %d\nRELCNT = %d\n' % (len(b10), len(rel)))
    stub = asm('stub.s', 'stub.o', 'stub.bin', cfg('stub', 'STUB', 0xD742, 125))
    sysf = asm('clocksys.s', 'sys.o', 'CLOCK.SYSTEM', cfg('sys', 'SYS', 0x2000, 0x1000))
    mainf = asm('clockmain.s', 'main.o', 'CLOCK.MAIN', cfg('main', 'BIN', 0x6000, 0x1000))
    setf = asm('clockset.s', 'set.o', 'CLOCK.SET', cfg('set', 'BIN', 0x6000, 0x1000))
    print('body %d bytes (%d relocations), stub %d/125 bytes, CLOCK.SYSTEM %d, CLOCK.MAIN %d, CLOCK.SET %d bytes'
          % (len(b10), len(rel), len(stub), len(sysf), len(mainf), len(setf)))


if __name__ == '__main__':
    main()
