#!/usr/bin/env python3
"""65C02 test harness for the Laser 128 clock software (py65).

Models: Laser 128 main/aux memory (RAMRD/RAMWRT), the language card, the expansion-RAM
"slinky" registers with auto-increment over 1 MB, the card's CPLD (unlock key, RTC port -
mirrors cpld/laser128_ramcard.v), a bit-level DS3231 I2C slave, and enough of ProDOS 8
(global page, MLI OPEN/READ/CLOSE/QUIT, BASIC.SYSTEM GETBUFR, COUT) to run the real binaries.

    python3 software/build.py && python3 software/test/harness.py
"""
import os
import random
import sys

from py65.devices.mpu65c02 import MPU

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, '..', 'build')
KEY = [0x8E, 0x27, 0xD1, 0x5B, 0x3F, 0xC4, 0x72, 0xA9]
STUB = 0xD742
SENTINEL = 0xFFF0


def bcd(v):
    return ((v // 10) << 4) | (v % 10)


class DS3231:
    """Bit-level I2C slave at address 0x68 with the timekeeping registers."""

    def __init__(self, y, mo, d, h, mi, s, dow=1):
        self.regs = [0] * 0x13
        self.regs[0:7] = [bcd(s), bcd(mi), bcd(h), dow, bcd(d), bcd(mo), bcd(y % 100)]
        self.ptr = 0
        self.mode = 'IDLE'
        self.sda_low = False
        self.scl = self.sda = 1
        self.byte = self.bitn = 0
        self.target = 'ADDR'
        self.rw = 0
        self.mack = False
        self.starts = 0

    def bus(self, scl, sda):
        pscl, psda = self.scl, self.sda
        self.scl, self.sda = scl, sda
        if pscl and scl and psda != sda:            # START / STOP
            if not sda:
                self.mode, self.target, self.byte, self.bitn, self.sda_low = 'RX', 'ADDR', 0, 0, False
                self.starts += 1
            else:
                self.mode, self.sda_low = 'IDLE', False
            return
        if not pscl and scl:                         # rising edge: sample
            if self.mode == 'RX':
                self.byte = ((self.byte << 1) | sda) & 0xFF
                self.bitn += 1
            elif self.mode == 'TXACK':
                self.mack = (sda == 0)
        elif pscl and not scl:                       # falling edge: drive
            if self.mode == 'RX' and self.bitn == 8:
                b = self.byte
                if self.target == 'ADDR':
                    if b >> 1 != 0x68:
                        self.mode = 'IDLE'
                        return
                    self.rw = b & 1
                    self.target = 'REG'
                elif self.target == 'REG':
                    self.ptr = b % 0x13
                    self.target = 'DATA'
                else:
                    self.regs[self.ptr] = b
                    self.ptr = (self.ptr + 1) % 0x13
                self.sda_low = True
                self.mode = 'RXACK'
            elif self.mode == 'RXACK':
                self.sda_low = False
                if self.rw:
                    self._load()
                else:
                    self.mode, self.bitn, self.byte = 'RX', 0, 0
            elif self.mode == 'TX':
                self.bitn += 1
                if self.bitn < 8:
                    self.sda_low = not (self.byte >> (7 - self.bitn)) & 1
                else:
                    self.sda_low = False
                    self.mode = 'TXACK'
            elif self.mode == 'TXACK':
                if self.mack:
                    self._load()
                else:
                    self.mode = 'IDLE'

    def _load(self):
        self.byte = self.regs[self.ptr]
        self.ptr = (self.ptr + 1) % 0x13
        self.bitn = 0
        self.mode = 'TX'
        self.sda_low = not (self.byte >> 7) & 1


class Card:
    """Slinky registers (motherboard) + our card's CPLD + SRAM + DS3231."""

    def __init__(self, rtc, has_rtc=True):
        self.ram = bytearray(random.getrandbits(8) for _ in range(1 << 20))
        self.addr = 0
        self.enabled = False
        self.rtc = rtc
        self.has_rtc = has_rtc
        self.matched = 0
        self.rtc_mode = False
        self.mode_next = False
        self.sda_low = self.scl_low = False
        self.accesses = 0

    def lines(self):
        scl = 0 if self.scl_low else 1
        sda = 0 if (self.sda_low or self.rtc.sda_low) else 1
        return scl, sda

    def _bus(self):
        self.rtc.bus(*self.lines())

    def read(self, a):
        if a == 0: return self.addr & 0xFF
        if a == 1: return (self.addr >> 8) & 0xFF
        if a == 2: return 0xF0 | (self.addr >> 16)
        if not self.enabled:
            return 0xFF
        self.accesses += 1
        if self.rtc_mode:
            scl, sda = self.lines()
            v = 0xB4 | (scl << 1) | sda
        else:
            v = self.ram[self.addr]
        self.addr = (self.addr + 1) & 0xFFFFF
        return v

    def write(self, a, v):
        if a == 0: self.addr = (self.addr & 0xFFF00) | v; return
        if a == 1: self.addr = (self.addr & 0xF00FF) | (v << 8); return
        if a == 2: self.addr = (self.addr & 0x0FFFF) | ((v & 15) << 16); return
        if not self.enabled:
            return
        self.accesses += 1
        if self.rtc_mode:                           # RTC port; RAM never written
            if v & 0x80:
                self.mode_next = False
                self.sda_low = self.scl_low = False
            else:
                self.sda_low, self.scl_low = bool(v & 1), bool(v & 2)
            self.matched = 0
            self._bus()
        else:
            self.ram[self.addr] = v                 # the write completes as a RAM write
            if self.has_rtc:
                if v == KEY[self.matched]:
                    if self.matched == 7:
                        self.mode_next = True
                    self.matched = (self.matched + 1) & 7
                else:
                    self.matched = 1 if v == KEY[0] else 0
        self.rtc_mode = self.mode_next              # mode changes take effect at end of cycle
        self.addr = (self.addr + 1) & 0xFFFFF


class Laser128:
    def __init__(self, card):
        self.main = bytearray(65536)
        self.aux = bytearray(65536)
        self.lc1 = bytearray(4096)                  # $D000 bank 1
        self.lc2 = bytearray(4096)                  # $D000 bank 2
        self.lchi = bytearray(8192)                 # $E000-$FFFF
        self.rom = bytearray([0x60] * 0x3000)       # $D000-$FFFF ROM (RTS everywhere)
        self.ramrd = self.ramwrt = False
        self.lc_read, self.lc_write, self.lc_bank1, self.lc_pre = False, False, True, 0
        self.card = card

    def __len__(self):
        return 65536

    def _lc(self, a, op, rw):
        bit3, low = (a >> 3) & 1, a & 3
        self.lc_bank1 = bool(bit3)
        self.lc_read = low in (0, 3)
        if low in (1, 3):
            if op == 'r':
                self.lc_pre += 1
                if self.lc_pre >= 2:
                    self.lc_write = True
            else:
                self.lc_pre = 0
        else:
            self.lc_write = False
            self.lc_pre = 0

    def _io(self, a, op, v=0):
        if a in (0xC002, 0xC003) and op == 'w': self.ramrd = a == 0xC003
        elif a in (0xC004, 0xC005) and op == 'w': self.ramwrt = a == 0xC005
        elif 0xC080 <= a <= 0xC08F: self._lc(a, op, v)
        elif 0xC0D0 <= a <= 0xC0D3:
            return self.card.read(a - 0xC0D0) if op == 'r' else self.card.write(a - 0xC0D0, v)
        elif 0xC500 <= a <= 0xC5FF: self.card.enabled = True
        if op != 'r' and not (0xC0D0 <= a <= 0xC0D3) and a >= 0xC080:
            self.lc_pre = 0 if not (0xC080 <= a <= 0xC08F) else self.lc_pre
        return 0

    def __getitem__(self, a):
        if a < 0x200: return self.main[a]
        if a < 0xC000: return (self.aux if self.ramrd else self.main)[a]
        if a < 0xD000: return self._io(a, 'r') or 0
        if not self.lc_read: return self.rom[a - 0xD000]
        if a < 0xE000: return (self.lc1 if self.lc_bank1 else self.lc2)[a - 0xD000]
        return self.lchi[a - 0xE000]

    def __setitem__(self, a, v):
        if a < 0x200: self.main[a] = v; return
        if a < 0xC000: (self.aux if self.ramwrt else self.main)[a] = v; return
        if a < 0xD000: self._io(a, 'w', v); return
        if not self.lc_write: return
        if a < 0xE000: (self.lc1 if self.lc_bank1 else self.lc2)[a - 0xD000] = v
        else: self.lchi[a - 0xE000] = v


class ProDOS:
    """Global page + traps for MLI, COUT, GETBUFR."""

    def __init__(self, m):
        self.m = m
        self.out = ''
        self.files = {'BASIC.SYSTEM': bytes([0xEA] * 300)}
        self.quit = False
        self.loaded = None
        g = m.main
        g[0xBF00] = 0x4C                             # MLI entry (trapped)
        g[0xBF06] = 0x60                             # DATETIME: no clock yet
        g[0xBF07], g[0xBF08] = STUB & 0xFF, STUB >> 8
        g[0xBF10], g[0xBF11] = 0x47, 0xD0            # NODEV
        g[0xBF26], g[0xBF27] = 0x00, 0xD2            # /RAM driver (slot 3 drive 2)
        g[0xBF31] = 2                                # DEVCNT (count - 1)
        g[0xBF32:0xBF35] = bytes([0x60, 0xBF, 0x50])
        g[0xBF98] = 0xB2                             # MACHID: IIe/IIc class, 128K, 80-col
        m.lc_read, m.lc_bank1 = False, True          # SYS programs run with ROM in

    def trap(self, mpu):
        pc = mpu.pc
        if pc == 0xFDED:
            self.out += chr(mpu.a & 0x7F)
            return self._rts(mpu)
        if pc == 0xBEF5:                             # GETBUFR: 2 pages at $9400
            mpu.a = 0x94
            mpu.p &= ~1
            return self._rts(mpu)
        if pc == 0xBF00:
            return self._mli(mpu)
        return False

    def _rts(self, mpu):
        lo = mpu.memory[0x100 + ((mpu.sp + 1) & 0xFF)]
        hi = mpu.memory[0x100 + ((mpu.sp + 2) & 0xFF)]
        mpu.sp = (mpu.sp + 2) & 0xFF
        mpu.pc = ((hi << 8) | lo) + 1
        return True

    def _mli(self, mpu):
        m = self.m.main
        lo = m[0x100 + ((mpu.sp + 1) & 0xFF)]
        hi = m[0x100 + ((mpu.sp + 2) & 0xFF)]
        ret = (hi << 8) | lo
        cmd = m[ret + 1]
        p = m[ret + 2] | (m[ret + 3] << 8)
        err = 0
        if cmd == 0xC8:                              # OPEN
            nptr = m[p + 1] | (m[p + 2] << 8)
            name = bytes(m[nptr + 1:nptr + 1 + m[nptr]]).decode()
            if name in self.files:
                self.openf = self.files[name]
                m[p + 5] = 1
            else:
                err = 0x46
        elif cmd == 0xCA:                            # READ
            buf = m[p + 2] | (m[p + 3] << 8)
            data = self.openf
            m[buf:buf + len(data)] = data
            m[p + 6], m[p + 7] = len(data) & 0xFF, len(data) >> 8
            self.loaded = buf
        elif cmd == 0xCC:                            # CLOSE
            pass
        elif cmd == 0x65:                            # QUIT
            self.quit = True
        mpu.sp = (mpu.sp + 2) & 0xFF
        mpu.pc = ret + 4
        mpu.a = err
        mpu.p = (mpu.p | 1) if err else (mpu.p & ~1)
        mpu.p = (mpu.p | 2) if not err else (mpu.p & ~2)
        return True


class Machine:
    def __init__(self, rtc_time=(2026, 11, 15, 21, 47, 33), has_rtc=True, seed=1):
        random.seed(seed)
        self.rtc = DS3231(*rtc_time)
        self.card = Card(self.rtc, has_rtc)
        self.mem = Laser128(self.card)
        self.pd = ProDOS(self.mem)
        self.mpu = MPU(memory=self.mem)
        self.mpu.sp = 0xF0

    def load(self, path, addr):
        data = open(path, 'rb').read()
        self.mem.main[addr:addr + len(data)] = data
        return len(data)

    def call(self, addr, limit=2_000_000, stop_pc=None):
        mpu = self.mpu
        ret = SENTINEL - 1
        mpu.memory[0x100 + mpu.sp] = ret >> 8; mpu.sp = (mpu.sp - 1) & 0xFF
        mpu.memory[0x100 + mpu.sp] = ret & 0xFF; mpu.sp = (mpu.sp - 1) & 0xFF
        mpu.pc = addr
        for n in range(limit):
            if mpu.pc == SENTINEL:
                return n
            if stop_pc is not None and mpu.pc == stop_pc and n > 0:
                return n
            if self.pd.quit:
                return n
            if self.pd.trap(mpu):
                continue
            if mpu.memory[mpu.pc] == 0x00 and n > 0:
                raise RuntimeError('BRK at $%04X' % mpu.pc)
            mpu.step()
        raise RuntimeError('step limit at $%04X' % mpu.pc)

    def prodos_clock_call(self):
        """Call DATETIME the way the MLI does: language card bank 1 RAM read-enabled."""
        m = self.mem
        saved = (m.lc_read, m.lc_write, m.lc_bank1)
        m.lc_read, m.lc_write, m.lc_bank1 = True, False, True
        self.call(0xBF06)
        m.lc_read, m.lc_write, m.lc_bank1 = saved

    def prodos_date(self):
        g = self.mem.main
        lo, hi, mi, h = g[0xBF90], g[0xBF91], g[0xBF92], g[0xBF93]
        return (hi >> 1, ((hi & 1) << 3) | (lo >> 5), lo & 31, h, mi)


# ------------------------------------------------------------------ tests
FAILS = []


def check(cond, what):
    print(('  ok   ' if cond else '  FAIL ') + what)
    if not cond:
        FAILS.append(what)


def snapshot(c):
    return bytes(c.ram), c.addr


def main():
    sysf = os.path.join(BUILD, 'CLOCK.SYSTEM')
    mainf = os.path.join(BUILD, 'CLOCK.MAIN')
    stub = open(os.path.join(BUILD, 'stub.bin'), 'rb').read()

    print('1. CLOCK.SYSTEM on a card with the RTC')
    M = Machine()
    M.card.addr = 0x3ABCD
    ram0, addr0 = snapshot(M.card)
    M.load(sysf, 0x2000)
    M.call(0x2000, stop_pc=0x2000)
    check('LASER 128 CLOCK INSTALLED' in M.pd.out, 'message: %r' % M.pd.out.strip())
    check(M.pd.loaded == 0x2000 and M.mpu.pc == 0x2000, 'chained to BASIC.SYSTEM')
    check(M.mem.main[0xBF06] == 0x4C, 'DATETIME = JMP')
    check(M.mem.main[0xBF98] & 1 == 1, 'MACHID clock bit set')
    check(bytes(M.mem.lc1[0x742:0x742 + 5]) == stub[:5] and M.mem.lc1[0x748] == 0x0C and M.mem.lc1[0x747] == 0,
          'stub in LC bank 1 at $D742, auxpg=$0C, mainpg=0')
    check(M.mem.main[0xBF31] == 1 and 0xBF not in M.mem.main[0xBF32:0xBF34], '/RAM removed from DEVLST')
    check(M.mem.main[0xBF26:0xBF28] == M.mem.main[0xBF10:0xBF12], '/RAM vector = NODEV')
    check(bytes(M.mem.aux[0x0C00:0x0C07])[3:7] == b'CLK1' and sum(M.mem.aux[0x0C00:0x0E00]) % 256 == 0,
          'aux copy at $0C00: signature and checksum')
    check(snapshot(M.card) == (ram0, addr0), 'RAM disk contents and slinky address unchanged by detection')
    check(not M.card.rtc_mode, 'card left in RAM mode')

    print('2. ProDOS clock call (aux copy)')
    M.mem.main[0xBF90:0xBF94] = bytes(4)
    M.card.addr = 0xFFFFC                                    # wraps past the end of 1 MB
    ram0, addr0 = snapshot(M.card)
    M.prodos_clock_call()
    check(M.prodos_date() == (26, 11, 15, 21, 47), 'date/time %r' % (M.prodos_date(),))
    check(snapshot(M.card) == (ram0, addr0), 'RAM disk + address intact (across 1 MB wrap)')
    check(not M.mem.ramrd and not M.mem.ramwrt, 'RAMRD/RAMWRT off afterwards')
    check(not M.card.rtc_mode and M.rtc.mode == 'IDLE', 'card locked, I2C bus idle')

    print('3. CLOCK.MAIN under BASIC.SYSTEM')
    M.mem.lc_read = False
    M.load(mainf, 0x6000)
    M.pd.out = ''
    M.call(0x6000)
    check('MAIN COPY INSTALLED' in M.pd.out, 'message: %r' % M.pd.out.strip())
    check(M.mem.lc1[0x747] == 0x94, 'stub mainpg = $94 (GETBUFR page)')
    check(bytes(M.mem.main[0x9403:0x9407]) == b'CLK1' and sum(M.mem.main[0x9400:0x9600]) % 256 == 0,
          'main copy at $9400: signature and checksum')

    print('4. clock call uses the main copy (aux copy destroyed)')
    M.mem.aux[0x0C00:0x0E00] = bytes(512)
    M.rtc.regs[0:7] = [bcd(5), bcd(9), bcd(7), 3, bcd(2), bcd(1), bcd(27)]   # 2027-01-02 07:09
    ram0, addr0 = snapshot(M.card)
    M.prodos_clock_call()
    check(M.prodos_date() == (27, 1, 2, 7, 9), 'date/time %r' % (M.prodos_date(),))
    check(snapshot(M.card) == (ram0, addr0), 'RAM disk + address intact')

    print('5. main copy partly overwritten -> falls back to aux copy')
    M2 = Machine(rtc_time=(2026, 12, 31, 23, 59, 59), seed=2)
    M2.load(sysf, 0x2000); M2.call(0x2000, stop_pc=0x2000)
    M2.mem.lc_read = False
    M2.load(mainf, 0x6000); M2.call(0x6000)
    M2.mem.main[0x9480] ^= 0x55                               # signature intact, code damaged
    M2.mem.main[0xBF90:0xBF94] = bytes(4)
    M2.prodos_clock_call()
    check(M2.prodos_date() == (26, 12, 31, 23, 59), 'date/time %r via aux' % (M2.prodos_date(),))

    print('6. both copies gone -> no update, no crash')
    M2.mem.aux[0x0C10] ^= 0xFF
    M2.mem.main[0xBF90:0xBF94] = bytes([1, 2, 3, 4])
    ram0, addr0 = snapshot(M2.card)
    acc0 = M2.card.accesses
    M2.prodos_clock_call()
    check(bytes(M2.mem.main[0xBF90:0xBF94]) == bytes([1, 2, 3, 4]), 'date untouched')
    check(snapshot(M2.card) == (ram0, addr0) and M2.card.accesses == acc0, 'card not accessed at all')
    check(not M2.mem.ramrd, 'RAMRD off')

    print('7. CLOCK.SYSTEM on a card without the RTC (e.g. stock DRAM card)')
    M3 = Machine(has_rtc=False, seed=3)
    M3.card.addr = 0x01234
    ram0, addr0 = snapshot(M3.card)
    M3.load(sysf, 0x2000)
    M3.call(0x2000, stop_pc=0x2000)
    check('NOT FOUND' in M3.pd.out, 'message: %r' % M3.pd.out.strip())
    check(M3.mem.main[0xBF06] == 0x60 and M3.mem.main[0xBF98] & 1 == 0, 'nothing installed')
    check(M3.mem.main[0xBF31] == 2, '/RAM left connected')
    check(snapshot(M3.card) == (ram0, addr0), 'RAM disk contents and address unchanged')
    check(M3.pd.loaded == 0x2000, 'still chains to BASIC.SYSTEM')

    print('8. CLOCK.SET writes the DS3231; the driver reads it back')
    M.mem.lc_read = False
    M.load(os.path.join(BUILD, 'CLOCK.SET'), 0x6000)
    M.mem.main[0x0300:0x0307] = bytes([28, 2, 29, 13, 5, 42, 3])     # 2028-02-29 13:05:42, Tue
    M.card.addr = 0x7FFF9
    ram0, addr0 = snapshot(M.card)
    M.call(0x6000)
    check(M.mem.main[0x0307] == 0, 'CLOCK.SET result 0')
    check(M.rtc.regs[0:7] == [0x42, 0x05, 0x13, 3, 0x29, 0x02, 0x28], 'DS3231 registers %s' % [hex(x) for x in M.rtc.regs[0:7]])
    check(snapshot(M.card) == (ram0, addr0) and not M.card.rtc_mode, 'RAM disk + address intact, locked')
    M.prodos_clock_call()
    check(M.prodos_date() == (28, 2, 29, 13, 5), 'driver reads back %r' % (M.prodos_date(),))
    M3.load(os.path.join(BUILD, 'CLOCK.SET'), 0x6000)
    M3.mem.main[0x0300:0x0307] = bytes([28, 2, 29, 13, 5, 42, 3])
    ram0, addr0 = snapshot(M3.card)
    M3.call(0x6000)
    check(M3.mem.main[0x0307] == 0xFF and snapshot(M3.card) == (ram0, addr0), 'no-RTC card: result $FF, RAM intact')

    print('\n%s' % ('ALL PASS' if not FAILS else '%d FAILED' % len(FAILS)))
    return 1 if FAILS else 0


if __name__ == '__main__':
    sys.exit(main())
