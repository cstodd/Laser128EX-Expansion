; Laser 128 RAM + clock card: ProDOS clock driver body (one page, relocatable).
;
; Called (JSR) by the stub in ProDOS's clock-driver slot. Reads the DS3231 through the
; card's hidden RTC port and fills in ProDOS DATE/TIME ($BF90-$BF93).
;
; Constraints (so the same code also runs from AUXILIARY memory with RAMRD on):
;   - scratch only in zero page (saved/restored on the stack) and on the stack;
;   - the only main-memory writes are DATE/TIME; no reads of main memory $0200-$BFFF.
;
; The unlock key's 8 writes land in RAM-disk memory at the current slinky address, so the
; driver saves those 8 bytes and the address registers first and puts everything back.
        .include "defs.inc"

ZBUF    = $3A           ; 6 RTC register bytes: min hour dow date month year
ZTMP    = ZBUF+6
ZSTAT   = ZBUF+7        ; 0 = RTC read OK
NZP     = 8

        .segment "BODY"
body:   jmp     read
sig:    .byte   "CLK1"                  ; body+3, checked by the stub

read:   php
        sei
        ldx     #NZP-1                  ; save our zero-page scratch
:       lda     ZBUF,x
        pha
        dex
        bpl     :-
        bit     XEN                     ; make sure the expansion RAM is enabled
        lda     XAH                     ; save the slinky address (H, M, L)
        pha
        lda     XAM
        pha
        lda     XAL
        pha
        ldx     #8                      ; save the 8 RAM bytes the key will overwrite
:       lda     PORT
        pha
        dex
        bne     :-
        jsr     setaddr
        ldx     #7                      ; unlock key (table is stored reversed)
:       lda     keyrev,x
        sta     PORT
        dex
        bpl     :-
        lda     PORT                    ; RTC mode answers with its signature
        and     #RTCMASK
        eor     #RTCSIG
        sta     ZSTAT
        bne     :+
        jsr     rtcread
        lda     #$80                    ; lock: back to RAM mode (never written to RAM)
        sta     PORT
:       jsr     setaddr                 ; put the 8 RAM bytes back
        tsx
        ldy     #8
:       lda     $0108,x                 ; data0 is deepest
        sta     PORT
        dex
        dey
        bne     :-
        ldx     #8                      ; drop them
:       pla
        dex
        bne     :-
        pla                             ; restore the slinky address
        sta     XAL
        pla
        sta     XAM
        pla
        sta     XAH
        lda     ZSTAT
        bne     done
; --- BCD registers -> ProDOS date/time
        lda     ZBUF+5                  ; year 00-99
        jsr     bcd2bin
        asl     a
        sta     ZBUF+5                  ; year << 1
        lda     ZBUF+4                  ; month (bit 7 = century)
        and     #$1F
        jsr     bcd2bin
        tay
        lsr     a
        lsr     a
        lsr     a
        ora     ZBUF+5
        sta     DATE+1                  ; DATEHI = year<<1 | month>>3
        tya
        asl     a
        asl     a
        asl     a
        asl     a
        asl     a
        sta     ZBUF+4
        lda     ZBUF+3                  ; date 1-31
        and     #$3F
        jsr     bcd2bin
        ora     ZBUF+4
        sta     DATE                    ; DATELO = month<<5 | day
        lda     ZBUF+1                  ; hour (24-hour mode)
        and     #$3F
        jsr     bcd2bin
        sta     TIME+1
        lda     ZBUF+0                  ; minute
        and     #$7F
        jsr     bcd2bin
        sta     TIME
done:   ldx     #0                      ; restore zero page
:       pla
        sta     ZBUF,x
        inx
        cpx     #NZP
        bne     :-
        plp
        rts

; X/Y-free: set the slinky address from the saved copy (called with 8 data bytes on stack)
setaddr:
        tsx
        lda     $010B,x
        sta     XAL
        lda     $010C,x
        sta     XAM
        lda     $010D,x
        sta     XAH
        rts

bcd2bin:
        pha
        lsr     a
        lsr     a
        lsr     a
        lsr     a
        sta     ZTMP
        asl     a
        asl     a
        adc     ZTMP                    ; tens * 5 (C clear)
        asl     a                       ; tens * 10
        sta     ZTMP
        pla
        and     #$0F
        adc     ZTMP
        rts

        .include "i2c.inc"

; DS3231: set register pointer to 1, read minute..year (6 bytes) into ZBUF
rtcread:
        ldx     #s_start-seqs
        jsr     seq
        lda     #$D0
        jsr     tx
        lda     #$01
        jsr     tx
        ldx     #s_start-seqs
        jsr     seq
        lda     #$D1
        jsr     tx
        ldx     #0
:       cpx     #5                      ; C=1 on the last byte -> NACK
        jsr     rx
        sta     ZBUF,x
        inx
        cpx     #6
        bne     :-
        ldx     #s_stop-seqs
        jmp     seq

keyrev: .byte   $A9,$72,$C4,$3F,$5B,$D1,$27,$8E   ; key 8E 27 D1 5B 3F C4 72 A9, reversed
