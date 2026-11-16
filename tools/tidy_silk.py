#!/usr/bin/python3
"""Silkscreen tidy-up for the routed board: references centred on their part bodies (small parts
at 0.8 mm), mounting-hole labels hidden, values kept off silkscreen. Then DRC again.

    /usr/bin/python3 tools/tidy_silk.py
"""
import os

import pcbnew

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PCB = os.path.join(ROOT, 'hardware', 'rev01', 'laser128-ramcard.kicad_pcb')


def main():
    b = pcbnew.LoadBoard(PCB)
    for fp in b.GetFootprints():
        ref = fp.Reference()
        name = fp.GetReference()
        if name.startswith('H'):
            ref.SetVisible(False)
            continue
        body = fp.GetBoundingBox(False, False)
        ref.SetPosition(body.GetCenter())
        ref.SetTextAngleDegrees(0)
        small = name[0] in 'CR' or name in ('J3',)
        s = pcbnew.FromMM(0.8 if small else 1.0)
        ref.SetTextSize(pcbnew.VECTOR2I(s, s))
        ref.SetTextThickness(pcbnew.FromMM(0.12 if small else 0.15))
        if name[0] == 'C' and fp.GetOrientationDegrees() in (90.0, -90.0, 270.0):
            ref.SetTextAngleDegrees(90)
        fp.Value().SetLayer(pcbnew.F_Fab)
        # connectors and the radial cap: label beside the part, not on the pads
        beside = {'J1': ('left', 90), 'J2': ('below', 0), 'J3': ('left', 90), 'C13': ('below', 0)}
        if name in beside:
            side, ang = beside[name]
            c = body.GetCenter()
            if side == 'left':
                pos = pcbnew.VECTOR2I(body.GetLeft() - pcbnew.FromMM(1.0), c.y)
            else:
                pos = pcbnew.VECTOR2I(c.x, body.GetBottom() + pcbnew.FromMM(1.0))
            ref.SetPosition(pos)
            ref.SetTextAngleDegrees(ang)
    for d in b.GetDrawings():
        if d.GetClass() == 'PCB_TEXT' and d.GetText().startswith('Laser 128/128EX'):
            d.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.0), pcbnew.FromMM(1.0)))
            d.SetTextThickness(pcbnew.FromMM(0.15))
    # board text: the long SRAM note is shortened so it fits the free area
    for d in b.GetDrawings():
        if d.GetClass() == 'PCB_TEXT' and d.GetText().startswith('U5/U6'):
            d.SetText('U5/U6: AS6C4008-55 or 45ns SRAM on TSOP-DIP adapter')
            d.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.8), pcbnew.FromMM(0.8)))
            d.SetTextThickness(pcbnew.FromMM(0.12))
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(PCB)
    pcbnew.WriteDRCReport(b, PCB.replace('.kicad_pcb', '.drc.rpt'), pcbnew.EDA_UNITS_MILLIMETRES, True)


if __name__ == '__main__':
    main()
