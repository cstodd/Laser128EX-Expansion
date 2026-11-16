#!/usr/bin/env python3
"""Build dist/LASERCLOCK.po: a 140K ProDOS data disk (not bootable) with the clock software.

Copy its files to your ProDOS boot disk (Filer, Copy II+, CiderPress, ADTPro, ...):
  CLOCK.SYSTEM  SYS  put it before BASIC.SYSTEM so ProDOS runs it first
  CLOCK.MAIN    BIN  BRUN from STARTUP (second copy of the driver in main memory)
  CLOCK.SET     BIN  used by SET.CLOCK
  SET.CLOCK     BAS  RUN it to set the date and time
  CARD.TEST     BAS  RUN it to test the card (RAM at 1/2.3/3.6 MHz, retention, clock)
  CARDTEST      BIN  used by CARD.TEST
  STARTUP       BAS  example STARTUP that BRUNs CLOCK.MAIN

The image is read back and checked (directory walk, file contents, BASIC detokenized).
"""
import os
import re
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, 'build')
DIST = os.path.join(HERE, 'dist')

# ---------------------------------------------------------------- Applesoft tokenizer
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


def prodos_name(s):
    return s.upper().encode()[:15].ljust(15, b'\0')


def build_image(volname, files):
    img = bytearray(512 * BLOCKS)
    used = set(range(0, 7))                            # boot 0-1, directory 2-5, bitmap 6
    nxt = [7]

    def alloc():
        while nxt[0] in used:
            nxt[0] += 1
        used.add(nxt[0])
        return nxt[0]

    def put(block, data):
        img[block * 512:block * 512 + len(data)] = data

    entries = []
    for name, ftype, aux, data in files:
        if len(data) <= 512:
            key = alloc(); put(key, data); storage, nblk = 1, 1
        else:
            key = alloc()
            blocks = [alloc() for _ in range((len(data) + 511) // 512)]
            idx = bytearray(512)
            for k, b in enumerate(blocks):
                put(b, data[k * 512:(k + 1) * 512])
                idx[k], idx[256 + k] = b & 255, b >> 8
            put(key, idx)
            storage, nblk = 2, len(blocks) + 1
        e = bytearray(39)
        e[0] = (storage << 4) | len(name)
        e[1:16] = prodos_name(name)
        e[16] = ftype
        struct.pack_into('<HH', e, 17, key, nblk)
        e[21:24] = struct.pack('<I', len(data))[:3]
        e[30] = 0xE3                                   # access: destroy/rename/write/read
        struct.pack_into('<H', e, 31, aux)
        struct.pack_into('<H', e, 37, 2)               # header pointer: volume directory key
        entries.append(e)

    # volume directory blocks 2-5 (13 entries per block; first entry = volume header)
    hdr = bytearray(39)
    hdr[0] = 0xF0 | len(volname)
    hdr[1:16] = prodos_name(volname)
    hdr[30], hdr[31], hdr[32] = 0xC3, 0x27, 0x0D
    struct.pack_into('<HHH', hdr, 33, len(entries), 6, BLOCKS)
    slots = [hdr] + entries
    assert len(slots) <= 4 * 13
    for k, blk in enumerate(range(2, 6)):
        d = bytearray(512)
        struct.pack_into('<HH', d, 0, blk - 1 if blk > 2 else 0, blk + 1 if blk < 5 else 0)
        for j in range(13):
            s = k * 13 + j
            if s < len(slots):
                d[4 + j * 39:4 + (j + 1) * 39] = slots[s]
        put(blk, d)
    bm = bytearray(512)                                # 1 = free
    for b in range(BLOCKS):
        if b not in used:
            bm[b >> 3] |= 0x80 >> (b & 7)
    put(6, bm)
    return bytes(img)


def read_image(img):
    """Independent reader used to verify the image."""
    files = {}
    blk = 2
    first = True
    while blk:
        d = img[blk * 512:(blk + 1) * 512]
        nxt = struct.unpack_from('<H', d, 2)[0]
        for j in range(13):
            e = d[4 + j * 39:4 + (j + 1) * 39]
            if first and j == 0:
                assert e[0] >> 4 == 0xF and struct.unpack_from('<H', e, 35)[0] == 6
                continue
            st, nl = e[0] >> 4, e[0] & 15
            if st == 0:
                continue
            name = e[1:1 + nl].decode()
            key = struct.unpack_from('<H', e, 17)[0]
            eof = e[21] | (e[22] << 8) | (e[23] << 16)
            if st == 1:
                data = img[key * 512:key * 512 + eof]
            else:
                idx = img[key * 512:(key + 1) * 512]
                data = b''.join(img[(idx[k] | (idx[256 + k] << 8)) * 512:][:512]
                                for k in range((eof + 511) // 512))[:eof]
            files[name] = (e[16], struct.unpack_from('<H', e, 31)[0], data)
        first = False
        blk = nxt
    return files


SET_CLOCK = '''
10 HOME : PRINT "LASER 128 CLOCK SETUP" : PRINT
20 PRINT CHR$(4);"BLOAD CLOCK.SET"
30 INPUT "YEAR (2000-2099): ";Y : IF Y < 2000 OR Y > 2099 THEN 30
40 INPUT "MONTH (1-12): ";M : IF M < 1 OR M > 12 THEN 40
50 INPUT "DAY (1-31): ";D : IF D < 1 OR D > 31 THEN 50
60 INPUT "HOUR (0-23): ";H : IF H < 0 OR H > 23 THEN 60
70 INPUT "MINUTE (0-59): ";N : IF N < 0 OR N > 59 THEN 70
80 REM WEEKDAY 1=SUNDAY (ZELLER)
90 Y1 = Y : M1 = M : IF M1 < 3 THEN M1 = M1 + 12 : Y1 = Y1 - 1
100 W = D + INT(13 * (M1 + 1) / 5) + Y1 + INT(Y1 / 4) - INT(Y1 / 100) + INT(Y1 / 400)
110 W = W + 6 : W = W - INT(W / 7) * 7 + 1
120 PRINT : PRINT "SECONDS START AT 0 WHEN YOU PRESS RETURN"
130 INPUT "PRESS RETURN TO SET: ";A$
140 POKE 768,Y - 2000 : POKE 769,M : POKE 770,D : POKE 771,H : POKE 772,N : POKE 773,0 : POKE 774,W
150 CALL 24576
160 IF PEEK(775) <> 0 THEN PRINT "CLOCK NOT FOUND" : END
170 PRINT "CLOCK SET."
'''

CARD_TEST = '''
10 TEXT : HOME : DEF FN B(X) = INT(X / 16) * 10 + X - INT(X / 16) * 16
20 PRINT "LASER 128 RAM + CLOCK CARD TEST" : PRINT
30 PRINT CHR$(4);"BLOAD CARDTEST"
40 PRINT "CPU SPEED: 1) 1 MHZ  2) 2.3 MHZ  3) 3.6 MHZ"
50 INPUT "CHOOSE (1-3): ";S : IF S < 1 OR S > 3 THEN 50
60 SP = 0 : IF S = 2 THEN SP = 128
70 IF S = 3 THEN SP = 192
80 POKE 49268,SP
90 PRINT : PRINT "1) QUICK RAM TEST (KEEPS RAM DISK)"
100 PRINT "2) FULL ADDRESS TEST (ERASES RAM DISK)"
110 PRINT "3) RETENTION CHECK (AFTER 2 + POWER OFF)"
120 PRINT "4) CLOCK TEST"
125 PRINT "5) BANK HOP TEST (KEEPS RAM DISK)"
130 PRINT "6) CHANGE SPEED  7) QUIT"
140 INPUT "CHOOSE (1-7): ";C : IF C < 1 OR C > 7 THEN 140
150 IF C = 7 THEN END
160 IF C = 6 THEN 40
170 IF C = 4 THEN 400
180 IF C = 2 THEN INPUT "ERASE ALL RAM DISK DATA (Y/N)? ";A$ : IF A$ <> "Y" THEN 90
190 POKE 768,C : POKE 777,0 : PRINT "TESTING ";
200 CALL 24576
210 IF C = 2 AND PEEK(769) = 0 THEN POKE 768,3 : CALL 24576
220 PRINT : R = PEEK(769)
230 IF R = 255 THEN PRINT "CARD NOT RESPONDING" : GOTO 90
240 IF R = 0 THEN PRINT "PASS" : GOTO 300
250 E = PEEK(775) + 256 * PEEK(776)
260 PRINT "FAIL: ";E;" ERRORS"; : IF E = 65535 THEN PRINT " OR MORE";
270 PRINT : N = PEEK(770) + 256 * PEEK(771) + 65536 * PEEK(772)
280 PRINT "FIRST AT $"; : GOSUB 600 : PRINT ": WROTE ";PEEK(773);", READ ";PEEK(774)
290 GOTO 90
300 IF C = 2 THEN PRINT "TEST PATTERN LEFT IN RAM. TO CHECK THE" : PRINT "BATTERY: POWER OFF, WAIT, THEN RUN 3."
310 IF C = 2 OR C = 3 THEN PRINT "RAM DISK ERASED: REFORMAT IT OR REBOOT."
320 GOTO 90
400 POKE 768,4 : CALL 24576 : IF PEEK(769) <> 0 THEN PRINT "CLOCK NOT FOUND" : GOTO 90
410 GOSUB 500 : S0 = PEEK(784)
420 FOR I = 1 TO 600 : POKE 768,4 : CALL 24576 : IF PEEK(784) <> S0 THEN 450
430 NEXT I
440 PRINT "CLOCK NOT RUNNING (SECONDS NOT CHANGING)" : GOTO 460
450 PRINT "CLOCK RUNNING" : GOSUB 500
460 IF PEEK(799) > 127 THEN PRINT "NOTE: OSCILLATOR STOPPED SINCE THE CLOCK" : PRINT "WAS SET (BATTERY?) - RUN SET.CLOCK."
470 GOTO 90
500 M = PEEK(789) : IF M > 127 THEN M = M - 128
510 H = PEEK(786) : IF H > 63 THEN H = H - 64
520 PRINT 2000 + FN B(PEEK(790));"-"; : V = FN B(M) : GOSUB 700 : PRINT "-"; : V = FN B(PEEK(788)) : GOSUB 700
530 PRINT " "; : V = FN B(H) : GOSUB 700 : PRINT ":"; : V = FN B(PEEK(785)) : GOSUB 700 : PRINT ":"; : V = FN B(PEEK(784)) : GOSUB 700 : PRINT
540 RETURN
600 H$ = "0123456789ABCDEF" : FOR K = 4 TO 0 STEP - 1 : P = 16 ^ K : D = INT(N / P) : N = N - D * P : PRINT MID$(H$,D + 1,1); : NEXT K : RETURN
700 PRINT RIGHT$("0" + STR$(V),2); : RETURN
'''

STARTUP = '''
10 PRINT CHR$(4);"BRUN CLOCK.MAIN"
'''


def main():
    os.makedirs(DIST, exist_ok=True)
    rd = lambda n: open(os.path.join(BUILD, n), 'rb').read()
    files = [
        ('CLOCK.SYSTEM', 0xFF, 0x2000, rd('CLOCK.SYSTEM')),
        ('CLOCK.MAIN', 0x06, 0x6000, rd('CLOCK.MAIN')),
        ('CLOCK.SET', 0x06, 0x6000, rd('CLOCK.SET')),
        ('CARDTEST', 0x06, 0x6000, rd('CARDTEST')),
        ('CARD.TEST', 0xFC, 0x0801, tokenize(CARD_TEST)),
        ('SET.CLOCK', 0xFC, 0x0801, tokenize(SET_CLOCK)),
        ('STARTUP', 0xFC, 0x0801, tokenize(STARTUP)),
    ]
    img = build_image('LASERCLOCK', files)
    out = os.path.join(DIST, 'LASERCLOCK.po')
    open(out, 'wb').write(img)
    for n in ('CLOCK.SYSTEM', 'CLOCK.MAIN', 'CLOCK.SET', 'CARDTEST'):
        shutil.copy(os.path.join(BUILD, n), os.path.join(DIST, n))
    # verify
    back = read_image(img)
    ok = True
    for name, ft, aux, data in files:
        got = back.get(name)
        good = got == (ft, aux, data)
        ok &= good
        print('%-13s type $%02X aux $%04X %5d bytes %s' % (name, ft, aux, len(data), 'ok' if good else 'MISMATCH'))
    for name, src in (('SET.CLOCK', SET_CLOCK), ('CARD.TEST', CARD_TEST), ('STARTUP', STARTUP)):
        print('--- %s (detokenized from the image)' % name)
        print(detokenize(back[name][2]))
    print('wrote', out)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
