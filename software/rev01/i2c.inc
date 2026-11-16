; I2C master primitives over the card's RTC port (shared by the driver body and utilities).
; Port value: bit0 = pull SDA low, bit1 = pull SCL low.  Uses A, Y, ZTMP; X preserved.

; send one bit (C = bit), clock it, leave SCL low
sendbit:
        lda     #0
        rol     a                       ; A = bit
        eor     #3                      ; SCL low, SDA = bit
        sta     PORT
        and     #1                      ; SCL high
        sta     PORT
        ora     #2                      ; SCL low
        sta     PORT
        rts

; send byte A (MSB first), then clock the slave's ACK (ignored)
tx:     sta     ZTMP
        ldy     #8
:       asl     ZTMP
        jsr     sendbit
        dey
        bne     :-
        sec
        jmp     sendbit

; receive a byte into A; C on entry = ACK bit to send afterwards (0 = ACK, 1 = NACK)
rx:     php
        ldy     #8
:       lda     #2                      ; SCL low, SDA released
        sta     PORT
        lda     #0                      ; SCL high
        sta     PORT
        lda     PORT
        lsr     a                       ; C = SDA
        rol     ZTMP
        dey
        bne     :-
        plp
        jsr     sendbit
        lda     ZTMP
        rts

; write the port sequence at seqs+X up to a negative terminator
seq:    lda     seqs,x
        bmi     :+
        sta     PORT
        inx
        bne     seq
:       rts

seqs:
s_start: .byte  2, 0, 1, 3, $FF         ; (repeated) START: SDA falls while SCL high
s_stop:  .byte  3, 1, 0, $FF            ; STOP: SDA rises while SCL high
