"""Bootable ProDOS tool disks.

boot_image(volname, files, run) builds a 140K ProDOS-order disk with the ProDOS 2.4 boot blocks, PRODOS and
BASIC.SYSTEM (taken from prodos/ProDOS_2_4.dsk), the given files, and a STARTUP program that does BRUN `run`.
Also: dos_to_po() for DOS-order (.dsk) images, read_files() for any ProDOS image (seedling, sapling, tree files
in the volume directory), and an Applesoft tokenizer.
"""
import os, re, struct
import mkdisk
HERE = os.path.dirname(os.path.abspath(__file__))
PRODOS_DSK = os.path.join(HERE, 'prodos', 'ProDOS_2_4.dsk')

def dos_to_po(raw):
    m = [0, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 15]
    out = bytearray(len(raw))
    for t in range(len(raw) // 4096):
        for k in range(16):
            out[t * 4096 + k * 256:t * 4096 + k * 256 + 256] = raw[t * 4096 + m[k] * 256:t * 4096 + m[k] * 256 + 256]
    return bytes(out)

def _blk(img, b): return img[b * 512:(b + 1) * 512]

def read_files(img):
    """{name: (type, aux, data, storage)} for the files in the volume directory (subdirectories listed, not read)."""
    files = {}; blk = 2; first = True
    while blk:
        d = _blk(img, blk); nxt = struct.unpack_from('<H', d, 2)[0]
        for j in range(13):
            e = d[4 + j * 39:4 + (j + 1) * 39]
            if first and j == 0: continue
            st, nl = e[0] >> 4, e[0] & 15
            if st == 0: continue
            name = e[1:1 + nl].decode()
            key = struct.unpack_from('<H', e, 17)[0]
            eof = e[21] | (e[22] << 8) | (e[23] << 16)
            def ptrs(b): x = _blk(img, b); return [x[k] | x[256 + k] << 8 for k in range(256)]
            if st == 1: data = _blk(img, key)[:eof]
            elif st == 2: data = b''.join(_blk(img, p) for p in ptrs(key)[:(eof + 511) // 512])[:eof]
            elif st == 3:
                n = (eof + 511) // 512; out = []
                for ib in ptrs(key)[:(n + 255) // 256]: out += ptrs(ib)
                data = b''.join(_blk(img, p) for p in out[:n])[:eof]
            else: data = None
            files[name] = (e[16], struct.unpack_from('<H', e, 31)[0], data, st)
        first = False; blk = nxt
    return files

# ---- Applesoft tokenizer (from cstodd/Laser128EX-Expansion software/rev01/mkdisk.py)
TOKENS = ('END FOR NEXT DATA INPUT DEL DIM READ GR TEXT PR# IN# CALL PLOT HLIN VLIN HGR2 HGR '
          'HCOLOR= HPLOT DRAW XDRAW HTAB HOME ROT= SCALE= SHLOAD TRACE NOTRACE NORMAL INVERSE '
          'FLASH COLOR= POP VTAB HIMEM: LOMEM: ONERR RESUME RECALL STORE SPEED= LET GOTO RUN IF '
          'RESTORE & GOSUB RETURN REM STOP ON WAIT LOAD SAVE DEF POKE PRINT CONT LIST CLEAR GET '
          'NEW TAB( TO FN SPC( THEN AT NOT STEP + - * / ^ AND OR > = < SGN INT ABS USR FRE SCRN( '
          'PDL POS SQR RND LOG EXP COS SIN TAN ATN PEEK LEN STR$ VAL ASC CHR$ LEFT$ RIGHT$ MID$').split()
assert len(TOKENS) == 0xEB - 0x80, len(TOKENS)


def tokenize_line(text):
    out = bytearray()
    i, n = 0, len(text)
    in_data = False
    while i < n:
        c = text[i]
        if c == '"':                                   # string literal: copy verbatim
            j = text.find('"', i + 1)
            j = n if j < 0 else j + 1
            out += text[i:j].encode()
            i = j
            continue
        if in_data:
            if c == ':':
                in_data = False
            out += c.encode()
            i += 1
            continue
        if c == ' ':
            i += 1
            continue
        best = None                                    # longest keyword at i, ignoring spaces
        for t, kw in enumerate(TOKENS):
            k, m = i, 0
            while m < len(kw) and k < n:
                if text[k] == ' ':
                    k += 1
                    continue
                if text[k].upper() != kw[m]:
                    break
                k += 1
                m += 1
            if m == len(kw) and (best is None or len(kw) > len(TOKENS[best])):
                best, bend = t, k
        if best is not None:
            out.append(0x80 + best)
            i = bend
            if TOKENS[best] == 'REM':                  # rest of line verbatim
                out += text[i:].lstrip(' ').encode()
                break
            if TOKENS[best] == 'DATA':
                in_data = True
            continue
        out += c.upper().encode()
        i += 1
    return bytes(out)


def tokenize(src, base=0x0801):
    prog = bytearray()
    addr = base
    for line in src.strip().splitlines():
        m = re.match(r'\s*(\d+)\s*(.*)$', line)
        num, body = int(m.group(1)), m.group(2)
        body = tokenize_line(body) + b'\0'
        nxt = addr + 4 + len(body)
        prog += struct.pack('<HH', nxt, num) + body
        addr = nxt
    return bytes(prog + b'\0\0')


def detokenize(prog, base=0x0801):
    lines, p = [], 0
    while True:
        nxt = struct.unpack_from('<H', prog, p)[0]
        if nxt == 0:
            return '\n'.join(lines)
        num = struct.unpack_from('<H', prog, p + 2)[0]
        end = prog.index(0, p + 4)
        s = ''.join(' %s ' % TOKENS[b - 0x80] if b >= 0x80 else chr(b) for b in prog[p + 4:end])
        lines.append('%d %s' % (num, re.sub(' +', ' ', s).strip()))
        p = nxt - base


# ---------------------------------------------------------------- ProDOS volume writer
BLOCKS = 280

def prodos_parts():
    img = dos_to_po(open(PRODOS_DSK, 'rb').read())
    f = read_files(img)
    return img[:1024], f['PRODOS'], f['BASIC.SYSTEM']

def boot_image(volname, files, run=None, startup=None, sys_first=()):
    """Bootable disk: ProDOS 2.4 boot blocks, PRODOS, then sys_first (.SYSTEM files that must run before
    BASIC.SYSTEM, e.g. a clock driver that chains to it), BASIC.SYSTEM, files, and a STARTUP program.
    files and sys_first: [(name, type, aux, data)]. STARTUP is `BRUN run` if run is given, else the Applesoft
    listing in startup (or none if both are None)."""
    boot, prodos, basic = prodos_parts()
    allf = [('PRODOS', prodos[0], prodos[1], prodos[2])] + list(sys_first) + \
           [('BASIC.SYSTEM', basic[0], basic[1], basic[2])] + list(files)
    if run: startup = '10 PRINT CHR$(4)"BRUN %s"' % run
    if startup: allf.append(('STARTUP', 0xFC, 0x0801, tokenize(startup)))
    img = bytearray(mkdisk.build_image(volname, allf))
    img[:1024] = boot
    back = read_files(bytes(img))
    for n, t, a, d in allf: assert back[n][:3] == (t, a, d), n
    return bytes(img)
