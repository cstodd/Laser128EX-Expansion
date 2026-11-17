; CLOCK.SET (rev 0.2): BIN program (BLOAD + CALL 24576 from SET.CLOCK). Sets the DS3234.
; Input at $0300 (binary): year 0-99, month 1-12, day 1-31, hour 0-23, minute, second, weekday 1-7;
;   $0308 = 1 to stop temperature compensation while on battery (BB_TD: saves ~0.8 uA, more drift while off).
;   $0309 MODE: 0 = set the clock (above), 1 = only read registers 00h-12h into $0310-$0322 (no writes).
; Output: $0307 = 0 if the card answered, $FF if the clock was not found.
; Also writes control/status 0Fh = 00h: clears the oscillator-stopped flag, conversion every 64 s, 32 kHz off.
        .setcpu "65C02"
        .include "../rev01/defs.inc"
PARM    = $0300
RESULT  = $0307
BBTD    = $0308
MODE    = $0309
REGS    = $0310                         ; read mode: registers 00h-12h land here
NREAD   = $13
ZTMP    = $3A

        .segment "BIN"
start:  php
        sei
        lda     MODE
        beq     setclk
        jsr     rtc_open                ; read-only mode
        bcc     :+
        lda     #$FF
        bra     done
:       lda     #$00                    ; read from 00h
        jsr     rtc_start
        jsr     rtc_rdmode
        ldx     #0
:       jsr     rtc_rx
        sta     REGS,x
        inx
        cpx     #NREAD
        bne     :-
        jsr     rtc_stop
        jsr     rtc_close
        lda     #0
        bra     done

setclk: ldx     #6                      ; binary -> BCD in register order (sec min hour dow date month year)
:       ldy     order,x
        lda     PARM,y
        cpx     #3                      ; weekday is plain 1-7
        beq     :+
        jsr     bin2bcd
:       sta     regs,x
        dex
        bpl     :--
        jsr     rtc_open
        bcc     :+
        lda     #$FF
        bra     done
:       lda     #$80                    ; write 00h-06h (24-hour mode: hour bit 6 = 0)
        jsr     rtc_start
        ldx     #0
:       lda     regs,x
        jsr     rtc_tx
        inx
        cpx     #7
        bne     :-
        jsr     rtc_stop
        lda     #$8F                    ; 0Fh = 00h
        jsr     rtc_start
        lda     #$00
        jsr     rtc_tx
        jsr     rtc_stop
        lda     #$93                    ; 13h = BB_TD
        jsr     rtc_start
        lda     BBTD
        and     #$01
        jsr     rtc_tx
        jsr     rtc_stop
        jsr     rtc_close
        lda     #0
done:   sta     RESULT
        plp
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

        .include "rtcspi.inc"

order:  .byte   5, 4, 3, 6, 2, 1, 0     ; reg n <- PARM[order[n]]
regs:   .res    7
