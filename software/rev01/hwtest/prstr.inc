prstr:  sta     PTR
        stx     PTR+1
        ldy     #0
:       lda     (PTR),y
        beq     :+
        ora     #$80                    ; Apple text: high bit set
        jsr     COUT
        iny
        bne     :-
:       rts
