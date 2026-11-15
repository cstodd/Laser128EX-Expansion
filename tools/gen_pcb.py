#!/usr/bin/python3
"""Create hardware/laser128-ramcard.kicad_pcb: outline, mounting hole, placed footprints with
nets from the schematic netlist, GND pours. Routing is NOT done here.

Run with the system python that has KiCad's pcbnew module:
    kicad-cli sch export netlist -o /tmp/l128.net hardware/laser128-ramcard.kicad_sch
    /usr/bin/python3 tools/gen_pcb.py /tmp/l128.net
Coordinates are board coordinates (mm, origin top-left, y down); see docs/mechanical.md.
"""
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(__file__))
from sexp import parse, find, find1  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'hardware', 'laser128-ramcard.kicad_pcb')
FPLIBS = {'Laser128': os.path.join(ROOT, 'hardware', 'lib', 'Laser128.pretty')}
STOCK_FP = '/usr/share/kicad/footprints'
OX, OY = 50.0, 50.0          # board origin on the KiCad page
W, H = 100.0, 90.0           # board size

# ref: (x, y, rotation_deg) of footprint origin (pad 1 for DIP/headers/J1)
PLACE = {
    'J1': (94.73, 27.44, 0),        # measured: pins 15/16 are 23.00 mm above H1, row centreline x = 96
    'U5': (4.0, 6.0, 0), 'U6': (25.0, 6.0, 0),            # SRAMs (DIP-32)
    'U1': (61.27, 15.65, 0),                               # CPLD socket, body centre ~ (60, 22)
    'U2': (50.0, 44.0, 0), 'U3': (64.0, 44.0, 0),          # row / column registers
    'U4': (80.0, 44.0, 0),                                 # '245, B side faces J1
    'U7': (35.0, 52.0, 0),                                 # MAX693A
    'U8': (40.0, 80.0, 0),                                 # DS3231 (SOIC origin = centre)
    'BT1': (5.0, 75.0, 0),
    'J2': (78.0, 7.0, 0), 'J3': (88.0, 6.0, 0),
    'R3': (74.0, 26.0, 0), 'R4': (74.0, 30.0, 0), 'R5': (74.0, 34.0, 0),
    'R1': (60.0, 79.0, 0), 'R2': (60.0, 83.0, 0),
    'C1': (48.5, 38.3, 0), 'C2': (56.5, 38.3, 0), 'C3': (64.5, 38.3, 0), 'C4': (52.0, 5.0, 0),
    'C5': (50.0, 71.5, 0), 'C6': (64.0, 71.5, 0), 'C7': (80.0, 71.5, 0),
    'C8': (35.0, 48.0, 0), 'C9': (48.0, 77.0, 0),
    'C10': (4.0, 48.0, 0), 'C12': (13.0, 48.0, 0), 'C11': (25.0, 48.0, 0),
    'C13': (88.0, 20.0, 0),
}
HOLE = (96.0, 86.0)


def mm(v):
    return pcbnew.FromMM(v)


def pt(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))


def load_fp(fpid):
    lib, name = fpid.split(':')
    path = FPLIBS.get(lib, os.path.join(STOCK_FP, lib + '.pretty'))
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise SystemExit('footprint not found: ' + fpid)
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def main(netfile):
    t = parse(open(netfile).read())
    comps = {}
    for c in find(find1(t, 'components'), 'comp'):
        comps[find1(c, 'ref')[1]] = dict(value=find1(c, 'value')[1], fp=find1(c, 'footprint')[1],
                                         tstamp=find1(c, 'tstamps')[1])
    pads = {}
    netnames = []
    for n in find(find1(t, 'nets'), 'net'):
        name = find1(n, 'name')[1].lstrip('/')
        netnames.append(name)
        for x in find(n, 'node'):
            pads[(find1(x, 'ref')[1], find1(x, 'pin')[1])] = name

    board = pcbnew.BOARD()
    board.SetCopperLayerCount(2)
    ds = board.GetDesignSettings()
    ds.m_TrackMinWidth = mm(0.2)
    ds.m_MinClearance = mm(0.2)
    ds.m_ViasMinSize = mm(0.6)
    ds.m_MinThroughDrill = mm(0.3)
    ds.m_HoleToHoleMin = mm(0.25)
    ds.m_CopperEdgeClearance = mm(0.5)

    nets = {}
    for name in netnames:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        nets[name] = ni

    # outline
    corners = [(0, 0), (W, 0), (W, H), (0, H)]
    for (x1, y1), (x2, y2) in zip(corners, corners[1:] + corners[:1]):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pt(x1, y1))
        s.SetEnd(pt(x2, y2))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(mm(0.1))
        board.Add(s)

    missing = [r for r in comps if r not in PLACE]
    if missing:
        raise SystemExit('no placement for: %s' % missing)
    for ref, c in sorted(comps.items()):
        fp = load_fp(c['fp'])
        fp.SetReference(ref)
        fp.SetValue(c['value'])
        fp.SetPath(pcbnew.KIID_PATH('/' + c['tstamp']))
        x, y, rot = PLACE[ref]
        fp.SetPosition(pt(x, y))
        fp.SetOrientationDegrees(rot)
        board.Add(fp)
        for pad in fp.Pads():
            key = (ref, pad.GetNumber())
            if key in pads:
                pad.SetNet(nets[pads[key]])

    # mounting hole, grounded (like the stock card's plated holes)
    h = load_fp('MountingHole:MountingHole_3.2mm_M3_Pad')
    h.SetReference('H1')
    h.SetValue('M3, Laser standoff')
    h.SetPosition(pt(*HOLE))
    board.Add(h)
    for pad in h.Pads():
        pad.SetNet(nets['GND'])

    # GND pours on both layers (filled after routing)
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNet(nets['GND'])
        z.SetLocalClearance(mm(0.3))
        z.SetMinThickness(mm(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        ol = z.Outline()
        ol.NewOutline()
        for x, y in ((0.3, 0.3), (W - 0.3, 0.3), (W - 0.3, H - 0.3), (0.3, H - 0.3)):
            ol.Append(mm(OX + x), mm(OY + y))
        board.Add(z)

    def text(s, x, y, layer, size=1.5):
        tx = pcbnew.PCB_TEXT(board)
        tx.SetText(s)
        tx.SetPosition(pt(x, y))
        tx.SetLayer(layer)
        tx.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
        tx.SetTextThickness(mm(size * 0.15))
        tx.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
        if layer == pcbnew.B_SilkS:
            tx.SetMirrored(True)
        board.Add(tx)
        return tx

    text('Laser 128/128EX 1MB RAM + Clock  rev 0.1', 48, 87.5, pcbnew.F_SilkS, 1.0)
    bt = text('github.com/cstodd/laser128ex-expansion', 60, 87.5, pcbnew.B_SilkS, 1.0)

    board.Save(OUT)
    rpt = OUT.replace('.kicad_pcb', '.drc.rpt')
    pcbnew.WriteDRCReport(board, rpt, pcbnew.EDA_UNITS_MILLIMETRES, True)
    print('wrote', OUT, len(comps), 'footprints +H1')


if __name__ == '__main__':
    main(sys.argv[1])
