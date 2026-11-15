#!/usr/bin/python3
"""Autoroute hardware/laser128-ramcard.kicad_pcb with Freerouting, then fill zones and run DRC.

    /usr/bin/python3 tools/route_pcb.py <path/to/freerouting-2.5.0-executable.jar> [java]

Freerouting 2.5.0 (Maven Central app.freerouting:freerouting) needs Java 25.
Analytics, GUI and API server are disabled on the command line.
"""
import os
import subprocess
import sys

import pcbnew

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PCB = os.path.join(ROOT, 'hardware', 'laser128-ramcard.kicad_pcb')
POWER_NETS = ('GND', '+5V', 'VBB', 'VBAT')
TIMEOUT = int(os.environ.get('ROUTE_TIMEOUT', '900'))


def mm(v):
    return pcbnew.FromMM(v)


def main(jar, java='java', passes=25):
    board = pcbnew.LoadBoard(PCB)
    ns = board.GetDesignSettings().m_NetSettings
    dc = ns.m_DefaultNetClass
    dc.SetTrackWidth(mm(0.25))
    dc.SetClearance(mm(0.2))
    dc.SetViaDiameter(mm(0.7))
    dc.SetViaDrill(mm(0.35))
    pc = pcbnew.NETCLASS('Power')
    pc.SetTrackWidth(mm(0.6))
    pc.SetClearance(mm(0.25))
    pc.SetViaDiameter(mm(0.9))
    pc.SetViaDrill(mm(0.45))
    ns.m_NetClasses['Power'] = pc
    for name, net in board.GetNetsByName().items():
        if str(name) in POWER_NETS:
            net.SetNetClass(pc)

    # remove old tracks/vias so the run is reproducible
    for t in list(board.GetTracks()):
        board.Remove(t)

    base = PCB[:-len('.kicad_pcb')]
    dsn, ses = base + '.dsn', base + '.ses'
    if not pcbnew.ExportSpecctraDSN(board, dsn):
        raise SystemExit('DSN export failed')
    cmd = [java, '-jar', jar, '-de', dsn, '-do', ses, '-mp', str(passes),
           '--gui.enabled=false', '--api_server.enabled=false',
           '--usage_and_diagnostic_data.disable_analytics=true']
    print(' '.join(cmd))
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        print('freerouting timed out after %ds; using its last saved result if any' % TIMEOUT)
    if not os.path.exists(ses):
        raise SystemExit('no session file produced')
    if not pcbnew.ImportSpecctraSES(board, ses):
        raise SystemExit('SES import failed')

    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    board.Save(PCB)
    rpt = base + '.drc.rpt'
    pcbnew.WriteDRCReport(board, rpt, pcbnew.EDA_UNITS_MILLIMETRES, True)
    for f in (dsn, ses):
        os.remove(f)
    print('routed; DRC report:', rpt)


if __name__ == '__main__':
    main(sys.argv[1], *(sys.argv[2:3] or ['java']))
