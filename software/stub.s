; Laser 128 clock: stub installed in ProDOS's 125-byte clock-driver slot ($D742).
; Runs the driver body from main memory (page mainpg) or, failing that, from auxiliary
; memory (page auxpg), but only if that copy's signature and whole-page checksum are
; intact. Otherwise it returns without touching the date. Never crashes on a stale copy.
        .include "defs.inc"
ZP      = $42                           ; pointer (saved/restored); clear of the body's $3A-$41

        .segment "STUB"
stub:   jmp     start
        .byte   "L1"                    ; stub+3: identifies our stub
mainpg: .byte   0                       ; stub+5: first page of the main-memory copy (0 = none)
auxpg:  .byte   0                       ; stub+6: first page of the aux-memory copy (0 = none)

start:  php
        sei
        lda     ZP
        pha
        lda     ZP+1
        pha
        lda     mainpg
        beq     tryaux
        jsr     check
        bne     tryaux
        jsr     call
        jmp     done
tryaux: lda     auxpg
        beq     done
        sta     RAMRDON                 ; reads of $0200-$BFFF now come from aux memory
        jsr     check
        bne     :+
        jsr     call                    ; body runs from aux; its DATE/TIME writes go to main
:       sta     RAMRDOFF
done:   pla
        sta     ZP+1
        pla
        sta     ZP
        plp
        rts

call:   jmp     (ZP)

; A = first page. Z=1 if it holds an intact body ("CLK1" at +3, all BODY_PAGES pages sum to 0)
check:  sta     ZP+1
        lda     #0
        sta     ZP
        ldy     #BODY_SIG_OFS
:       lda     (ZP),y
        cmp     sigtab-BODY_SIG_OFS,y
        bne     bad
        iny
        cpy     #BODY_SIG_OFS+4
        bne     :-
        ldx     #BODY_PAGES
        ldy     #0
        tya
:       clc
        adc     (ZP),y
        iny
        bne     :-
        inc     ZP+1
        dex
        bne     :-
        dec     ZP+1                    ; back to the first page (BODY_PAGES = 2)
        dec     ZP+1
        cmp     #0
bad:    rts
sigtab: .byte   "CLK1"
