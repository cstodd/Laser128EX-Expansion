; CLOCK.MAIN: BIN program, BRUN it from STARTUP (BASIC.SYSTEM). Reserves two pages with
; BASIC.SYSTEM's GETBUFR, puts a second copy of the clock driver body there and tells the
; stub about it. The stub prefers this copy; the aux copy remains the fallback.
        .include "defs.inc"
        .segment "BIN"
start:  lda     DATETIME
        cmp     #$4C
        bne     notinst
        lda     DATETIME+1
        sta     $06
        lda     DATETIME+2
        sta     $07
        lda     $C088                   ; read the language card (bank 1) to see the stub
        ldy     #3
        lda     ($06),y
        cmp     #'L'
        bne     notinst
        iny
        lda     ($06),y
        cmp     #'1'
        bne     notinst
        lda     $C082                   ; ROM back in for BASIC.SYSTEM
        lda     #BODY_PAGES
        jsr     GETBUFR
        bcs     nomem
        sta     mpage
        tax
        jsr     reloc                   ; body linked for and placed in that page
        lda     DATETIME+1
        sta     $06
        lda     DATETIME+2
        sta     $07
        lda     $C08B                   ; language card bank 1, write-enabled
        lda     $C08B
        ldy     #5
        lda     mpage
        sta     ($06),y                 ; stub mainpg
        lda     $C082
        ldx     #m_ok-msgs
        bpl     print
notinst: lda    $C082
        ldx     #m_ni-msgs
        bpl     print
nomem:  ldx     #m_nm-msgs
print:  lda     msgs,x
        beq     :+
        jsr     COUT
        inx
        bpl     print
:       rts
mpage:  .byte   0

        .include "reloc.inc"

        .macro  hstr s
        .repeat .strlen(s), i
        .byte   .strat(s, i) | $80
        .endrep
        .endmacro
msgs:
m_ok:   hstr    "CLOCK: MAIN COPY INSTALLED"
        .byte   $8D, 0
m_ni:   hstr    "CLOCK: RUN CLOCK.SYSTEM FIRST"
        .byte   $8D, 0
m_nm:   hstr    "CLOCK: NO MEMORY"
        .byte   $8D, 0
