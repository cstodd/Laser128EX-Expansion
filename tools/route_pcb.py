#!/usr/bin/python3
"""Autoroute hardware/laser128-ramcard.kicad_pcb with Freerouting, then fill zones and run DRC.

    /usr/bin/python3 tools/route_pcb.py <path/to/freerouting-2.5.0-executable.jar> [java]

Freerouting 2.5.0 (Maven Central app.freerouting:freerouting) needs Java 25.
Analytics, GUI and API server are disabled on the command line.
"""
import os
import subprocess
import sys

import re

import pcbnew

sys.path.insert(0, os.path.dirname(__file__))
from sexp import parse, find, find1  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PCB = os.path.join(ROOT, 'hardware', 'laser128-ramcard.kicad_pcb')
POWER_NETS = ('GND', '+5V', 'VBB', 'VBAT')
TIMEOUT = int(os.environ.get('ROUTE_TIMEOUT', '900'))
JOB_TIMEOUT = os.environ.get('ROUTE_JOB_TIMEOUT', '00:12:00')   # freerouting stops itself and saves


def mm(v):
    return pcbnew.FromMM(v)


def main(jar, java='java', passes=25):
    board = pcbnew.LoadBoard(PCB)
    ns = board.GetDesignSettings().m_NetSettings
    dc = ns.m_DefaultNetClass
    board.GetDesignSettings().m_TrackMinWidth = mm(0.15)   # router squeezes 0.187 mm between TSOP pads
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
    import_only = bool(os.environ.get('ROUTE_IMPORT_ONLY'))
    move_power_nets(dsn)
    cmd = [java, '-jar', jar, '-de', dsn, '-do', ses,
           '--gui.enabled=false', '--api_server.enabled=false',
           '--router.autorouter.max_passes=%d' % passes, '--router.optimizer.enabled=false',
           '--router.automatic_neckdown=false', '--router.copper_to_edge_clearance_um=600',
           '--router.job_timeout=%s' % JOB_TIMEOUT,
           '--usage_and_diagnostic_data.disable_analytics=true']
    print(' '.join(cmd))
    try:
        if not import_only:
          subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        print('freerouting timed out after %ds; using its last saved result if any' % TIMEOUT)
    if not os.path.exists(ses):
        raise SystemExit('no session file produced')
    ntracks, nvias = import_ses(board, ses)
    print('imported %d track segments, %d vias' % (ntracks, nvias))

    # drop vias with no track at all (router leftovers); GND vias may legitimately
    # connect a single track to the pour on the other layer, so keep those
    tracks = list(board.GetTracks())
    segs = [x for x in tracks if x.GetClass() == 'PCB_TRACK']
    for v in [x for x in tracks if x.GetClass() == 'PCB_VIA']:
        if v.GetNetname() == 'GND':
            continue
        if not any(s.GetNetCode() == v.GetNetCode() and
                   (s.GetStart() == v.GetPosition() or s.GetEnd() == v.GetPosition()) for s in segs):
            board.Remove(v)

    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    board.Save(PCB)
    rpt = base + '.drc.rpt'
    pcbnew.WriteDRCReport(board, rpt, pcbnew.EDA_UNITS_MILLIMETRES, True)
    print('routed; DRC report:', rpt)


def move_power_nets(dsn):
    """KiCad 7's DSN exporter ignores per-net classes set from Python; move the power nets
    from the default class into the Power class by editing the DSN text."""
    s = open(dsn).read()
    for n in POWER_NETS:
        s = re.sub(r'(\(class kicad_default[^()]*?)\s%s(?=[\s)])' % re.escape(n), r'\1', s, count=1)
    s = s.replace('(class Power', '(class Power ' + ' '.join(POWER_NETS), 1)
    open(dsn, 'w').write(s)


def import_ses(board, ses):
    """Minimal Specctra session importer (KiCad 7's ImportSpecctraSES needs the GUI).
    SES units: 'resolution um 10' => 0.1 um, Y axis inverted, page coordinates."""
    t = parse(open(ses).read())
    routes = find1(t, 'routes')
    res = find1(routes, 'resolution')
    per_mm = {'um': 1000.0, 'mm': 1.0, 'mil': 1000 / 25.4, 'inch': 1 / 25.4}[str(res[1])] * float(res[2])
    layers = {'F.Cu': pcbnew.F_Cu, 'B.Cu': pcbnew.B_Cu}
    padstacks = {}
    for ps in find(find1(routes, 'library_out') or [], 'padstack'):
        m = re.search(r'_(\d+):(\d+)_um', ps[1])
        padstacks[ps[1]] = (int(m.group(1)), int(m.group(2))) if m else (700, 350)
    nets = board.GetNetsByName()

    def xy(x, y):
        return pcbnew.VECTOR2I(pcbnew.FromMM(float(x) / per_mm), pcbnew.FromMM(-float(y) / per_mm))

    nt = nv = 0
    for net in find(find1(routes, 'network_out'), 'net'):
        ni = nets[net[1]]
        for w in find(net, 'wire'):
            path = find1(w, 'path')
            layer, width, pts = layers[str(path[1])], float(path[2]), path[3:]
            pts = [p for p in pts if not isinstance(p, list)]
            for i in range(0, len(pts) - 2, 2):
                tr = pcbnew.PCB_TRACK(board)
                tr.SetStart(xy(pts[i], pts[i + 1]))
                tr.SetEnd(xy(pts[i + 2], pts[i + 3]))
                tr.SetWidth(pcbnew.FromMM(width / per_mm))
                tr.SetLayer(layer)
                tr.SetNet(ni)
                board.Add(tr)
                nt += 1
        for v in find(net, 'via'):
            dia, drill = padstacks.get(v[1], (700, 350))
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(xy(v[2], v[3]))
            via.SetWidth(pcbnew.FromMM(dia / 1000.0))
            via.SetDrill(pcbnew.FromMM(drill / 1000.0))
            via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            via.SetNet(ni)
            board.Add(via)
            nv += 1
    return nt, nv


if __name__ == '__main__':
    main(sys.argv[1], *(sys.argv[2:3] or ['java']))
