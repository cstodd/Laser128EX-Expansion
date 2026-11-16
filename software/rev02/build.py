#!/usr/bin/env python3
"""Build the rev 0.2 (DS3234) software and dist/LASERCLOCK2.po."""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(HERE, 'build')
sys.path.insert(0, os.path.join(HERE, '..', 'rev01'))
import mkdisk

def cfg(name, seg, start, size):
    p = os.path.join(B, name + '.cfg')
    open(p, 'w').write('MEMORY { M: start = $%04X, size = $%04X, fill = no; }\n'
                       'SEGMENTS { %s: load = M, type = rw; }\n' % (start, size, seg))
    return p

def asm(src, out, cfgp, lbl=False):
    obj = os.path.join(B, out + '.o')
    subprocess.check_call(['ca65', '-I', HERE, '-l', os.path.join(B, out + '.lst'), '-o', obj, os.path.join(HERE, src)], cwd=HERE)
    cmd = ['ld65', '-C', cfgp, '-o', os.path.join(B, out), obj]
    if lbl: cmd += ['-Ln', os.path.join(B, out + '.lbl')]
    subprocess.check_call(cmd)
    return open(os.path.join(B, out), 'rb').read()

def main():
    os.makedirs(B, exist_ok=True)
    drv = asm('clkdrv.s', 'clkdrv.bin', cfg('drv', 'DRV', 0xD742, 125), lbl=True)
    lbl = {l.split()[2].lstrip('.'): int(l.split()[1], 16) for l in open(os.path.join(B, 'clkdrv.bin.lbl'))}
    open(os.path.join(B, 'drvinfo.inc'), 'w').write('DRV_LEN = %d\nKEYOP_OFS = %d\nKEYREV_OFS = %d\n'
                                                    % (len(drv), lbl['KEYOP_OFS'], lbl['KEYREV_OFS']))
    sysf = asm('clocksys.s', 'CLOCK.SYSTEM', cfg('sys', 'SYS', 0x2000, 0x1000))
    setf = asm('clockset.s', 'CLOCK.SET', cfg('set', 'BIN', 0x6000, 0x1000))
    test = asm('cardtest.s', 'CARDTEST', cfg('test', 'BIN', 0x6000, 0x0F00))
    bas = lambda n: mkdisk.tokenize(open(os.path.join(HERE, 'basic', n + '.bas')).read())
    files = [('CLOCK.SYSTEM', 0xFF, 0x2000, sysf), ('CLOCK.SET', 0x06, 0x6000, setf),
             ('CARDTEST', 0x06, 0x6000, test), ('SET.CLOCK', 0xFC, 0x0801, bas('SET.CLOCK')),
             ('CARD.TEST', 0xFC, 0x0801, bas('CARD.TEST'))]
    img = mkdisk.build_image('LASERCLOCK', files)
    back = mkdisk.read_image(img)
    os.makedirs(os.path.join(HERE, 'dist'), exist_ok=True)
    for n, t, a, d in files:
        assert back[n] == (t, a, d), n
        if t != 0xFC: open(os.path.join(HERE, 'dist', n), 'wb').write(d)
        print('%-13s %5d bytes ok' % (n, len(d)))
    print('clock driver: %d bytes (ProDOS slot: 125)' % len(drv))
    out = os.path.join(HERE, 'dist', 'LASERCLOCK2.po')
    open(out, 'wb').write(img)
    print('wrote', out)

if __name__ == '__main__':
    main()
