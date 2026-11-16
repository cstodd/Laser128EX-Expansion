; LC.CANARY: does a program (e.g. AppleWorks 5.1) leave aux language card bank 2 $D100-$DFFF alone?
; (Driver v2 question 2, docs/design-notes.md section 9; ProDOS TN #26 reserves that area for
; third-party RAM-based drivers.)
;   M = mark: fill $D100-$DFFF (aux LC bank 2) with a pattern made from each byte's address.
;   C = check: report each page as "." (intact) or "X" (changed), and the number of changed pages.
; Boot with CLOCK.SYSTEM first (it removes /RAM, which would otherwise own all aux memory).
        .setcpu "65C02"
        .include "common.inc"
PG      = $08           ; zero page $08-$09: pointer

        .segment "BIN"
start:  print   title
:       jsr     RDKEY
        and     #$DF                    ; upper case
        cmp     #'M' | $80
        beq     mark
        cmp     #'C' | $80
        beq     check
        cmp     #$9B                    ; Escape
        bne     :-
        rts


mark:   sei
        sta     ALTZPON                 ; no stack use until ALTZPOFF
        lda     RWBNK2
        lda     RWBNK2
        stz     PG
        lda     #$D1
        sta     PG+1
@pg:    ldy     #0
@by:    tya                             ; inline pat (no JSR: stack is aux now)
        eor     PG+1
        eor     #$A5
        sta     (PG),y
        iny
        bne     @by
        inc     PG+1
        lda     PG+1
        cmp     #$E0
        bne     @pg
        lda     ROMIN
        sta     ALTZPOFF
        cli
        print   m_marked
        rts

check:  print   m_check
        lda     #$D1
        sta     cpg
        stz     nbad
@pg:    sei
        sta     ALTZPON
        lda     RDBNK2
        lda     cpg
        sta     PG+1                    ; PG is in aux zero page now: set it here
        stz     PG
        ldx     #0                      ; X = 0 if the page is intact
        ldy     #0
@by:    tya
        eor     PG+1
        eor     #$A5
        cmp     (PG),y
        beq     :+
        inx
:       iny
        bne     @by
        lda     ROMIN
        sta     ALTZPOFF
        cli
        txa
        beq     @ok
        inc     nbad
        lda     #'X' | $80
        bne     @pr
@ok:    lda     #'.' | $80
@pr:    jsr     COUT
        inc     cpg
        lda     cpg
        cmp     #$E0
        bne     @pg
        jsr     CROUT
        print   m_nbad
        lda     nbad
        jsr     PRBYTE
        jsr     CROUT
        lda     nbad
        bne     :+
        print   m_intact
        rts
:       print   m_changed
        rts

        .include "prstr.inc"

title:  .byte   $8D, "LC.CANARY: AUX LC BANK 2 $D100-$DFFF", $8D
        .byte   "M = MARK, C = CHECK, ESC = QUIT", $8D, 0
m_marked: .byte "MARKED. NOW RUN THE PROGRAM TO TEST,", $8D
        .byte   "THEN RUN LC.CANARY AGAIN AND PRESS C.", $8D, 0
m_check: .byte  "PAGES $D1-$DF (. = INTACT, X = CHANGED):", $8D, 0
m_nbad: .byte   "CHANGED PAGES: $", 0
m_intact: .byte "AREA LEFT ALONE.", $8D, 0
m_changed: .byte "AREA WAS USED BY SOMETHING.", $8D, 0

cpg:    .byte   0
nbad:   .byte   0
