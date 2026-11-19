#!/usr/bin/env python3
"""Build dist/LASERCLOCK2.po as a bootable ProDOS 2.4 disk from the assembled programs in dist/ and the
Applesoft sources in basic/. Run by build.py after assembling; can also be run on its own (needs no ca65).

Order on the disk: PRODOS, CLOCK.SYSTEM (the first .SYSTEM file, so ProDOS runs it; it installs the driver
and chains to BASIC.SYSTEM), BASIC.SYSTEM, the utilities, and a STARTUP that lists them."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import prodisk

STARTUP = '''
10 PRINT : PRINT "LASER 128 CLOCK CARD UTILITIES (REV 0.2)"
20 PRINT : PRINT "  RUN SET.CLOCK   SHOW OR SET THE CLOCK"
30 PRINT "  RUN CARD.TEST   TEST THE CARD"
40 PRINT : END
'''

def build():
    rd = lambda n: open(os.path.join(HERE, 'dist', n), 'rb').read()
    bas = lambda n: prodisk.tokenize(open(os.path.join(HERE, 'basic', n + '.bas')).read())
    img = prodisk.boot_image(
        'LASERCLOCK',
        [('CLOCK.SET', 0x06, 0x6000, rd('CLOCK.SET')), ('CARDTEST', 0x06, 0x6000, rd('CARDTEST')),
         ('SET.CLOCK', 0xFC, 0x0801, bas('SET.CLOCK')), ('CARD.TEST', 0xFC, 0x0801, bas('CARD.TEST'))],
        startup=STARTUP,
        sys_first=[('CLOCK.SYSTEM', 0xFF, 0x2000, rd('CLOCK.SYSTEM'))])
    out = os.path.join(HERE, 'dist', 'LASERCLOCK2.po')
    open(out, 'wb').write(img)
    print('wrote', out, '(bootable)')
    return img

if __name__ == '__main__':
    build()
