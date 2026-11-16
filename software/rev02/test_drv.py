#!/usr/bin/env python3
"""Rev 0.2 driver test: 65C02 emulation (software/rev01/test/harness.py) with the rev02 CPLD port and a DS3234."""
import os, random, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'rev01', 'test'))
import harness as H

class DS3234:
    """SPI mode 3, one clock per call. Registers 00h-13h (BCD time in 00h-06h)."""
    def __init__(self, y, mo, d, h, mi, s, dow=1):
        self.regs = [0] * 0x14
        self.set(y, mo, d, h, mi, s, dow)
        self.selected = False
        self.clocks = 0
    def set(self, y, mo, d, h, mi, s, dow=1):
        self.regs[0:7] = [H.bcd(s), H.bcd(mi), H.bcd(h), dow, H.bcd(d), H.bcd(mo), H.bcd(y % 100)]
    def select(self, on):
        if on and not self.selected:
            self.nbit, self.sh, self.addr, self.rmode, self.dout = 0, 0, None, False, None
        if not on:
            self.dout = None
        self.selected = on
    def clock(self, din):
        """Falling edge (shift out), then rising edge (latch din). Returns DOUT after the falling edge."""
        if not self.selected:
            return None
        self.clocks += 1
        if self.addr is not None and self.rmode:     # falling edge: next data bit out
            self.dout = (self.regs[self.addr % 0x14] >> (7 - self.nbit)) & 1
        # rising edge
        if self.addr is None:
            self.sh = ((self.sh << 1) | din) & 0xFF
            self.nbit += 1
            if self.nbit == 8:
                self.addr, self.rmode, self.nbit = self.sh & 0x7F, not (self.sh & 0x80), 0
        elif self.rmode:
            self.nbit += 1
            if self.nbit == 8:
                self.nbit, self.addr = 0, self.addr + 1
        else:
            self.sh = ((self.sh << 1) | din) & 0xFF
            self.nbit += 1
            if self.nbit == 8:
                self.regs[self.addr % 0x14] = self.sh
                self.nbit, self.addr = 0, self.addr + 1
        return self.dout

class Card2(H.Card):
    """Rev 0.2 CPLD: same RAM/key logic; RTC mode = SPI port (reads clock, writes set registers)."""
    def __init__(self, rtc, has_rtc=True):
        super().__init__(rtc, has_rtc)
        self.cs = self.oe = self.mosi = 0
        self.contention = 0
    def read(self, a):
        if a < 3 or not self.enabled or not self.present or not self.rtc_mode:
            return super().read(a)
        self.accesses += 1
        dio = 0                                         # board pull-down
        if self.cs:
            dout = self.rtc.clock(self.mosi if self.oe else 0)
            if self.oe and dout is not None:
                self.contention += 1
            dio = self.mosi if self.oe else (dout if dout is not None else 0)
        self.addr = (self.addr + 1) & 0xFFFFF
        return 0xB4 | (self.cs << 1) | dio
    def write(self, a, v):
        if a < 3 or not self.enabled or not self.present or not self.rtc_mode:
            return super().write(a, v)
        self.accesses += 1
        if v & 0x80:
            self.mode_next, self.cs, self.oe = False, 0, 0
        elif v & 0x40:
            self.cs, self.oe = v & 1, (v >> 1) & 1
        else:
            self.mosi = v & 1
        self.rtc.select(bool(self.cs))
        self.matched = 0
        self.rtc_mode = self.mode_next
        self.addr = (self.addr + 1) & 0xFFFFF

class Machine2(H.Machine):
    def __init__(self, rtc_time=(2026, 11, 15, 21, 47, 33), has_rtc=True, seed=1):
        random.seed(seed)
        self.rtc = DS3234(*rtc_time)
        self.card = Card2(self.rtc, has_rtc)
        self.mem = H.Laser128(self.card)
        self.pd = H.ProDOS(self.mem)
        self.mpu = H.MPU(memory=self.mem)
        self.mpu.sp = 0xF0

def build():
    b = os.path.join(HERE, 'build'); os.makedirs(b, exist_ok=True)
    subprocess.check_call(['ca65', '-l', b + '/clkdrv.lst', '-o', b + '/clkdrv.o', HERE + '/clkdrv.s'])
    open(b + '/drv.cfg', 'w').write('MEMORY { M: start = $D742, size = $7D, fill = no; }\nSEGMENTS { DRV: load = M, type = rw; }\n')
    subprocess.check_call(['ld65', '-C', b + '/drv.cfg', '-o', b + '/clkdrv.bin', '-Ln', b + '/clkdrv.lbl', b + '/clkdrv.o'])
    drv = open(b + '/clkdrv.bin', 'rb').read()
    lbl = {l.split()[2].lstrip('.'): int(l.split()[1], 16) for l in open(b + '/clkdrv.lbl')}
    return drv, (lbl['KEYOP_OFS'], lbl['KEYREV_OFS'])

def install(M, drv, ofs, slot=H.STUB):
    """What CLOCK.SYSTEM (rev02) will do: copy into the slot, patch the key pointer, DATETIME = JMP."""
    d = bytearray(drv)
    op, kr = ofs
    keyrev = slot + kr
    d[op], d[op + 1] = keyrev & 0xFF, keyrev >> 8
    M.mem.lc1[slot - 0xD000:slot - 0xD000 + len(d)] = d
    g = M.mem.main
    g[0xBF06], g[0xBF07], g[0xBF08] = 0x4C, slot & 0xFF, slot >> 8
    M.card.enabled = True

def clock_call(M):
    """ProDOS clock call with interrupts ENABLED; returns (cycles, longest interrupts-off run)."""
    mpu, m = M.mpu, M.mem
    m.lc_read, m.lc_write, m.lc_bank1 = True, True, True     # as the MLI leaves the language card
    ret = H.SENTINEL - 1
    mpu.memory[0x100 + mpu.sp] = ret >> 8; mpu.sp = (mpu.sp - 1) & 0xFF
    mpu.memory[0x100 + mpu.sp] = ret & 0xFF; mpu.sp = (mpu.sp - 1) & 0xFF
    mpu.pc = 0xBF06; mpu.p &= ~4
    c0 = mpu.processorCycles; run = mx = 0
    for _ in range(200000):
        if mpu.pc == H.SENTINEL:
            return mpu.processorCycles - c0, mx
        c = mpu.processorCycles; mpu.step(); d = mpu.processorCycles - c
        if mpu.p & 4: run += d; mx = max(mx, run)
        else: run = 0
    raise RuntimeError('runaway at $%04X' % mpu.pc)

def main():
    drv, ofs = build()
    print('driver: %d bytes (ProDOS slot holds 125)' % len(drv))
    H.check(len(drv) <= 125, 'driver fits the ProDOS clock slot')
    cases = [((2026, 11, 15, 21, 47, 33), 0x3ABCD), ((2027, 1, 2, 7, 9, 5), 0xFFFFC), ((2099, 12, 31, 23, 59, 59), 0x123FF),
             ((2030, 8, 1, 0, 0, 0), 0x00000), ((2031, 10, 9, 12, 30, 0), 0x7FF00), ((2040, 9, 30, 13, 1, 2), 0xABCFF)]
    worst = 0
    for t, addr in cases:
        M = Machine2(rtc_time=t, seed=addr)
        install(M, drv, ofs)
        M.card.addr = addr
        ram0 = bytes(M.card.ram)
        main0 = bytes(M.mem.main)
        cyc, irqoff = clock_call(M)
        worst = max(worst, cyc)
        y, mo, d, h, mi, s = t
        got = M.prodos_date()
        H.check(got == (y % 100, mo, d, h, mi), '%04d-%02d-%02d %02d:%02d at slinky $%05X -> %r, %d cycles' % (y, mo, d, h, mi, addr, got, cyc))
        H.check(bytes(M.card.ram) == ram0, '  RAM disk unchanged')
        H.check((M.card.addr >> 8) == (addr >> 8), '  slinky address mid/high kept ($%05X -> $%05X)' % (addr, M.card.addr))
        H.check(not M.card.rtc_mode and not M.card.cs and not M.rtc.selected, '  card back in RAM mode, DS3234 deselected')
        H.check(irqoff == 0, '  interrupts never disabled (longest off-run %d cycles)' % irqoff)
        H.check(M.card.contention == 0, '  no DIO contention')
        allowed = set(range(0x3B, 0x3E)) | set(range(0x200, 0x208)) | set(range(0xBF90, 0xBF94)) | set(range(0x100, 0x200))
        changed = [a for a in range(0x10000) if a not in allowed and M.mem.main[a] != main0[a]]
        H.check(not changed, '  main memory untouched outside $3B-$3D, $200-$207, DATE/TIME, stack (%s)' % [hex(a) for a in changed[:5]])
    # card without the RTC: must not hang or crash; RAM must survive
    M = Machine2(has_rtc=False, seed=9); install(M, drv, ofs); M.card.addr = 0x45678; ram0 = bytes(M.card.ram)
    clock_call(M)
    H.check(bytes(M.card.ram) == ram0 and not M.card.rtc_mode, 'card without RTC: returns, RAM disk unchanged')
    print('worst-case cycles per clock call: %d (~%.1f ms at 1 MHz), interrupts left enabled throughout' % (worst, worst / 1000))
    print('\n%s' % ('ALL PASS' if not H.FAILS else '%d FAILED' % len(H.FAILS)))
    return 1 if H.FAILS else 0

if __name__ == '__main__':
    sys.exit(main())
