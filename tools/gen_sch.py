#!/usr/bin/env python3
"""Generate hardware/laser128-ramcard.kicad_sch (KiCad 7 format) from an explicit
pin->net table.  Every pin of every part is either connected by a net label placed on its
endpoint or marked no-connect; the script refuses to emit a schematic otherwise.

Architecture (option B, see docs/design-notes.md):
  J1  Laser J13 mate          U1  ATF1504AS-10JU44 (PLCC-44, socket)
  U2  74AHCT574 row register  U3  74AHCT574 column register
  U4  74HCT245 data buffer    U5/U6 AS6C4008-55PCN 512Kx8 SRAM (DIP-32)
  U7  DS1210 NV controller    U8  DS3231SN RTC     BT1 CR2032
"""
import os
import sys
import uuid as _uuid

sys.path.insert(0, os.path.dirname(__file__))
from sexp import S, Sym, dumps, parse, find, find1, walk  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
HW = os.path.join(ROOT, 'hardware')
STOCK = '/usr/share/kicad/symbols'
PROJECT = 'laser128-ramcard'
ROOT_UUID = '6c1d0a4e-1a28-4e5b-9f3e-128e0000c0d3'

_n = [0]


def U():
    """Deterministic UUIDs so regenerating gives stable diffs."""
    _n[0] += 1
    return str(_uuid.uuid5(_uuid.NAMESPACE_URL, 'laser128-ramcard/%d' % _n[0]))


# ------------------------------------------------------------------ symbol loading
_cache = {}


def _lib(path):
    if path not in _cache:
        _cache[path] = parse(open(path).read())
    return _cache[path]


def load_symbol(lib_id):
    lib, name = lib_id.split(':')
    path = (os.path.join(HW, 'lib', 'Laser128.kicad_sym') if lib == 'Laser128'
            else os.path.join(STOCK, lib + '.kicad_sym'))
    t = _lib(path)
    sym = [s for s in find(t, 'symbol') if s[1] == name][0]
    ext = find1(sym, 'extends')
    if ext:
        parent = [s for s in find(t, 'symbol') if s[1] == ext[1]][0]
        body = [c for c in parent[2:] if not (isinstance(c, list) and c[0] == 'property')]
        props = [c for c in sym[2:] if isinstance(c, list) and c[0] == 'property']
        # keep parent props that the child does not override
        have = {p[1] for p in props}
        props += [c for c in parent[2:] if isinstance(c, list) and c[0] == 'property' and c[1] not in have]
        rest = [c for c in sym[2:] if not (isinstance(c, list) and c[0] in ('property', 'extends'))]
        sym = [Sym('symbol'), name] + rest + props + body
        pname = ext[1]
    else:
        pname = name
    out = [Sym('symbol'), lib_id]
    for c in sym[2:]:
        if isinstance(c, list) and c[0] == 'symbol':
            c = [c[0], c[1].replace(pname, name, 1)] + c[2:]
        out.append(c)
    return out


def sym_pins(symdef):
    pins = {}
    for p in walk(symdef, 'pin'):
        num = find1(p, 'number')[1]
        at = find1(p, 'at')
        hidden = 'hide' in [x for x in p if isinstance(x, Sym)]
        pins.setdefault(num, []).append((float(at[1]), float(at[2]), int(float(at[3])), hidden))
    return pins


# ------------------------------------------------------------------ design table
def bus(prefix, pins, start=0):
    return {p: '%s%d' % (prefix, i + start) for i, p in enumerate(pins)}


PARTS = []


def part(ref, lib_id, value, fp, nets, at, nc=(), datasheet='~'):
    PARTS.append(dict(ref=ref, lib_id=lib_id, value=value, fp=fp, nets={str(k): v for k, v in nets.items()},
                      nc={str(x) for x in nc}, at=at, ds=datasheet))


FP_DIP20 = 'Package_DIP:DIP-20_W7.62mm_Socket'
FP_C = 'Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm'
FP_CP = 'Capacitor_THT:CP_Radial_D5.0mm_P2.00mm'
FP_R = 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal'

# J1: Laser J13 mate (pin map from Tech Ref Manual D-102)
J1 = {1: '+5V', 2: '+5V', 3: 'RWR_n', 4: 'ECAS4_n', 5: 'ECAS2_n', 6: 'ERA0', 7: 'ERA2', 8: 'ERA4',
      9: 'ERA6', 10: 'ERA8', 11: 'D1', 12: 'D3', 13: 'D5', 14: 'D7', 15: 'MEMRD', 16: 'E1MOE_n',
      17: 'D6', 18: 'D4', 19: 'D2', 20: 'D0', 21: 'ERA7', 22: 'ERA5', 23: 'ERA3', 24: 'ERA1',
      25: 'ECAS1_n', 26: 'ECAS3_n', 27: 'RASB_n', 28: 'GND', 29: 'GND', 30: 'GND'}
part('J1', 'Laser128:Laser128_J1', 'Laser128_J1',
     'Laser128:Laser128_J1_Socket_2x15_P2.54mm_Unumbered', J1, (45.72, 101.6))

# U1: CPLD pin assignment (PLCC-44).  Mirrored in cpld/laser128_ramcard.pin
CPLD = {
    # bus inputs
    1: 'ECAS1_n', 44: 'ECAS2_n', 4: 'ECAS3_n', 5: 'ECAS4_n', 2: 'RASB_n', 43: 'E1MOE_n',
    6: 'RWR_n', 8: 'ERA8', 39: 'MEMRD',
    # card-side data bus
    9: 'XD0', 11: 'XD1', 12: 'XD2', 14: 'XD3', 16: 'XD4', 17: 'XD5', 18: 'XD6', 19: 'XD7',
    # outputs
    20: 'ROWCLK', 21: 'COLCLK', 33: 'MA8', 37: 'MA17', 24: 'MA18',
    25: 'RAM_CE_n', 26: 'OE0_n', 27: 'OE1_n', 28: 'WE0_n', 29: 'WE1_n', 31: 'BUF_OE_n',
    34: 'SDA', 36: 'SCL', 40: 'DBG0', 41: 'DBG1',
    # JTAG
    7: 'TDI', 13: 'TMS', 32: 'TCK', 38: 'TDO',
    # power
    3: '+5V', 15: '+5V', 23: '+5V', 35: '+5V', 10: 'GND', 22: 'GND', 30: 'GND', 42: 'GND',
}
part('U1', 'Laser128:ATF1504AS-xJx44', 'ATF1504AS-10JU44', 'Package_LCC:PLCC-44_THT-Socket',
     CPLD, (139.7, 101.6), datasheet='https://www.microchip.com/en-us/product/atf1504as')

# U2: row register  ERA0-7 -> MA9-16, clocked on /RASB fall (ROWCLK from CPLD)
row = {1: 'GND', 10: 'GND', 20: '+5V', 11: 'ROWCLK'}
row.update(bus('ERA', [2, 3, 4, 5, 6, 7, 8, 9]))
row.update(bus('MA', [19, 18, 17, 16, 15, 14, 13, 12], 9))
part('U2', '74xx:74HCT574', '74AHCT574', FP_DIP20, row, (226.06, 63.5))

# U3: column register  ERA0-7 -> MA0-7, clocked on first /ECASn fall (COLCLK)
col = {1: 'GND', 10: 'GND', 20: '+5V', 11: 'COLCLK'}
col.update(bus('ERA', [2, 3, 4, 5, 6, 7, 8, 9]))
col.update(bus('MA', [19, 18, 17, 16, 15, 14, 13, 12], 0))
part('U3', '74xx:74HCT574', '74AHCT574', FP_DIP20, col, (226.06, 129.54))

# U4: data buffer. A = card side (XD), B = Laser side (D). DIR = MEMRD (high: card -> Laser)
buf = {1: 'MEMRD', 19: 'BUF_OE_n', 10: 'GND', 20: '+5V'}
buf.update(bus('XD', [2, 3, 4, 5, 6, 7, 8, 9]))
buf.update(bus('D', [18, 17, 16, 15, 14, 13, 12, 11]))
part('U4', '74xx:74HC245', '74HCT245', FP_DIP20, buf, (139.7, 205.74))


def sram(n):
    pins = {32: 'VBB', 16: 'GND', 22: 'RAM_CEO_n', 24: 'OE%d_n' % n, 29: 'WE%d_n' % n}
    addr = {12: 0, 11: 1, 10: 2, 9: 3, 8: 4, 7: 5, 6: 6, 5: 7, 27: 8, 26: 9, 23: 10, 25: 11,
            4: 12, 28: 13, 3: 14, 31: 15, 2: 16, 30: 17, 1: 18}
    for p, a in addr.items():
        pins[p] = 'MA%d' % a
    pins.update(bus('XD', [13, 14, 15, 17, 18, 19, 20, 21]))
    return pins


part('U5', 'Memory_RAM:AS6C4008-55PCN', 'AS6C4008-55PCN', 'Package_DIP:DIP-32_W15.24mm_Socket',
     sram(0), (317.5, 73.66))
part('U6', 'Memory_RAM:AS6C4008-55PCN', 'AS6C4008-55PCN', 'Package_DIP:DIP-32_W15.24mm_Socket',
     sram(1), (317.5, 162.56))

# U7: DS1210. TOL->VCCO (4.37V trip), unused VBAT2 grounded (datasheet note 3)
part('U7', 'Power_Management:DS1210', 'DS1210', 'Package_DIP:DIP-8_W7.62mm_Socket',
     {1: 'VBB', 2: 'VBAT', 3: 'VBB', 4: 'GND', 5: 'RAM_CE_n', 6: 'RAM_CEO_n', 7: 'GND', 8: '+5V'},
     (226.06, 205.74))

# U8: DS3231SN (stock DS3231M symbol has the same SOIC-16 pinout). N.C. pins 5-12 -> GND.
rtc = {2: '+5V', 13: 'GND', 14: 'VBAT', 15: 'SDA', 16: 'SCL'}
rtc.update({p: 'GND' for p in range(5, 13)})
part('U8', 'Timer_RTC:DS3231M', 'DS3231SN', 'Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm',
     rtc, (317.5, 236.22), nc=(1, 3, 4))

part('BT1', 'Device:Battery_Cell', 'CR2032', 'Battery:BatteryHolder_Keystone_103_1x20mm',
     {1: 'VBAT', 2: 'GND'}, (381.0, 233.68))

# J2: JTAG, Altera/Atmel 10-pin (ATDH1150USB / ByteBlaster layout)
part('J2', 'Connector_Generic:Conn_02x05_Odd_Even', 'JTAG', 'Connector_IDC:IDC-Header_2x05_P2.54mm_Vertical',
     {1: 'TCK', 2: 'GND', 3: 'TDO', 4: '+5V', 5: 'TMS', 9: 'TDI', 10: 'GND'}, (45.72, 190.5), nc=(6, 7, 8))
part('J3', 'Connector_Generic:Conn_01x04', 'DEBUG', 'Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical',
     {1: 'GND', 2: 'DBG0', 3: 'DBG1', 4: '+5V'}, (45.72, 228.6))

# pull resistors
for ref, val, a, b, x in (('R1', '4.7k', 'SDA', '+5V', 50.8), ('R2', '4.7k', 'SCL', '+5V', 63.5),
                          ('R3', '10k', 'TMS', '+5V', 76.2), ('R4', '10k', 'TDI', '+5V', 88.9),
                          ('R5', '1k', 'TCK', 'GND', 101.6)):
    part(ref, 'Device:R', val, FP_R, {1: b, 2: a}, (x, 262.89))

# decoupling: one 100nF per supply pin group, plus bulk
caps = [('C1', 'U1'), ('C2', 'U1'), ('C3', 'U1'), ('C4', 'U1'), ('C5', 'U2'), ('C6', 'U3'),
        ('C7', 'U4'), ('C8', 'U7'), ('C9', 'U8')]
x = 127.0
for ref, _ in caps:
    part(ref, 'Device:C', '100n', FP_C, {1: '+5V', 2: 'GND'}, (x, 262.89))
    x += 10.16
for ref in ('C10', 'C11'):   # SRAM decoupling on the battery-backed rail
    part(ref, 'Device:C', '100n', FP_C, {1: 'VBB', 2: 'GND'}, (x, 262.89))
    x += 10.16
part('C12', 'Device:C', '1u', FP_C, {1: 'VBB', 2: 'GND'}, (x, 262.89))      # ceramic: no leakage on VBB
x += 10.16
part('C13', 'Device:C_Polarized', '22u', FP_CP, {1: '+5V', 2: 'GND'}, (x, 262.89))

# power flags (J1 pins are passive; battery is passive)
FLAGS = [('+5V', (40.64, 279.4)), ('GND', (55.88, 279.4)), ('VBAT', (71.12, 279.4))]


# ------------------------------------------------------------------ emitter
def eff(justify=None, hide=False, size=1.27):
    e = S('effects', S('font', S('size', size, size)))
    if justify:
        e.append(S('justify', *[Sym(j) for j in justify.split()]))
    if hide:
        e.append(Sym('hide'))
    return e


def label(net, x, y, pin_rot):
    # pin_rot is the pin direction in symbol coordinates (0: line goes right, endpoint on left)
    ang = {0: 180, 180: 0, 90: 270, 270: 90}[pin_rot]
    just = 'right bottom' if ang in (180, 270) else 'left bottom'
    return S('label', net, S('at', round(x, 2), round(y, 2), ang), S('fields_autoplaced'),
             eff(just), S('uuid', U()))


def instance(lib_id, ref, value, fp, at, pins, ds='~', extra_props=()):
    X, Y = at
    ys = [Y - p[1] for v in pins.values() for p in v] or [Y]
    xs = [X + p[0] for v in pins.values() for p in v] or [X]
    rots = [p[2] for v in pins.values() for p in v]
    top = min(ys) - (10.16 if 270 in rots else 3.81)   # vertical labels above the part
    bot = max(ys) + (10.16 if 90 in rots else 3.81)
    cx = (min(xs) + max(xs)) / 2
    e = S('symbol', S('lib_id', lib_id), S('at', X, Y, 0), S('unit', 1),
          S('in_bom', Sym('no' if ref.startswith('#') else 'yes')), S('on_board', Sym('no' if ref.startswith('#') else 'yes')),
          S('dnp', Sym('no')), S('uuid', U()),
          S('property', 'Reference', ref, S('at', round(cx, 2), round(top, 2), 0), eff(hide=ref.startswith('#'))),
          S('property', 'Value', value, S('at', round(cx, 2), round(bot, 2), 0), eff()),
          S('property', 'Footprint', fp, S('at', X, Y, 0), eff(hide=True)),
          S('property', 'Datasheet', ds, S('at', X, Y, 0), eff(hide=True)))
    for k, v in extra_props:
        e.append(S('property', k, v, S('at', X, Y, 0), eff(hide=True)))
    for num in pins:
        e.append(S('pin', num, S('uuid', U())))
    e.append(S('instances', S('project', PROJECT, S('path', '/' + ROOT_UUID, S('reference', ref), S('unit', 1)))))
    return e


def build():
    libs = {}
    items = []
    placed = set()
    errors = []
    for p in PARTS:
        if p['lib_id'] not in libs:
            libs[p['lib_id']] = load_symbol(p['lib_id'])
        pins = sym_pins(libs[p['lib_id']])
        X, Y = p['at']
        for num, locs in pins.items():
            if num in p['nc']:
                px, py, rot, hid = locs[0]
                items.append(S('no_connect', S('at', round(X + px, 2), round(Y - py, 2)), S('uuid', U())))
                continue
            if num not in p['nets']:
                errors.append('%s pin %s unassigned' % (p['ref'], num))
                continue
            for px, py, rot, hid in locs:
                key = (round(X + px, 2), round(Y - py, 2))
                if key in placed:
                    continue
                placed.add(key)
                items.append(label(p['nets'][num], X + px, Y - py, rot))
        for num in p['nets']:
            if num not in pins:
                errors.append('%s has no pin %s' % (p['ref'], num))
        items.append(instance(p['lib_id'], p['ref'], p['value'], p['fp'], p['at'], pins, p['ds']))
    # power flags
    libs['power:PWR_FLAG'] = load_symbol('power:PWR_FLAG')
    for i, (net, (x, y)) in enumerate(FLAGS):
        items.append(label(net, x, y, 90))
        items.append(instance('power:PWR_FLAG', '#FLG0%d' % (i + 1), 'PWR_FLAG', '', (x, y),
                              sym_pins(libs['power:PWR_FLAG'])))
    if errors:
        raise SystemExit('\n'.join(errors))

    notes = [
        'Laser 128 / 128EX battery-backed 1MB SRAM expansion + RTC  (architecture B, see docs/design-notes.md)',
        'Row register U2 latches ERA0-7 on /RASB fall; column register U3 on first /ECASn fall. CPLD holds ERA8 (MA8/MA17) and bank bits.',
        'U5 = bank 0 (512K), U6 = bank 1. Both CE# from DS1210 CEO (battery write-protect); CPLD selects chip with OEn/WEn.',
        'RTC: DS3231 I2C bit-banged through the CPLD, reachable via $C0D3 only after the 8-byte unlock key.',
        'U2/U3: use 74AHCT574 (fast). Do not substitute 74LS. U5/U6: AS6C4008 (2.7-5.5V) - NOT 3.3V-only parts.',
    ]
    for i, n in enumerate(notes):
        items.append(S('text', n, S('at', 25.4, 15.24 + i * 3.81, 0), eff('left bottom'), S('uuid', U())))

    sch = S('kicad_sch', S('version', 20230121), S('generator', 'eeschema'), S('uuid', ROOT_UUID),
            S('paper', 'A3'),
            S('title_block', S('title', 'Laser 128/128EX Battery-Backed RAM + Clock Card'),
              S('date', '2026-11-15'), S('rev', '0.1'),
              S('comment', 1, 'Generated by tools/gen_sch.py - edit the script, not this file'),
              S('comment', 2, 'Interface: LASER 128 Tech Ref Manual sec. 11.10, D-102/D-103')),
            S('lib_symbols', *libs.values()), *items,
            S('sheet_instances', S('path', '/', S('page', '1'))))
    return sch


if __name__ == '__main__':
    out = os.path.join(HW, PROJECT + '.kicad_sch')
    with open(out, 'w') as f:
        f.write(dumps(build()) + '\n')
    print('wrote', out, len(PARTS), 'parts')
