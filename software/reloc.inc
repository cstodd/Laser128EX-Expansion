; Relocate the driver body image (assembled for page $10) into pages X.., linked for page A,
; then make all BODY_PAGES*256 bytes sum to 0 (last byte adjusts). Uses ZP $06-$09.
; reltab: RELCNT entries of (offset low, offset high) for high bytes to relocate.
RL_SRC  = $06
RL_DST  = $08

reloc:  sta     rl_pg
        stx     RL_DST+1
        stx     rl_dpg
        lda     #0
        sta     RL_DST
        lda     #<bodyimg
        sta     RL_SRC
        lda     #>bodyimg
        sta     RL_SRC+1
        lda     #<BODYLEN               ; bytes left to copy (16-bit)
        sta     rl_cnt
        lda     #>BODYLEN
        sta     rl_cnt+1
        ldx     #BODY_PAGES
        ldy     #0
rl_cp:  lda     rl_cnt                  ; copy, padding with 0 after the image
        ora     rl_cnt+1
        beq     :+
        lda     rl_cnt
        bne     rl_dec
        dec     rl_cnt+1
rl_dec: dec     rl_cnt
        lda     (RL_SRC),y
:       sta     (RL_DST),y
        iny
        bne     rl_cp
        inc     RL_SRC+1
        inc     RL_DST+1
        dex
        bne     rl_cp
        ldx     #0                      ; relocations
rl_rel: cpx     #RELCNT*2
        beq     rl_sum
        lda     rl_dpg
        clc
        adc     reltab+1,x
        sta     RL_DST+1
        ldy     reltab,x
        lda     (RL_DST),y
        sec
        sbc     #$10
        clc
        adc     rl_pg
        sta     (RL_DST),y
        inx
        inx
        bne     rl_rel
rl_sum: lda     rl_dpg                  ; checksum over all pages
        sta     RL_DST+1
        ldx     #BODY_PAGES
        ldy     #0
        tya
:       clc
        adc     (RL_DST),y
        iny
        bne     :-
        inc     RL_DST+1
        dex
        bne     :-
        dec     RL_DST+1                ; last byte of the last page
        dey
        sec                             ; it was included in the sum: new = old - sum
        eor     #$FF
        adc     (RL_DST),y
        sta     (RL_DST),y
        rts
rl_pg:  .byte   0
rl_dpg: .byte   0
rl_cnt: .word   0

bodyimg: .incbin "build/body10.bin"
reltab:  .incbin "build/reltab.bin"
        .include "build/body.inc"          ; BODYLEN, RELCNT
