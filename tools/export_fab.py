#!/usr/bin/python3
"""Export fabrication outputs for hardware/laser128-ramcard.kicad_pcb into hardware/fab/:
Gerbers (JLCPCB/Protel naming), Excellon drill (PTH+NPTH merged), BOM CSV, pick-and-place CSV,
and a zip ready to upload.

    /usr/bin/python3 tools/export_fab.py
"""
import csv
import os
import zipfile

import pcbnew

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PCB = os.path.join(ROOT, 'hardware', 'laser128-ramcard.kicad_pcb')
OUT = os.path.join(ROOT, 'hardware', 'fab')
NAME = 'laser128-ramcard'

LAYERS = [
    (pcbnew.F_Cu, 'F_Cu', 'gtl'), (pcbnew.B_Cu, 'B_Cu', 'gbl'),
    (pcbnew.F_SilkS, 'F_Silkscreen', 'gto'), (pcbnew.B_SilkS, 'B_Silkscreen', 'gbo'),
    (pcbnew.F_Mask, 'F_Mask', 'gts'), (pcbnew.B_Mask, 'B_Mask', 'gbs'),
    (pcbnew.F_Paste, 'F_Paste', 'gtp'), (pcbnew.B_Paste, 'B_Paste', 'gbp'),
    (pcbnew.Edge_Cuts, 'Edge_Cuts', 'gm1'),
]


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))
    board = pcbnew.LoadBoard(PCB)

    pc = pcbnew.PLOT_CONTROLLER(board)
    po = pc.GetPlotOptions()
    po.SetOutputDirectory(OUT)
    po.SetPlotFrameRef(False)
    po.SetUseGerberProtelExtensions(True)
    po.SetUseGerberX2format(True)
    po.SetIncludeGerberNetlistInfo(True)
    po.SetCreateGerberJobFile(False)
    po.SetSubtractMaskFromSilk(True)
    po.SetUseAuxOrigin(False)
    po.SetDrillMarksType(pcbnew.DRILL_MARKS_NO_DRILL_SHAPE)
    po.SetSkipPlotNPTH_Pads(False)
    po.SetPlotValue(True)
    po.SetPlotReference(True)
    for layer, suffix, _ in LAYERS:
        pc.SetLayer(layer)
        pc.OpenPlotfile(suffix, pcbnew.PLOT_FORMAT_GERBER, suffix)
        pc.PlotLayer()
    pc.ClosePlot()

    dw = pcbnew.EXCELLON_WRITER(board)
    dw.SetOptions(False, False, board.GetDesignSettings().GetAuxOrigin(), True)   # merge PTH+NPTH
    dw.SetFormat(True)    # metric
    dw.CreateDrillandMapFilesSet(OUT, True, False)

    # BOM grouped by value + footprint
    groups = {}
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref.startswith('H'):
            continue
        key = (fp.GetValue(), str(fp.GetFPID().GetUniStringLibItemName()))
        groups.setdefault(key, []).append(ref)
    with open(os.path.join(OUT, NAME + '-bom.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Comment', 'Designator', 'Footprint', 'Qty'])
        for (val, fpn), refs in sorted(groups.items(), key=lambda kv: kv[1][0]):
            w.writerow([val, ','.join(sorted(refs, key=lambda r: (r[0], int(''.join(c for c in r if c.isdigit()) or 0)))), fpn, len(refs)])

    # pick-and-place (all parts; JLCPCB column names)
    with open(os.path.join(OUT, NAME + '-cpl.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Designator', 'Val', 'Package', 'Mid X', 'Mid Y', 'Rotation', 'Layer'])
        ox, oy = 50.0, 50.0
        for fp in sorted(board.GetFootprints(), key=lambda x: x.GetReference()):
            p = fp.GetPosition()
            w.writerow([fp.GetReference(), fp.GetValue(), str(fp.GetFPID().GetUniStringLibItemName()),
                        '%.3f' % (pcbnew.ToMM(p.x) - ox), '%.3f' % (oy - pcbnew.ToMM(p.y)),
                        '%.1f' % fp.GetOrientationDegrees(), 'top' if fp.GetLayer() == pcbnew.F_Cu else 'bottom'])

    zpath = os.path.join(OUT, NAME + '-gerbers.zip')
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
        for fn in sorted(os.listdir(OUT)):
            if fn.endswith(('.gtl', '.gbl', '.gto', '.gbo', '.gts', '.gbs', '.gtp', '.gbp', '.gm1', '.drl')):
                z.write(os.path.join(OUT, fn), fn)
    print('\n'.join(sorted(os.listdir(OUT))))


if __name__ == '__main__':
    main()
