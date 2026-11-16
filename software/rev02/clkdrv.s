; Laser 128 RAM + clock card, rev 0.2 (DS3234 on SPI): ProDOS clock driver.
; The whole driver lives in ProDOS's 125-byte clock slot (DATETIME+1). No aux memory, no /RAM removal.
;
; RTC port (CPLD rev02, RTC mode): write D7=1 lock; write D6=1 control (D0 = chip select, D1 = drive DIO);
; other writes set the next data bit; every READ is one SPI clock and returns DOUT in D0.
; With DIO not driven, the board's pull-down makes DIN = 0, so the 8 address bits for a read of register
; 00h need no writes: one loop of 64 reads = address byte (discarded) + registers 00h-06h.
;
; Scratch: $3B-$3D (ProDOS's own clock driver uses $3A-$3E) and $200-$207 (TN #1: clock drivers may use
; the start of the GETLN buffer). Leaves the slinky address's mid/high bytes alone; sets the low byte to 0
; (the RAM-disk firmware sets the address before each transfer). The one RAM-disk byte the key lands on is
; saved and restored.
;
; Interrupts are never disabled (no interrupts-off window at all, unlike most clock drivers). This relies on
; no interrupt handler using the expansion RAM while the driver runs: such a handler would disturb the
; unlock sequence or clock the RTC port. Serial, mouse and timer handlers don't. (Keeping php/sei/plp would
; push the driver past 125 bytes.)
        .setcpu "65C02"
        .include "../defs.inc"

RAMSAVE = $3B
ACC     = $3C
TENS    = $3D
BUF     = $0200         ; BUF+7 = first byte read (address phase, discarded), BUF+6 = seconds ...
                        ; BUF+5 min, +4 hour, +3 day of week, +2 date, +1 month, +0 year (binary)
CTL_SEL = %01000001     ; control: chip select on, DIO not driven

        .segment "DRV"
drv:    bit     XEN                     ; expansion RAM interface on
        stz     XAL                     ; byte $xxxx00 of the current page
        lda     PORT
        sta     RAMSAVE
        ldy     #8                      ; 8 key bytes, then the chip-select control write
keylp:   stz     XAL                     ; every key byte lands on that same byte
keyop:  lda     keyrev,y                ; (operand patched by the installer)
        sta     PORT
        dey
        bpl     keylp
        ldx     #7
bytelp:  ldy     #8
bitlp:   lda     PORT                    ; one SPI clock, D0 = DOUT
        lsr     a
        rol     ACC
        dey
        bne     bitlp
        lda     ACC                     ; BCD -> binary: tens*10 + units
        and     #$F0
        lsr     a
        sta     TENS                    ; tens*8
        lsr     a
        lsr     a                       ; tens*2 (C = 0)
        adc     TENS
        sta     TENS
        lda     ACC
        and     #$0F
        adc     TENS
        sta     BUF,x
        dex
        bpl     bytelp
        stz     XAL                     ; lock (also deselects), aimed at the saved byte so that
        lda     #$80                    ; on a card without the RTC (never in RTC mode) every write
        sta     PORT                    ; lands on the one byte restored next
        stz     XAL                     ; put the RAM-disk byte back
        lda     RAMSAVE
        sta     PORT
        lda     BUF+5                   ; ProDOS TIME = minute, hour
        sta     TIME
        lda     BUF+4
        sta     TIME+1
        lda     BUF+1                   ; month (C <- bit 3 after five shifts)
        asl     a
        asl     a
        asl     a
        asl     a
        asl     a
        ora     BUF+2                   ; | date
        sta     DATE
        lda     BUF+0                   ; year << 1 | month bit 3
        rol     a
        sta     DATE+1
        rts
keyrev: .byte   CTL_SEL                 ; written last: chip select on, DIO not driven
        .byte   $A9,$72,$C4,$3F,$5B,$D1,$27,$8E   ; key 8E 27 D1 5B 3F C4 72 A9, reversed
drv_end:
        .assert drv_end - drv <= 125, error, "driver must fit ProDOS's 125-byte clock slot"
KEYOP_OFS = keyop - drv + 1             ; installer patches this word to (slot + keyrev - drv)
KEYREV_OFS = keyrev - drv
        .export KEYOP_OFS, KEYREV_OFS
