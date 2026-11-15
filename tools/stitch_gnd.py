#!/usr/bin/python3
"""Add GND stitching vias between the F.Cu and B.Cu ground pours of the routed board, keep only
those that land in filled GND copper on both layers, refill, and rerun DRC.

    /usr/bin/python3 tools/stitch_gnd.py [pitch_mm]
"""
import math
import os
import sys

import pcbnew

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PCB = os.path.join(ROOT, 'hardware', 'laser128-ramcard.kicad_pcb')
VIA_D, VIA_DRILL, CLEAR = 0.6, 0.3, 0.3          # mm
EDGE = 1.5


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def main(pitch=3.0):
    b = pcbnew.LoadBoard(PCB)
    mm = pcbnew.ToMM
    gnd = b.FindNet('GND')
    bb = b.GetBoardEdgesBoundingBox()
    x0, y0, x1, y1 = mm(bb.GetLeft()) + EDGE, mm(bb.GetTop()) + EDGE, mm(bb.GetRight()) - EDGE, mm(bb.GetBottom()) - EDGE

    tracks = list(b.GetTracks())                  # read once, before adding anything
    segs = [(mm(t.GetStart().x), mm(t.GetStart().y), mm(t.GetEnd().x), mm(t.GetEnd().y), mm(t.GetWidth()) / 2)
            for t in tracks if t.GetClass() == 'PCB_TRACK']
    vias = [(mm(t.GetPosition().x), mm(t.GetPosition().y), mm(t.GetWidth()) / 2)
            for t in tracks if t.GetClass() == 'PCB_VIA']
    pads = []
    for fp in b.GetFootprints():
        for p in fp.Pads():
            r = p.GetBoundingBox()
            pads.append((mm(r.GetLeft()), mm(r.GetTop()), mm(r.GetRight()), mm(r.GetBottom())))

    rv = VIA_D / 2
    added = []
    y = y0
    while y <= y1:
        x = x0
        while x <= x1:
            ok = all(seg_dist(x, y, ax, ay, bx2, by2) >= rv + w + CLEAR for ax, ay, bx2, by2, w in segs) and \
                 all(math.hypot(x - vx, y - vy) >= rv + vr + CLEAR for vx, vy, vr in vias) and \
                 all(not (l - rv - CLEAR < x < r + rv + CLEAR and t - rv - CLEAR < y < bt + rv + CLEAR)
                     for l, t, r, bt in pads)
            if ok:
                v = pcbnew.PCB_VIA(b)
                v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
                v.SetWidth(pcbnew.FromMM(VIA_D))
                v.SetDrill(pcbnew.FromMM(VIA_DRILL))
                v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                v.SetNet(gnd)
                b.Add(v)
                added.append(v)
                vias.append((x, y, rv))
            x += pitch
        y += pitch

    filler = pcbnew.ZONE_FILLER(b)
    filler.Fill(b.Zones())
    zones = {z.GetLayer(): z for z in b.Zones() if z.GetNetname() == 'GND'}
    kept = 0
    for v in added:
        pos = v.GetPosition()
        if all(zones[l].HitTestFilledArea(l, pos) for l in (pcbnew.F_Cu, pcbnew.B_Cu) if l in zones):
            kept += 1
        else:
            b.Remove(v)
    filler.Fill(b.Zones())
    b.Save(PCB)
    rpt = PCB.replace('.kicad_pcb', '.drc.rpt')
    pcbnew.WriteDRCReport(b, rpt, pcbnew.EDA_UNITS_MILLIMETRES, True)
    print('stitching vias: %d candidates, %d kept' % (len(added), kept))


if __name__ == '__main__':
    main(*(float(a) for a in sys.argv[1:2]))
