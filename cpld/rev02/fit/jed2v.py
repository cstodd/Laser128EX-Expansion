#!/usr/bin/env python3
"""Decode an ATF1504AS (PLCC-44) .jed back into Verilog, independently of the Atmel fitter.

Uses only the fuse file and Project Bureau's fuse database (github.com/whitequark/prjbureau,
database.json). It does not read the fitter's report or equations, so running the testbench on
its output checks the actual fuses.

    jed2v.py PRJBUREAU_DIR design.jed pins.txt > decoded.v

Macrocell model (zero delay). Sources:
  * PT routing, clock/CE, AR, AS/OE and D/Q/FB muxes: prjbureau docs/options/logic.rst tables.
  * XOR / cascade / foldback / polarity: the hardware-measured truth table at the end of
    prjbureau notes/xor.txt. Let A = sum if xor_a_mux = sum, else (pt2 if pt2_mux = xor, else 1).
    xor_invert = on gives out = A; xor_invert = off gives out = A ^ B, where B = pt2 when
    pt2_mux = xor and xor_a_mux = sum, else 1 (xor_b_mux = ff_qn is not handled: this design
    doesn't use it, and the script stops if it sees it). CASOUT = sum when
    xor_a_mux = VCC_pt2, else 0. FLB = ~pt1 when pt1_mux = flb.
    Which way round 'on'/'off' go: the notes name the fuse differently (o_inv). Here 'on' =
    non-inverting, which agrees with the fuzzer 008 comment (a DFF with D=1'b0 or 1'b1 differs only
    in xor_a_mux, with xor_invert left at its default 'on').
  * Cascade direction MC(n) -> MC(n+1): not in the database. Taken from the fitter report's
    CascadeOut column. If wrong, the key matcher (which uses cascades) fails the testbench.
Only the features this design uses are modelled; anything else stops the script.
"""
import json, re, sys

pb, jed_path, pins_path = sys.argv[1:4]
db = json.load(open(pb + '/database.json'))['ATF1504AS']

# ---------------------------------------------------------------- JED parse
txt = open(jed_path).read()
nfuse = int(re.search(r'QF(\d+)', txt).group(1))
default = re.search(r'\*\s*F([01])\s*\*', txt)
fuses = [int(default.group(1)) if default else 0] * nfuse
for m in re.finditer(r'\*\s*L(\d+)\s+([01\s]+)', txt):
    base, bits = int(m.group(1)), re.sub(r'\s', '', m.group(2))
    for i, b in enumerate(bits): fuses[base + i] = int(b)

def field(f, default=None):
    v = sum(fuses[x] << i for i, x in enumerate(f['fuses']))
    for k, kv in f['values'].items():
        if kv == v: return k
    if default is not None: return default
    raise SystemExit('unknown fuse value %d for %s' % (v, f))

# ---------------------------------------------------------------- pins / names
pin_of_pad = db['pins']['PLCC44']                     # 'M1' -> '12', 'C2' -> '2', ...
name_of_pin = {}
for l in open(pins_path):
    m = re.match(r'//PIN:\s*(\w+)\s*:\s*(\d+)', l)
    if m: name_of_pin[m.group(2)] = m.group(1)
def pad_net(pad):                                       # 'M33' -> net carrying that pin's level
    pin = pin_of_pad[pad]
    n = name_of_pin.get(pin)
    return n if n and n not in ('TDI', 'TMS', 'TCK', 'TDO') else 'pin%s' % pin

def src_net(s):
    if s.startswith('GND'): return "1'b0"
    m = re.match(r'(M\d+|C\d|E\d|R)_PAD$', s)
    if m: return pad_net(m.group(1))
    m = re.match(r'MC(\d+)_FB$', s)
    if m: return 'mc%s_fb' % m.group(1)
    raise SystemExit('unknown source ' + s)

uim = {name: src_net(field(sw['mux'])) for name, sw in db['switches'].items()}

# The prjbureau database (Mar 2025) lacks d_mux, dfast_mux, o_mux and oe_mux for ATF1504AS MC46 only.
# Those fields step regularly between same-parity macrocells, so fill a gap from MC(n-2)/MC(n+2):
# fuse numbers interpolated, value encoding copied. The filled fuses are checked to be unclaimed.
patched = []
claimed = set()
def _walk(o):
    if isinstance(o, dict):
        if isinstance(o.get('fuses'), list): claimed.update(o['fuses'])
        for v in o.values(): _walk(v)
_walk(db)
mcs = db['macrocells']; names = list(mcs)
allf = set().union(*[set(v) for v in mcs.values()])
for i, n in enumerate(names):
    for f in sorted(allf - set(mcs[n])):
        lo, hi = mcs[names[i - 2]][f], mcs[names[i + 2]][f]
        assert lo['values'] == hi['values'] and len(lo['fuses']) == len(hi['fuses'])
        fz = [(a + b) // 2 for a, b in zip(lo['fuses'], hi['fuses'])]
        assert all((a + b) % 2 == 0 for a, b in zip(lo['fuses'], hi['fuses']))
        mcs[n][f] = {'fuses': fz, 'values': lo['values']}
        patched.append((n, f, fz))
for n, f, fz in patched:
    # o_mux and dfast_mux share a fuse by design; anything else must be new
    assert not (set(fz) & claimed), (n, f, fz)

def glob(name):
    g = db['globals'][name]
    inv = field(g['invert']) == 'on' if 'invert' in g else False
    s = src_net(field(g['mux'])) if 'mux' in g else pad_net(db['specials']['CLR'])
    return ('~%s' % s) if inv else s

# ---------------------------------------------------------------- product terms
mc_names = list(db['macrocells'])
def pterm(block, rng):
    pts = db['blocks'][block]['pterm_points']
    lits = []
    for name, idx in pts.items():
        if fuses[rng[0] + idx] == 0:                    # 0 = connected
            if name.endswith('_FLB'): lits.append('mc%s_flb' % name[2:-4])
            else:
                net = uim[name[:-2]]
                lits.append(net if name.endswith('_P') else '~' + net)
    if len(lits) == len(pts): return "1'b0"             # every input connected: x & ~x
    return '(' + ' & '.join(lits) + ')' if lits else "1'b1"

out = ['// generated by jed2v.py from %s: do not edit' % jed_path, '`timescale 1ns/1ps',
       'module laser128_ramcard(input wire rasb_n, ecas1_n, ecas2_n, ecas3_n, ecas4_n, e1moe_n,',
       '  input wire rwr_n, era8, pwr_rst_n,',
       '  output wire rowclk, col_le, ma8, ma17, ma18, ram_ce_n, oe0_n, oe1_n, we0_n, we1_n, buf_oe_n, dbg0,',
       '  output wire rtc_cs_n, rtc_sclk, inout wire [7:0] xd, inout wire rtc_dio);']
for i in range(8): out.append('  wire xd_%d = xd[%d];' % (i, i))
report = []
for n, mcn in enumerate(mc_names):
    mc = db['macrocells'][mcn]; k = mcn[2:]; c = {o: field(mc[o]) for o in mc if isinstance(mc[o], dict) and 'fuses' in mc[o]}
    pad = mc['pad']
    pin = pin_of_pad.get(pad)
    if c['pt_power'] == 'off':
        if pin and c['oe_mux'] != 'GND': raise SystemExit(mcn + ': unpowered but output enabled')
        out.append('  wire mc%s_fb = 1\'b0, mc%s_flb = 1\'b1, mc%s_cas = 1\'b0;' % (k, k, k))
        if pin: report.append('%s pin %s (%s): no logic, output off (oe_mux=%s)' % (mcn, pin, pad_net(pad), c['oe_mux']))
        continue
    if c['xor_b_mux'] != 'VCC_pt12': raise SystemExit(mcn + ': xor_b_mux ff_qn not modelled')
    pt = {i: pterm(mc['block'], mc['pterm_ranges']['PT%d' % i]) for i in range(1, 6)}
    st = []
    if c['pt1_mux'] == 'sum': st.append(pt[1])
    if c['pt2_mux'] == 'sum': st.append(pt[2])
    if c['pt3_mux'] == 'sum': st.append(pt[3])
    if c['pt4_mux'] == 'sum': st.append(pt[4])
    if c['pt5_mux'] == 'sum': st.append(pt[5])
    if n > 0 and mc_names[n - 1] in db['blocks'][mc['block']]['macrocells']:
        st.append('mc%s_cas' % mc_names[n - 1][2:])       # cascade from the macrocell below
    out.append('  wire mc%s_st = %s;' % (k, ' | '.join(st) if st else "1'b0"))
    A = 'mc%s_st' % k if c['xor_a_mux'] == 'sum' else (pt[2] if c['pt2_mux'] == 'xor' else "1'b1")
    B = pt[2] if (c['pt2_mux'] == 'xor' and c['xor_a_mux'] == 'sum') else "1'b1"
    xt = A if c['xor_invert'] == 'on' else '(%s ^ %s)' % (A, B)
    out.append('  wire mc%s_xt = %s;' % (k, xt))
    out.append('  wire mc%s_cas = %s;' % (k, 'mc%s_st' % k if c['xor_a_mux'] == 'VCC_pt2' else "1'b0"))
    out.append('  wire mc%s_flb = %s;' % (k, '~' + pt[1] if c['pt1_mux'] == 'flb' else "1'b1"))
    # flip-flop
    gclk = glob(c['gclk_mux'])
    if c['pt4_mux'] == 'clk_ce': clk, ce = (pt[4], "1'b1") if c['pt4_func'] == 'clk' else (gclk, pt[4])
    else:                        clk, ce = ("1'b1", "1'b1") if c['pt4_func'] == 'clk' else (gclk, "1'b1")
    ar = []
    if c['pt3_mux'] == 'ar': ar.append(pt[3])
    if c['gclr_mux'] == 'GCLR': ar.append(glob('GCLR'))
    ar = ' | '.join(ar) or "1'b0"
    as_ = pt[5] if (c['pt5_mux'] == 'as_oe' and c['pt5_func'] == 'as') else "1'b0"
    if c['storage'] != 'dff': raise SystemExit(mcn + ': latch not modelled')
    d = 'mc%s_xt' % k if c['d_mux'] == 'comb' else (pt[2] if c['dfast_mux'] == 'pt2' else pad_net(pad))
    out.append('  wire mc%s_clk = %s, mc%s_ce = %s, mc%s_ar = %s, mc%s_as = %s;' % (k, clk, k, ce, k, ar, k, as_))
    out.append('  reg mc%s_q = 0;' % k)
    out.append('  always @(posedge mc%s_clk or posedge mc%s_ar or posedge mc%s_as)'
               ' if (mc%s_ar) mc%s_q <= 0; else if (mc%s_as) mc%s_q <= 1; else if (mc%s_ce) mc%s_q <= %s;'
               % (k, k, k, k, k, k, k, k, k, d))
    out.append('  wire mc%s_fb = %s;' % (k, 'mc%s_xt' % k if c['fb_mux'] == 'comb' else 'mc%s_q' % k))
    # output
    if pin:
        if c['oe_mux'] == 'GND': oe = "1'b0"
        elif c['oe_mux'] == 'VCC_pt5': oe = pt[5] if (c['pt5_mux'] == 'as_oe' and c['pt5_func'] == 'oe') else "1'b1"
        else: oe = glob(c['oe_mux'])
        a = 'mc%s_xt' % k if c['o_mux'] == 'comb' else 'mc%s_q' % k
        net = pad_net(pad)
        if oe == "1'b0":
            report.append('%s pin %s (%s): input only' % (mcn, pin, net)); continue
        if net.startswith('pin'): raise SystemExit('%s drives JTAG/unnamed pin %s' % (mcn, pin))
        drv = "%s ? 1'b0 : 1'bz" % a if c['output_driver'] == 'open_drain' else a
        tgt = 'xd[%s]' % net[3] if net.startswith('xd_') else net
        out.append("  assign %s = (%s) ? (%s) : 1'bz;" % (tgt, oe, drv))
        report.append('%s pin %s (%s): output, oe=%s' % (mcn, pin, net, oe))
cfg = {k: field(v) for k, v in db['config'].items() if 'fuses' in v}
out.append('endmodule')
print('\n'.join(out))
print('// ' + '\n// '.join(report), file=sys.stderr)
print('// config: ' + ', '.join('%s=%s' % kv for kv in sorted(cfg.items())), file=sys.stderr)
for n, f, fz in patched:
    print('// NOTE: %s.%s missing from database, inferred at fuses %s -> %s'
          % (n, f, fz, field(db['macrocells'][n][f])), file=sys.stderr)
