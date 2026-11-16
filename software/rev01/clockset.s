; CLOCK.SET: BIN program (BLOAD + CALL 24576 from SET.CLOCK). Sets the DS3231.
; Input at $0300 (binary): year 0-99, month 1-12, day 1-31, hour 0-23, minute, second, weekday 1-7
; Output: $0307 = 0 if the card answered, $FF if the clock was not found.
        .include "defs.inc"
PARM    = $0300
RESULT  = $0307
ZTMP    = $3A

        .segment "BIN"
start:  php
        sei
        ldx     #6                      ; binary -> BCD in DS3231 register order
:       ldy     order,x
        lda     PARM,y
        cpx     #3                      ; weekday is plain 1-7
        beq     :+
        jsr     bin2bcd
:       sta     regs,x
        dex
        bpl     :--
        bit     XEN
        lda     XAH                     ; save slinky address + the 8 bytes the key overwrites
        pha
        lda     XAM
        pha
        lda     XAL
        pha
        ldx     #0
:       lda     PORT
        sta     saved,x
        inx
        cpx     #8
        bne     :-
        jsr     setaddr
        ldx     #7
:       lda     keyrev,x
        sta     PORT
        dex
        bpl     :-
        lda     PORT
        and     #RTCMASK
        eor     #RTCSIG
        beq     :+
        lda     #$FF
        bne     restore
:       ldx     #s_start-seqs           ; write registers 0-6
        jsr     seq
        lda     #$D0
        jsr     tx
        lda     #$00
        jsr     tx
        ldx     #0
:       lda     regs,x
        stx     xsave
        jsr     tx
        ldx     xsave
        inx
        cpx     #7
        bne     :-
        ldx     #s_stop-seqs
        jsr     seq
        lda     #$80                    ; lock
        sta     PORT
        lda     #0
restore: sta    RESULT
        jsr     setaddr
        ldx     #0
:       lda     saved,x
        sta     PORT
        inx
        cpx     #8
        bne     :-
        pla
        sta     XAL
        pla
        sta     XAM
        pla
        sta     XAH
        plp
        rts

setaddr: tsx                            ; address saved under the return address
        lda     $0103,x
        sta     XAL
        lda     $0104,x
        sta     XAM
        lda     $0105,x
        sta     XAH
        rts

bin2bcd: ldy    #0                      ; A (0-99) -> BCD
:       cmp     #10
        bcc     :+
        sbc     #10
        iny
        bne     :-
:       sta     ZTMP
        tya
        asl     a
        asl     a
        asl     a
        asl     a
        ora     ZTMP
        rts

        .include "i2c.inc"

order:  .byte   5, 4, 3, 6, 2, 1, 0     ; DS3231 reg n <- PARM[order[n]] (sec min hour dow date month year)
keyrev: .byte   $A9,$72,$C4,$3F,$5B,$D1,$27,$8E
regs:   .res    7
saved:  .res    8
xsave:  .byte   0
