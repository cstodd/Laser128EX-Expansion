#!/usr/bin/env python3
"""Electrical sanity checks on the exported KiCad netlist (stands in for ERC, which the
KiCad 7 CLI lacks).  Usage: check_netlist.py <netlist.net>

Checks:
  * no single-pin nets except the explicitly allowed no-connects
  * at most one driver (output/power_out) per net; tri-state outputs only on known buses
  * every power_in pin sits on a supply net
  * J1 matches the Tech Ref Manual J13 table (entered independently below)
  * every SRAM address/data/control line reaches both SRAMs and has exactly one source
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from sexp import parse, find, find1  # noqa: E402

ALLOWED_NC = {('J2', '6'), ('J2', '7'), ('J2', '8'), ('U8', '1'), ('U8', '3'), ('U8', '4')} | \
             {('U7', p) for p in ('5', '6', '7', '8', '10', '11', '14', '16')}
SUPPLIES = {'+5V', 'GND', 'VBB', 'VBAT'}
TRISTATE_BUSES = {'XD%d' % i for i in range(8)} | {'D%d' % i for i in range(8)} | \
                 {'MA%d' % i for i in range(19)}

# Independent re-entry of LASER 128EX J13 (Tech Ref Manual D-102), pin: net
J13 = """1 +5V 2 +5V 3 RWR_n 4 ECAS4_n 5 ECAS2_n 6 ERA0 7 ERA2 8 ERA4 9 ERA6 10 ERA8
11 D1 12 D3 13 D5 14 D7 15 MEMRD 16 E1MOE_n 17 D6 18 D4 19 D2 20 D0 21 ERA7 22 ERA5
23 ERA3 24 ERA1 25 ECAS1_n 26 ECAS3_n 27 RASB_n 28 GND 29 GND 30 GND""".split()
J13 = dict(zip(J13[0::2], J13[1::2]))


def main(path):
    t = parse(open(path).read())
    nets = {}
    pinnet = {}
    for n in find(find1(t, 'nets'), 'net'):
        name = find1(n, 'name')[1].lstrip('/')
        nodes = []
        for x in find(n, 'node'):
            ref, pin = find1(x, 'ref')[1], find1(x, 'pin')[1]
            ptype = find1(x, 'pintype')[1] if find1(x, 'pintype') else 'unspecified'
            nodes.append((ref, pin, ptype))
            pinnet[(ref, pin)] = name
        nets[name] = nodes
    err = []

    for name, nodes in nets.items():
        if len(nodes) < 2 and (nodes[0][0], nodes[0][1]) not in ALLOWED_NC:
            err.append('single-pin net %s %s' % (name, nodes))
        drivers = [x for x in nodes if x[2].split('+')[0] in ('output', 'power_out')]
        if len(drivers) > 1:
            err.append('multiple drivers on %s: %s' % (name, drivers))
        tri = [x for x in nodes if x[2].startswith('tri_state')]
        if tri and name not in TRISTATE_BUSES:
            err.append('tri-state pin on non-bus net %s: %s' % (name, tri))
        for x in nodes:
            if x[2].startswith('power_in') and name not in SUPPLIES:
                err.append('power_in pin %s.%s on non-supply net %s' % (x[0], x[1], name))

    for pin, want in J13.items():
        got = pinnet.get(('J1', pin))
        if got != want:
            err.append('J1 pin %s is %s, manual says %s' % (pin, got, want))

    for i in range(19):
        n = 'MA%d' % i
        refs = sorted({r for r, p, _ in nets.get(n, [])})
        if not {'U5', 'U6', 'U9', 'U10'} <= set(refs):
            err.append('%s does not reach both SRAMs: %s' % (n, refs))
        src = [x for x in nets.get(n, []) if x[0] in ('U1', 'U2', 'U3')]
        if len(src) != 1:
            err.append('%s should have exactly one source (U1/U2/U3), has %s' % (n, src))
    for i in range(8):
        refs = {r for r, p, _ in nets.get('XD%d' % i, [])}
        if refs != {'U1', 'U4', 'U5', 'U6', 'U9', 'U10'}:
            err.append('XD%d connects %s' % (i, sorted(refs)))
        refs = {r for r, p, _ in nets.get('D%d' % i, [])}
        if refs != {'J1', 'U4'}:
            err.append('D%d connects %s' % (i, sorted(refs)))
    # SRAM supply must be battery-backed; chip enable must come through the DS1210
    for ref in ('U5', 'U6', 'U9', 'U10'):
        if pinnet.get((ref, '32')) != 'VBB':
            err.append('%s VCC not on VBB' % ref)
        if pinnet.get((ref, '22')) != 'RAM_CEO_n':
            err.append('%s CE# not from supervisor CE OUT' % ref)
    for a, b in (('U5', 'U9'), ('U6', 'U10')):    # SMD alternates wired pin-for-pin with the DIP
        for pin in map(str, range(1, 33)):
            if pinnet.get((a, pin)) != pinnet.get((b, pin)):
                err.append('%s/%s pin %s differ' % (a, b, pin))
    if pinnet.get(('U7', '12')) != 'RAM_CEO_n' or pinnet.get(('U7', '13')) != 'RAM_CE_n' or \
            pinnet.get(('U7', '2')) != 'VBB' or pinnet.get(('U7', '1')) != 'VBAT':
        err.append('U7 (MAX693A) CE/VOUT/VBATT wiring wrong')
    if pinnet.get(('U1', '40')) != 'PWR_RST_n' or pinnet.get(('U7', '15')) != 'PWR_RST_n':
        err.append('power-on reset not wired U7.15 -> U1.40')

    print('%d nets, %d pins checked' % (len(nets), len(pinnet)))
    if err:
        print('\n'.join('ERROR: ' + e for e in err))
        return 1
    print('OK: no errors')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
