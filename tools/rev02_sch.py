#!/usr/bin/env python3
"""Rev 0.2 schematic edit (hardware/rev02): DS3231M (I2C) -> DS3234SN# (SPI). Text-level edits of the
KiCad schematic (KiCad has no schematic Python API). Run once on the copy of rev 0.1; checked by ERC + netlist.
  U8: Timer_RTC:DS3231M -> Laser128:DS3234, SOIC-20W; labels/no-connects re-placed at the new pin positions.
  R1: 4.7k pull-up -> 1k series, RTC_DIO (CPLD pin 39) to RTC_SDIO (DS3234 DIN+DOUT).
  R2: 4.7k pull-up -> 47k pull-down, RTC_SDIO to GND.
  U1 (CPLD): pin 34 SDA -> RTC_CS_n, pin 36 SCL -> RTC_SCLK, pin 39 MEMRD -> RTC_DIO (MEMRD stays on J1 + U4).
"""
import os, re, sys, uuid
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HW = os.path.join(ROOT, 'hardware', 'rev02')
SCH = os.path.join(HW, 'laser128-ramcard.kicad_sch')
LIB = os.path.join(HW, 'lib', 'Laser128.kicad_sym')
U8X, U8Y = 317.5, 236.22

def u(): return str(uuid.uuid4())
def pin(kind, x, y, ang, name, num, hide=False):
    return ('        (pin %s line\n          (at %s %s %d)\n          (length 2.54)%s\n'
            '          (name "%s"\n            (effects\n              (font\n                (size 1.27 1.27))))\n'
            '          (number "%s"\n            (effects\n              (font\n                (size 1.27 1.27)))))\n'
            % (kind, x, y, ang, ' hide' if hide else '', name, num))

# DS3234 symbol (KiCad Y up). Pin ends: left x=-10.16, right x=10.16, top y=12.7, bottom y=-15.24.
PINS = [('input', -10.16, 5.08, 0, '~{CS}', '1', False), ('input', -10.16, 2.54, 0, 'SCLK', '18', False),
        ('input', -10.16, 2.54, 0, 'SCLK', '20', True), ('input', -10.16, -2.54, 0, 'DIN', '17', False),
        ('tri_state', -10.16, -5.08, 0, 'DOUT', '19', False),
        ('power_in', -2.54, 12.7, 270, 'VCC', '4', False), ('power_in', 2.54, 12.7, 270, 'VBAT', '16', False),
        ('output', 10.16, 5.08, 180, '32kHz', '3', False), ('open_collector', 10.16, 0, 180, '~{INT}/SQW', '5', False),
        ('bidirectional', 10.16, -5.08, 180, '~{RST}', '6', False), ('power_in', 0, -15.24, 90, 'GND', '15', False)]
PINS += [('passive', 0, -15.24, 90, 'GND', n, True) for n in ('2', '7', '8', '9', '10', '11', '12', '13', '14')]

def symbol(name, in_sch):
    s = '    (symbol "%s"\n      (in_bom yes)\n      (on_board yes)\n' % name
    for k, v, at, hide in [('Reference', 'U', '-7.62 11.43 0', False), ('Value', 'DS3234', '1.27 -13.97 0', False),
                           ('Footprint', 'Package_SO:SOIC-20W_7.5x12.8mm_P1.27mm', '0 -19.05 0', True),
                           ('Datasheet', 'https://www.analog.com/media/en/technical-documentation/data-sheets/DS3234.pdf', '0 -21.59 0', True),
                           ('ki_description', 'Extremely accurate SPI RTC/TCXO/crystal + 256 B SRAM, SO-20W. N.C. pins 2, 7-14 must be grounded (stacked on GND here)', '0 0 0', True),
                           ('ki_fp_filters', 'SOIC*7.5x12.8mm*P1.27mm*', '0 0 0', True)]:
        s += ('      (property "%s" "%s"\n        (at %s)\n        (effects\n          (font\n            (size 1.27 1.27))%s))\n'
              % (k, v, at, ' hide' if hide else ''))
    base = name.split(':')[-1]
    s += ('      (symbol "%s_0_1"\n        (rectangle\n          (start -7.62 10.16)\n          (end 7.62 -12.7)\n'
          '          (stroke\n            (width 0.254)\n            (type default))\n          (fill\n            (type background))))\n' % base)
    s += '      (symbol "%s_1_1"\n' % base + ''.join(pin(*p) for p in PINS) + '      ))\n'
    return s

def abs_pin(num):
    p = [p for p in PINS if p[5] == num][0]
    return round(U8X + p[1], 2), round(U8Y - p[2], 2)

def main():
    t = open(SCH).read()
    # --- library symbol: replace the embedded DS3231M with DS3234
    i = t.index('    (symbol "Timer_RTC:DS3231M"'); j = i
    depth = 0
    while True:
        c = t[j]; depth += c == '('; depth -= c == ')'; j += 1
        if depth == 0: break
    t = t[:i] + symbol('Laser128:DS3234', True).rstrip('\n') + t[j:]
    # --- labels: rename by (old name, x, y)
    def relabel(old, new, x, y):
        nonlocal t
        pat = re.compile(r'\(label "%s"\s*\(at %s %s ' % (re.escape(old), re.escape(fmt(x)), re.escape(fmt(y))))
        m = pat.search(t); assert m, (old, x, y)
        t = t[:m.start()] + '(label "%s"' % new + t[m.start() + len('(label "%s"' % old):]
    def fmt(v): return ('%g' % v)
    def block_at(kind, name, x, y):
        pat = re.compile(r'\n\s*\(%s\s+%s\s*\(at %s %s[ )]' % (kind, ('"%s"' % re.escape(name)) if name else '', re.escape(fmt(x)), re.escape(fmt(y))))
        m = pat.search(t); assert m, (kind, name, x, y)
        k = m.start() + 1
        while t[k] != '(': k += 1
        d = 0; e = k
        while True:
            c = t[e]; d += c == '('; d -= c == ')'; e += 1
            if d == 0: break
        return m.start(), e
    def delete(kind, name, x, y):
        nonlocal t
        s, e = block_at(kind, name, x, y); t = t[:s] + t[e:]
    def add_label(name, x, y, ang, template):
        nonlocal t
        b = re.sub(r'\(at [-\d.]+ [-\d.]+ \d+\)', '(at %s %s %d)' % (fmt(x), fmt(y), ang), template, 1)
        b = re.sub(r'\(label "[^"]*"', '(label "%s"' % name, b, 1)
        b = re.sub(r'\(uuid "[^"]*"\)', '(uuid "%s")' % u(), b)
        b = re.sub(r'\(justify (left|right)\)', '(justify %s)' % ('right' if ang == 180 else 'left'), b)
        t = t.replace('\n  (sheet_instances', b + '\n  (sheet_instances', 1) if '(sheet_instances' in t else t[:t.rindex(')')] + b + '\n)'
    def add_nc(x, y):
        nonlocal t
        b = '\n  (no_connect\n    (at %s %s)\n    (uuid "%s"))' % (fmt(x), fmt(y), u())
        t = t.replace('\n  (sheet_instances', b + '\n  (sheet_instances', 1) if '(sheet_instances' in t else t[:t.rindex(')')] + b + '\n)'
    s, e = block_at('label', 'SDA', 304.8, 233.68); template = t[s:e]
    # CPLD pins
    relabel('SDA', 'RTC_CS_n', 154.94, 114.3); relabel('SCL', 'RTC_SCLK', 154.94, 111.76); relabel('MEMRD', 'RTC_DIO', 154.94, 104.14)
    # R1, R2
    relabel('+5V', 'RTC_DIO', 50.8, 259.08); relabel('SDA', 'RTC_SDIO', 50.8, 266.7)
    relabel('+5V', 'RTC_SDIO', 63.5, 259.08); relabel('SCL', 'GND', 63.5, 266.7)
    # U8: old labels / no-connects out
    for n, x, y in [('+5V', 314.96, 226.06), ('VBAT', 317.5, 226.06), ('GND', 317.5, 246.38), ('SDA', 304.8, 233.68), ('SCL', 304.8, 231.14)]:
        delete('label', n, x, y)
    for x, y in [(330.2, 231.14), (330.2, 238.76), (304.8, 241.3)]:
        delete('no_connect', None, x, y)
    for name, num, ang in [('RTC_CS_n', '1', 180), ('RTC_SCLK', '18', 180), ('RTC_SDIO', '17', 180), ('RTC_SDIO', '19', 180),
                           ('+5V', '4', 0), ('VBAT', '16', 0), ('GND', '15', 0)]:
        add_label(name, *abs_pin(num), ang, template)
    for num in ('3', '5', '6'):
        add_nc(*abs_pin(num))
    # U8 instance
    i = t.index('(lib_id "Timer_RTC:DS3231M"'); s = t.rindex('\n  (symbol', 0, i)
    d = 0; e = t.index('(', s)
    while True:
        c = t[e]; d += c == '('; d -= c == ')'; e += 1
        if d == 0: break
    blk = t[s:e]
    blk = blk.replace('(lib_id "Timer_RTC:DS3231M"', '(lib_id "Laser128:DS3234"')
    blk = blk.replace('"DS3231M+"', '"DS3234SN#"').replace('Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm', 'Package_SO:SOIC-20W_7.5x12.8mm_P1.27mm')
    blk = re.sub(r'\(property "Datasheet" "[^"]*"', '(property "Datasheet" "https://www.analog.com/media/en/technical-documentation/data-sheets/DS3234.pdf"', blk)
    blk = re.sub(r'\n\s*\(pin "\d+"\s*\(uuid "[^"]*"\)\)', '', blk)
    pins = ''.join('\n    (pin "%d"\n      (uuid "%s"))' % (n, u()) for n in range(1, 21))
    k = blk.index('\n    (instances') if '\n    (instances' in blk else blk.rindex(')')
    blk = blk[:k] + pins + blk[k:]
    t = t[:s] + blk + t[e:]
    # R values
    for ref, val in (('R1', '1k'), ('R2', '47k')):
        i = t.index('(property "Reference" "%s"' % ref); s = t.rindex('\n  (symbol', 0, i)
        e = t.index('(property "Value" "4.7k"', s); assert e < i + 2000
        t = t[:e] + '(property "Value" "%s"' % val + t[e + len('(property "Value" "4.7k"'):]
    # R1/R2 use the vertical DIN0207 footprint so the DS3234 cluster fits beside the CPLD (rev02_pcb.py move)
    for ref in ('R1', 'R2'):
        i = t.index('(property "Reference" "%s"' % ref); s = t.rindex('\n  (symbol', 0, i)
        h = 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal'
        e = t.index(h, s); assert e < i + 2000
        t = t[:e] + 'Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical' + t[e + len(h):]
    open(SCH, 'w').write(t)
    # project library
    L = open(LIB).read()
    if '(symbol "DS3234"' not in L:
        L = L[:L.rindex(')')] + symbol('DS3234', False) + ')\n'
        open(LIB, 'w').write(L)
    print('rev02 schematic edited')

if __name__ == '__main__':
    main()
