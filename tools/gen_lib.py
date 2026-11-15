#!/usr/bin/env python3
"""Generate the project's custom KiCad library:
   hardware/lib/Laser128.kicad_sym  (J1 connector, ATF1504AS PLCC-44)
   hardware/lib/Laser128.pretty/    (J1 2x15 U-numbered socket footprint)
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(__file__))
from sexp import S, Sym, dumps, parse, find, find1, walk  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LIB = os.path.join(ROOT, 'hardware', 'lib')
STOCK = '/usr/share/kicad/symbols'

# ---------------------------------------------------------------- J1 (J13 mate)
# Pin -> (name, electrical type).  Source: Tech Ref Manual D-94 / D-102.
J1_PINS = {
    1: ('+5V', 'passive'), 2: ('+5V', 'passive'),
    3: ('~{RWR}', 'passive'), 4: ('~{ECAS4}', 'passive'), 5: ('~{ECAS2}', 'passive'),
    6: ('ERA0', 'passive'), 7: ('ERA2', 'passive'), 8: ('ERA4', 'passive'),
    9: ('ERA6', 'passive'), 10: ('ERA8', 'passive'),
    11: ('D1', 'passive'), 12: ('D3', 'passive'), 13: ('D5', 'passive'), 14: ('D7', 'passive'),
    15: ('MEMRD', 'passive'), 16: ('~{E1MOE}', 'passive'),
    17: ('D6', 'passive'), 18: ('D4', 'passive'), 19: ('D2', 'passive'), 20: ('D0', 'passive'),
    21: ('ERA7', 'passive'), 22: ('ERA5', 'passive'), 23: ('ERA3', 'passive'), 24: ('ERA1', 'passive'),
    25: ('~{ECAS1}', 'passive'), 26: ('~{ECAS3}', 'passive'), 27: ('~{RASB}', 'passive'),
    28: ('GND', 'passive'), 29: ('GND', 'passive'), 30: ('GND', 'passive'),
}


def font(size=1.27):
    return S('effects', S('font', S('size', size, size)))


_PID = {'Reference': 0, 'Value': 1, 'Footprint': 2, 'Datasheet': 3,
        'ki_keywords': 4, 'ki_description': 5, 'ki_fp_filters': 6}


def prop(name, value, x=0, y=0, hide=False, pid=None):
    eff = S('effects', S('font', S('size', 1.27, 1.27)))
    if hide:
        eff.append(Sym('hide'))
    return S('property', name, value, S('id', _PID.get(name, 7) if pid is None else pid),
             S('at', x, y, 0), eff)


def pin(num, name, etype, x, y, rot, length=2.54, hidden=False):
    p = S('pin', Sym(etype), Sym('line'), S('at', x, y, rot), S('length', length))
    if hidden:
        p.append(Sym('hide'))
    p += [S('name', name, font()), S('number', str(num), font())]
    return p


def rect(x1, y1, x2, y2):
    return S('rectangle', S('start', x1, y1), S('end', x2, y2),
             S('stroke', S('width', 0.254), S('type', Sym('default'))),
             S('fill', S('type', Sym('background'))))


def j1_symbol():
    """Two columns like the physical socket: 1..15 on the left, 30..16 on the right."""
    name = 'Laser128_J1'
    pins = []
    for i in range(15):
        y = 17.78 - i * 2.54
        a = 1 + i            # left column, pins 1..15 top to bottom
        b = 30 - i           # right column, pins 30..16 top to bottom
        pins.append(pin(a, J1_PINS[a][0], J1_PINS[a][1], -12.7, y, 0, 5.08))
        pins.append(pin(b, J1_PINS[b][0], J1_PINS[b][1], 12.7, y, 180, 5.08))
    body = S('symbol', name + '_0_1', rect(-7.62, 20.32, 7.62, -20.32))
    pinset = S('symbol', name + '_1_1', *pins)
    return S('symbol', name, S('pin_names', S('offset', 1.016)),
             S('in_bom', Sym('yes')), S('on_board', Sym('yes')),
             prop('Reference', 'J', 0, 22.86),
             prop('Value', name, 0, -22.86),
             prop('Footprint', 'Laser128:Laser128_J1_Socket_2x15_P2.54mm_Unumbered', 0, -25.4, True),
             prop('Datasheet', 'LASER 128 Technical Reference Manual, D-94/D-102 (J13)', 0, 0, True),
             prop('ki_description', 'Laser 128/128EX expansion-RAM connector J13 mate (2x15, U-numbered)', 0, 0, True),
             body, pinset)


# ---------------------------------------------------------------- ATF1504AS PLCC-44
def atf1504_plcc_symbol():
    """Derived from the stock ATF1502AS-xAx44 (TQFP-44) symbol.
    PLCC-44 pin = TQFP-44 pin + 6 (mod 44): the two packages share the same pin order,
    the PLCC numbering just starts on the middle of the top edge.  Spot checks (EPM7064/
    ATF1504 PLCC-44): TDI 7, TMS 13, TCK 32, TDO 38, GCLK1 43, OE1 44, GCLR 1, OE2/GCLK2 2,
    VCC 3/15/23/35, GND 10/22/30/42."""
    t = parse(open(os.path.join(STOCK, 'CPLD_Microchip.kicad_sym')).read())
    src = [s for s in find(t, 'symbol') if s[1] == 'ATF1502AS-xAx44'][0]
    name = 'ATF1504AS-xJx44'
    out = [Sym('symbol'), name]
    for c in src[2:]:
        if isinstance(c, list) and c[0] == 'property':
            k = c[1]
            if k == 'Value':
                at = find1(c, 'at')
                c = prop('Value', name, at[1], at[2])
            elif k == 'Footprint':
                c = prop('Footprint', 'Package_LCC:PLCC-44_THT-Socket', 0, 0, True)
            elif k == 'Datasheet':
                c = prop('Datasheet', 'https://www.microchip.com/en-us/product/atf1504as', 0, 0, True)
            elif k == 'ki_description':
                c = prop('ki_description', 'ATF1504AS 64-macrocell 5V CPLD, PLCC-44', 0, 0, True)
            elif k == 'ki_fp_filters':
                c = prop('ki_fp_filters', 'PLCC*44*', 0, 0, True)
            out.append(c)
        elif isinstance(c, list) and c[0] == 'symbol':
            sub = [Sym('symbol'), c[1].replace('ATF1502AS-xAx44', name)]
            for g in c[2:]:
                if isinstance(g, list) and g[0] == 'pin':
                    num = find1(g, 'number')
                    n = int(num[1])
                    num[1] = str((n + 6 - 1) % 44 + 1)
                    nm = find1(g, 'name')
                    nm[1] = nm[1].replace('/Vpp', '')
                sub.append(g)
            out.append(sub)
        else:
            out.append(c)
    return out


def write_symlib():
    lib = S('kicad_symbol_lib', S('version', 20220914), S('generator', 'laser128_gen_lib'),
            j1_symbol(), atf1504_plcc_symbol())
    os.makedirs(LIB, exist_ok=True)
    with open(os.path.join(LIB, 'Laser128.kicad_sym'), 'w') as f:
        f.write(dumps(lib) + '\n')


# ---------------------------------------------------------------- J1 footprint
def write_j1_footprint():
    """Pin 1 square at origin. Left column (x=0): pins 1..15 going down (+y).
    Right column (x=+2.54): pins 30..16 going down, so pin 30 is beside pin 1.
    On the card the RIGHT column sits toward the board edge, LEFT column toward the
    interior (matches the stock card D-106 and the photo of the original board)."""
    fp = S('footprint', 'Laser128_J1_Socket_2x15_P2.54mm_Unumbered',
           S('version', 20221018), S('generator', 'laser128_gen_lib'), S('layer', 'F.Cu'),
           S('descr', 'Laser 128/128EX J13 mate: 2x15 female socket, 2.54mm, U-numbered '
                      '(1-15 down one row, 30-16 down the other). NOT the stock odd/even 2x15.'),
           S('tags', 'Laser 128 expansion RAM connector'),
           S('attr', Sym('through_hole')))

    def txt(kind, value, x, y, layer, hide=False):
        e = S('fp_text', Sym(kind), value, S('at', x, y), S('layer', layer))
        if hide:
            e.append(Sym('hide'))
        e.append(S('effects', S('font', S('size', 1, 1), S('thickness', 0.15))))
        e.append(S('tstamp', str(uuid.uuid4())))
        return e

    fp.append(txt('reference', 'REF**', 1.27, -2.77, 'F.SilkS'))
    fp.append(txt('value', 'Laser128_J1', 1.27, 38.33, 'F.Fab'))
    fp.append(txt('user', '${REFERENCE}', 1.27, 17.78, 'F.Fab'))

    def line(x1, y1, x2, y2, layer, w):
        return S('fp_line', S('start', x1, y1), S('end', x2, y2),
                 S('stroke', S('width', w), S('type', Sym('solid'))), S('layer', layer),
                 S('tstamp', str(uuid.uuid4())))

    # silkscreen outline with pin-1 notch line (like the stock card)
    x0, x1, y0, y1 = -1.33, 3.87, -1.33, 36.89
    for a in ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)):
        fp.append(line(*a, 'F.SilkS', 0.12))
    fp.append(line(x0, 1.27, 1.27, 1.27, 'F.SilkS', 0.12))   # pin-1 marker bar
    fp.append(line(1.27, 1.27, 1.27, y0, 'F.SilkS', 0.12))
    # courtyard
    c0, c1, d0, d1 = -1.8, 4.35, -1.8, 37.35
    for a in ((c0, d0, c1, d0), (c1, d0, c1, d1), (c1, d1, c0, d1), (c0, d1, c0, d0)):
        fp.append(line(*a, 'F.CrtYd', 0.05))
    # fab
    for a in ((-1.27, -1.27, 3.81, -1.27), (3.81, -1.27, 3.81, 36.83),
              (3.81, 36.83, -1.27, 36.83), (-1.27, 36.83, -1.27, -1.27)):
        fp.append(line(*a, 'F.Fab', 0.1))

    for i in range(15):
        y = i * 2.54
        for num, x in ((1 + i, 0.0), (30 - i, 2.54)):
            shape = 'rect' if num == 1 else 'oval'
            fp.append(S('pad', str(num), Sym('thru_hole'), Sym(shape), S('at', x, y),
                        S('size', 1.7, 1.7), S('drill', 1.0), S('layers', '*.Cu', '*.Mask'),
                        S('tstamp', str(uuid.uuid4()))))
    d = os.path.join(LIB, 'Laser128.pretty')
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, 'Laser128_J1_Socket_2x15_P2.54mm_Unumbered.kicad_mod'), 'w') as f:
        f.write(dumps(fp) + '\n')


if __name__ == '__main__':
    write_symlib()
    write_j1_footprint()
    print('wrote', LIB)
