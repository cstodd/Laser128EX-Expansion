; CARDTEST (rev 0.2: clock read over SPI, otherwise identical to rev 0.1): machine-language engine for CARD.TEST (BLOAD CARDTEST, CALL 24576).
; Parameter block at $0300:
;   $0300 CMD     1 = quick non-destructive RAM test, 2 = fill (destructive), 3 = verify fill,
;                 4 = read clock registers 0-15 into $0310-$031F,
;                 5 = bank-hop test (non-destructive): every access changes 256K bank, which is
;                     the card's slowest path (A18 / chip select through the CPLD)
;   $0301 RESULT  0 = pass, 1 = errors, $FF = card/clock not responding
;   $0302 ERRADR  first failing address L,M,H
;   $0305 ERREXP  value written, $0306 ERRGOT value read
;   $0307 ERRCNT  error count (16-bit, stops at $FFFF)
;   $0309 NREG    number of 64K regions to test (0 = all 16)
;   $030A FIRST   first 64K region to test (commands 1-3; normally 0). The retention check uses 1:
;                 after test 2 the RAM disk's directory is gone, so the Laser firmware reformats the
;                 start of the RAM disk at the next boot, overwriting the pattern there.
;   $0310 CLOCK   DS3231 registers 0-15
; Address pattern: byte at H:M:L = L + 7*M + 13*H (detects stuck/shorted address lines).
        .setcpu "65C02"
        .include "../rev01/defs.inc"
CMD     = $0300
RESULT  = $0301
ERRADR  = $0302
ERREXP  = $0305
ERRGOT  = $0306
ERRCNT  = $0307
NREG    = $0309
FIRST   = $030A
CLOCK   = $0310
ZTMP    = $3A
SAVE    = $6F00                         ; block save buffer (above this program)

        .segment "BIN"
start:  bit     XEN                     ; enable the expansion RAM
        lda     #0
        sta     RESULT
        sta     ERRCNT
        sta     ERRCNT+1
        lda     XAH                     ; keep the slinky address for whoever had it
        pha
        lda     XAM
        pha
        lda     XAL
        pha
        lda     CMD
        cmp     #4
        bne     :+
        jmp     clock
:       jsr     probe                   ; RAM answers? (write/read two patterns)
        bcc     :+
        jmp     dead
:
        lda     CMD
        cmp     #5
        bne     :+
        jmp     dohop
:       lda     NREG
        and     #$0F
        bne     :+
        lda     #16
:       asl     a                       ; 64K regions -> end value of bh:bm (bh = regions)
        asl     a
        asl     a
        asl     a
        sta     endh
        lda     #0
        sta     bm
        lda     FIRST                   ; start region (0 unless the caller skips some)
        and     #$0F
        sta     bh
blk:    lda     CMD
        cmp     #1
        beq     doquick
        cmp     #2
        beq     dofill
        jsr     check_k                 ; 3 = verify
        jmp     next
dofill: jsr     write_k
        jmp     next
doquick:
        jsr     setblk                  ; save the block
        ldx     #0
:       lda     PORT
        sta     SAVE,x
        inx
        bne     :-
        ldy     #3
:       sty     ysave
        lda     pats,y
        jsr     write_c
        ldy     ysave
        lda     pats,y
        jsr     check_c
        ldy     ysave
        dey
        bpl     :-
        jsr     write_k
        jsr     check_k
        jsr     setblk                  ; restore the block
        ldx     #0
:       lda     SAVE,x
        sta     PORT
        inx
        bne     :-
next:   inc     bm
        bne     :+
        lda     #'.' | $80              ; progress: one dot per 64K
        jsr     COUT
        inc     bh
:       lda     bh
        asl     a
        asl     a
        asl     a
        asl     a
        cmp     endh
        bcc     blk
fin:    lda     ERRCNT
        ora     ERRCNT+1
        beq     out
        lda     #1
        sta     RESULT
        bne     out
dead:   lda     #$FF
        sta     RESULT
out:    pla
        sta     XAL
        pla
        sta     XAM
        pla
        sta     XAH
        rts

clock:  jsr     rtcregs
        jmp     out

; ---- bank-hop test: 1024 offsets x 4 banks. Each location is saved, written and read back
; with two complementary patterns in an order where every access is in a different bank
; from the one before, then restored.
dohop:  lda     #0
        sta     hq
hq_lp:  lda     #0
        sta     hi
hi_lp:  lda     hi
        sta     am
        asl     a
        clc
        adc     hi
        clc
        adc     #1
        sta     al                      ; low byte = 3*i + 1
        ldy     #0                      ; save: read twice, the 2nd read is in the same bank
:       jsr     hset
        lda     PORT
        jsr     hset
        lda     PORT
        sta     hsave,y
        iny
        cpy     #4
        bne     :-
        lda     #0
        jsr     hpass
        lda     #$FF
        jsr     hpass
        ldy     #0                      ; restore
:       jsr     hset
        lda     hsave,y
        sta     PORT
        iny
        cpy     #4
        bne     :-
        inc     hi
        bne     hi_lp
        lda     #'.' | $80
        jsr     COUT
        inc     hq
        lda     hq
        cmp     #4
        bne     hq_lp
        jmp     fin

hpass:  sta     hmask                   ; write 4 banks, then read them in hopping order
        ldy     #0
:       jsr     hset
        jsr     hopval
        sta     PORT
        iny
        cpy     #4
        bne     :-
        ldx     #0
hp_rd:  ldy     horder,x
        stx     xs
        jsr     hset
        jsr     hopval
        sta     expv
        lda     PORT
        cmp     expv
        beq     :+
        pha
        lda     am
        sta     bm
        lda     curh
        sta     bh
        pla
        ldx     al
        jsr     recerr
:       ldx     xs
        inx
        cpx     #8
        bne     hp_rd
        rts

hset:   lda     al                      ; address = bank Y (256K) + hq*64K + am*256 + al
        sta     XAL
        lda     am
        sta     XAM
        tya
        asl     a
        asl     a
        ora     hq
        sta     XAH
        sta     curh
        rts

hopval: lda     al                      ; value differs per bank and per pass
        eor     htab,y
        eor     hmask
        rts

; ---- block helpers (block = bh:bm, 256 bytes)
setblk: lda     #0
        sta     XAL
        lda     bm
        sta     XAM
        lda     bh
        sta     XAH
        rts

write_c: pha                           ; A = constant (setblk clobbers A)
        jsr     setblk
        pla
        ldx     #0
:       sta     PORT
        inx
        bne     :-
        rts

check_c: sta    expv                    ; A = constant
        jsr     setblk
        ldx     #0
:       lda     PORT
        cmp     expv
        beq     :+
        jsr     recerr
:       inx
        bne     :--
        rts

kval:   lda     bm                      ; K = 7*bm + 13*bh (mod 256)
        asl     a
        asl     a
        asl     a
        sec
        sbc     bm
        sta     kk
        lda     bh
        asl     a
        asl     a
        asl     a
        asl     a
        sec
        sbc     bh
        sec
        sbc     bh
        sec
        sbc     bh
        clc
        adc     kk
        sta     kk
        rts

write_k: jsr    kval
        jsr     setblk
        ldx     #0
:       txa
        clc
        adc     kk
        sta     PORT
        inx
        bne     :-
        rts

check_k: jsr    kval
        jsr     setblk
        ldx     #0
:       txa
        clc
        adc     kk
        sta     expv
        lda     PORT
        cmp     expv
        beq     :+
        jsr     recerr
:       inx
        bne     :--
        rts

; A = value read, expv = expected, X = byte in block
recerr: pha
        lda     ERRCNT
        ora     ERRCNT+1
        bne     :+
        stx     ERRADR                  ; first error: where and what
        lda     bm
        sta     ERRADR+1
        lda     bh
        sta     ERRADR+2
        lda     expv
        sta     ERREXP
        pla
        pha
        sta     ERRGOT
:       inc     ERRCNT                  ; count, stopping at $FFFF
        bne     :+
        inc     ERRCNT+1
        bne     :+
        dec     ERRCNT
        dec     ERRCNT+1
:       pla
        rts

; is there RAM? write $5A/$A5 at block 0 and read back (restoring the 2 bytes). C=1 if not.
; Only "both read-backs equal" counts as absent (no card reads $FF/$FF); bit faults are left
; for the real tests to report.
probe:  lda     #0
        sta     bm
        sta     bh
        jsr     setblk
        lda     PORT
        sta     SAVE
        lda     PORT
        sta     SAVE+1
        jsr     setblk
        lda     #$5A
        sta     PORT
        lda     #$A5
        sta     PORT
        jsr     setblk
        lda     PORT
        sta     ysave
        lda     PORT
        eor     ysave                   ; 0 if both read the same -> nothing there
        pha
        jsr     setblk
        lda     SAVE
        sta     PORT
        lda     SAVE+1
        sta     PORT
        pla
        beq     :+                      ; equal read-backs: nothing there
        clc
        rts
:       sec
        rts

; ---- clock: unlock (saving the 8 RAM bytes), read registers 0-15, lock, restore
rtcregs:                                ; DS3234 registers 00h-0Fh -> CLOCK (rev 0.2, SPI)
        php
        sei
        jsr     rtc_open
        bcc     :+
        lda     #$FF
        sta     RESULT
        plp
        rts
:       lda     #$00                    ; read from 00h
        jsr     rtc_start
        jsr     rtc_rdmode
        ldx     #0
:       jsr     rtc_rx
        sta     CLOCK,x
        inx
        cpx     #16
        bne     :-
        jsr     rtc_stop
        jsr     rtc_close
        plp
        rts

        .include "rtcspi.inc"

pats:   .byte   $00, $FF, $55, $AA
htab:   .byte   $00, $FF, $5A, $A5
horder: .byte   0, 1, 2, 3, 0, 2, 1, 3   ; covers A18-only, chip-only and both changing
hsave:  .res    4
hq:     .byte   0
hi:     .byte   0
al:     .byte   0
am:     .byte   0
curh:   .byte   0
hmask:  .byte   0
xs:     .byte   0
bm:     .byte   0
bh:     .byte   0
endh:   .byte   0
kk:     .byte   0
expv:   .byte   0
ysave:  .byte   0
        .assert * < SAVE, error, "CARDTEST overlaps its save buffer"
