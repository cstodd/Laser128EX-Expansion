; Rev 0.2 RTC access for the utilities (CLOCK.SYSTEM probe, CLOCK.SET, CARDTEST): DS3234 over the rev02 CPLD
; SPI port. Not size-limited, so these save/restore the whole slinky address. Call with interrupts off.
; RTC-mode port: write D7=1 lock; write D6=1 control (D0 = CS, D1 = drive DIO); other writes = next data bit;
; every read = one SPI clock, D0 = DOUT. Deselected read = signature %101101, CS=0, DIO=0 (board pull-down).
CTL_OUT  = %01000011    ; CS on, drive DIO (address / write data)
CTL_IN   = %01000001    ; CS on, DIO released (read data)
CTL_OFF  = %01000000    ; CS off
RTC_LOCK = $80
RTC_SIG  = %10110100

; rtc_open: unlock. C = 0: in RTC mode. C = 1: no rev 0.2 RTC answered (everything already put back).
; Only RAM-disk byte $xxxx00 of the current page is touched (saved here, restored by rtc_close).
rtc_open:
        bit     XEN
        lda     XAL
        sta     rs_al
        lda     XAM
        sta     rs_am
        lda     XAH
        sta     rs_ah
        stz     XAL
        lda     PORT
        sta     rs_byte
        ldy     #7
:       stz     XAL
        lda     rs_key,y
        sta     PORT
        dey
        bpl     :-
        lda     PORT                    ; signature twice (RAM would need two equal bytes to fool it)
        cmp     #RTC_SIG
        bne     :+
        lda     PORT
        cmp     #RTC_SIG
        bne     :+
        clc
        rts
:       jsr     rtc_close
        sec
        rts

; rtc_close: lock (aimed at byte 00, so on a card that never unlocked it lands on the saved byte),
; restore the saved byte and the slinky address.
rtc_close:
        stz     XAL
        lda     #RTC_LOCK
        sta     PORT
        stz     XAL
        lda     rs_byte
        sta     PORT
        lda     rs_al
        sta     XAL
        lda     rs_am
        sta     XAM
        lda     rs_ah
        sta     XAH
        rts

; rtc_start: A = address byte (bit 7 = 0 read, 1 write). Selects the DS3234 and sends it.
; For a read, follow with rtc_rdmode before rtc_rx.
rtc_start:
        pha
        lda     #CTL_OUT
        sta     PORT
        pla
; rtc_tx: send A, MSB first (write the bit, then a read clocks it). Uses Y.
rtc_tx: sta     rs_t
        ldy     #8
:       asl     rs_t
        lda     #0
        rol     a
        sta     PORT
        lda     PORT
        dey
        bne     :-
        rts
rtc_rdmode:
        lda     #CTL_IN
        sta     PORT
        rts
; rtc_rx: read one byte into A, MSB first. Uses Y.
rtc_rx: ldy     #8
:       lda     PORT
        lsr     a
        rol     rs_t
        dey
        bne     :-
        lda     rs_t
        rts
rtc_stop:
        lda     #CTL_OFF
        sta     PORT
        rts

rs_key: .byte   $A9,$72,$C4,$3F,$5B,$D1,$27,$8E   ; key 8E 27 D1 5B 3F C4 72 A9, reversed
rs_al:  .byte   0
rs_am:  .byte   0
rs_ah:  .byte   0
rs_byte: .byte  0
rs_t:   .byte   0
