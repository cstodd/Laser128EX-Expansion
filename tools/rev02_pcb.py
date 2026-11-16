#!/usr/bin/env python3
"""Rev 0.2 PCB edit (hardware/rev02), KiCad 10 pcbnew API. Step 1 ('prep'):
  - U8 footprint SOIC-16W -> SOIC-20W_7.5x12.8mm (same position/orientation, linked to the schematic symbol)
  - every pad's net from the rev 0.2 schematic netlist (kicad-cli export)
  - rip up SDA, SCL, MEMRD completely; remove +5V/VBAT stubs left dangling at the old U8 pins and R1/R2
Step 2 ('route'): lock all remaining tracks, Freerouting routes only what's missing, import, refill zones."""
import os, subprocess, sys
import pcbnew
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from sexp import parse
HW = os.path.join(ROOT, 'hardware', 'rev02')
PCB = os.path.join(HW, 'laser128-ramcard.kicad_pcb')
SCH = os.path.join(HW, 'laser128-ramcard.kicad_sch')
FPLIB = '/usr/share/kicad/footprints/Package_SO.pretty'
mm = pcbnew.FromMM

def netlist():
    out = os.path.join(HW, 'rev02.net')
    subprocess.check_call(['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', out, SCH],
                          stdout=subprocess.DEVNULL)
    t = parse(open(out).read()); os.remove(out); m = {}
    for n in [x for x in t if isinstance(x, list) and x[0] == 'nets'][0][1:]:
        name = [x for x in n if isinstance(x, list) and x[0] == 'name'][0][1]
        for node in [x for x in n if isinstance(x, list) and x[0] == 'node']:
            g = {x[0]: x[1] for x in node if isinstance(x, list)}
            m[(g['ref'], g['pin'])] = name
    return m

def net(board, name):
    n = board.FindNet(name)
    if n is None:
        n = pcbnew.NETINFO_ITEM(board, name); board.Add(n)
    return n

def touches(board, item_pt, netname, skip):
    """Is point item_pt connected to something else on netname (pad, via, or another track)?"""
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() == netname and p.HitTest(item_pt):
                return True
    for t in board.GetTracks():
        if t is skip or t.GetNetname() != netname:
            continue
        if t.Type() == pcbnew.PCB_VIA_T:
            if (t.GetPosition() - item_pt).EuclideanNorm() <= t.GetWidth(pcbnew.F_Cu) // 2:
                return True
        elif t.GetStart() == item_pt or t.GetEnd() == item_pt or t.HitTest(item_pt):
            return True
    return False

def prep():
    board = pcbnew.LoadBoard(PCB)
    nets = netlist()
    old = board.FindFootprintByReference('U8')
    new = pcbnew.FootprintLoad(FPLIB, 'SOIC-20W_7.5x12.8mm_P1.27mm')
    new.SetFPID(pcbnew.LIB_ID('Package_SO', 'SOIC-20W_7.5x12.8mm_P1.27mm'))
    pos = old.GetPosition(); pos.y += mm(0.5)          # 0.5 mm down: the longer body clears C5's courtyard
    new.SetPosition(pos); new.SetOrientation(old.GetOrientation())
    new.SetReference('U8'); new.SetValue('DS3234SN#')
    new.SetPath(old.GetPath()); new.SetSheetname(old.GetSheetname()); new.SetSheetfile(old.GetSheetfile())
    new.Reference().SetPosition(old.Reference().GetPosition())
    board.Remove(old); board.Add(new)
    # net names as the KiCad 10 schematic gives them (local labels on the root sheet are '/NAME');
    # rev 0.1 has the same 199 name-only parity conflicts. No net classes are assigned by name.
    names = set(nets.values())
    for ni in list(board.GetNetsByName().values()):
        n = str(ni.GetNetname())
        if n and not n.startswith('/') and '/' + n in names:
            ni.SetNetname('/' + n)
    changed = 0
    for fp in board.GetFootprints():
        for p in fp.Pads():
            name = nets.get((fp.GetReference(), p.GetNumber()))
            if name is None:
                continue
            if p.GetNetname() != name:
                p.SetNet(net(board, name)); changed += 1
    # One snapshot of the tracks, decide in Python, remove in one pass: KiCad's SWIG wrappers break if
    # GetTracks() is called again after Remove().
    tracks = list(board.GetTracks())
    kill = set(i for i, tr in enumerate(tracks) if str(tr.GetNetname()).lstrip('/') in ('SDA', 'SCL', 'MEMRD'))
    pads = [p for fp in board.GetFootprints() for p in fp.Pads()]
    # stale copper: any track/via touching a pad of another net (old routing under the new U8 pads, the old
    # +5V feed into R1/R2 pad 1) goes; the dangling pass below then removes what it leaves behind
    for i, tr in enumerate(tracks):
        if i in kill: continue
        lay = tr.GetLayer() if tr.Type() != pcbnew.PCB_VIA_T else None
        for p in pads:
            if p.GetNetname() == tr.GetNetname() or (lay is not None and not p.IsOnLayer(lay)):
                continue
            if p.GetEffectiveShape(lay if lay is not None else pcbnew.F_Cu).Collide(tr.GetEffectiveShape(lay if lay is not None else pcbnew.F_Cu)):
                kill.add(i); break
    # dangling pass: only the signal/power nets that lost copper (+5V, VBAT and any hit above). Never GND:
    # its vias connect through the pours, so 'fewer than two tracks' doesn't mean dangling there.
    affected = (set(str(tracks[i].GetNetname()) for i in kill) | {'/+5V', '/VBAT'}) - {'/GND', '/SDA', '/SCL', '/MEMRD', 'SDA', 'SCL', 'MEMRD'}
    def connected(pt, netname, me):
        if any(p.GetNetname() == netname and p.HitTest(pt) for p in pads):
            return True
        for j, o in enumerate(tracks):
            if j == me or j in kill or o.GetNetname() != netname:
                continue
            if o.Type() == pcbnew.PCB_VIA_T:
                if (o.GetPosition() - pt).EuclideanNorm() <= o.GetWidth(pcbnew.F_Cu) // 2:
                    return True
            elif o.GetStart() == pt or o.GetEnd() == pt or o.HitTest(pt):
                return True
        return False
    while True:
        gone = []
        for i, tr in enumerate(tracks):
            if i in kill or str(tr.GetNetname()) not in affected:
                continue
            if tr.Type() == pcbnew.PCB_VIA_T:
                n = sum(1 for j, s in enumerate(tracks) if j != i and j not in kill and s.Type() != pcbnew.PCB_VIA_T
                        and s.GetNetname() == tr.GetNetname() and tr.GetPosition() in (s.GetStart(), s.GetEnd()))
                if n <= 1 and not any(p.GetNetname() == tr.GetNetname() and p.HitTest(tr.GetPosition()) for p in pads):
                    gone.append(i)
            elif not (connected(tr.GetStart(), tr.GetNetname(), i) and connected(tr.GetEnd(), tr.GetNetname(), i)):
                gone.append(i)
        if not gone:
            break
        kill.update(gone)
    # leftover ground copper from the old U8 pin-to-pin links: GND segments inside U8's area with a free end
    box = new.GetBoundingBox(False); box.Inflate(mm(1))
    while True:
        more = [i for i, tr in enumerate(tracks)
                if i not in kill and tr.Type() != pcbnew.PCB_VIA_T and str(tr.GetNetname()) == '/GND'
                and (box.Contains(tr.GetStart()) or box.Contains(tr.GetEnd()))
                and not (connected(tr.GetStart(), tr.GetNetname(), i) and connected(tr.GetEnd(), tr.GetNetname(), i))]
        if not more:
            break
        kill.update(more)
    removed = len(kill)
    for i in sorted(kill):
        board.Remove(tracks[i])
    for n in ('SDA', 'SCL'):
        ni = board.FindNet(n)
        if ni: board.Remove(ni)
    # starved thermals: U8's grounded pads (N.C. 2, 7-14, GND 15) and J1 pin 28 get solid pour connections
    for ref, nums in (('U8', [str(n) for n in (2, 7, 8, 9, 10, 11, 12, 13, 14, 15)]), ('J1', ['28'])):
        fp = board.FindFootprintByReference(ref)
        for p in fp.Pads():
            if p.GetNumber() in nums:
                p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.Save(PCB)
    print('U8 swapped; %d pad nets changed; %d track/via items removed (SDA/SCL/MEMRD + dangling +5V/VBAT)' % (changed, removed))

def touches_pad(board, pt, netname):
    return any(p.GetNetname() == netname and p.HitTest(pt) for fp in board.GetFootprints() for p in fp.Pads())

if __name__ == '__main__':
    {'prep': prep}[sys.argv[1]]()
