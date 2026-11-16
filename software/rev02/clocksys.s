; CLOCK.SYSTEM (rev 0.2): ProDOS 8 system program. Put it before BASIC.SYSTEM on the boot disk.
; Finds the rev 0.2 card (DS3234), installs the 122-byte clock driver in ProDOS's clock slot, then runs
; BASIC.SYSTEM. Leaves /RAM and all aux memory alone. Does nothing if another clock is already installed.
        .setcpu "65C02"
        .include "../rev01/defs.inc"
        .include "build/drvinfo.inc"            ; DRV_LEN, KEYOP_OFS, KEYREV_OFS (from the driver build)
PTR     = $06

        .segment "SYS"
start:  ldx     #msg_hello-msgs
        jsr     print
        lda     MACHID                  ; a clock already? (ProDOS's own, or another driver)
        lsr     a
        bcs     fail_have
        lda     DATETIME
        cmp     #$60                    ; RTS = no clock driver installed
        bne     fail_have
        php
        sei
        jsr     rtc_open                ; C = 1: not found (already put back)
        bcs     :+
        jsr     rtc_close
        plp
        bra     install
:       plp
        bra     fail_rtc
install:
        lda     DATETIME+1              ; driver -> ProDOS's clock slot (LC bank 1, write-enabled)
        sta     PTR
        lda     DATETIME+2
        sta     PTR+1
        lda     $C08B
        lda     $C08B
        ldy     #DRV_LEN-1
:       lda     drvimg,y
        sta     (PTR),y
        dey
        bpl     :-
        clc                             ; patch the key-table pointer: slot + KEYREV_OFS
        lda     PTR
        adc     #KEYREV_OFS
        ldy     #KEYOP_OFS
        sta     (PTR),y
        lda     PTR+1
        adc     #0
        iny
        sta     (PTR),y
        lda     $C082                   ; ROM back, LC write-protected
        lda     #$4C                    ; DATETIME = JMP slot
        sta     DATETIME
        lda     MACHID
        ora     #$01                    ; clock present
        sta     MACHID
        ldx     #msg_ok-msgs
        bne     msgchain
fail_have: ldx  #msg_have-msgs
        bne     msgchain
fail_rtc: ldx   #msg_rtc-msgs
msgchain:
        jsr     print
        ldx     #chain_end-chain_run    ; chain loader to $0300 (BASIC.SYSTEM loads over us at $2000)
:       lda     chain_img-1,x
        sta     chain_run-1,x
        dex
        bne     :-
        jmp     chain_run

print:  lda     msgs,x
        beq     :+
        jsr     COUT
        inx
        bne     print
:       rts

        .include "rtcspi.inc"

drvimg: .incbin "build/clkdrv.bin"
        .assert * - drvimg = DRV_LEN, error, "driver image size mismatch"

msgs:
        .macro  hstr s
        .repeat .strlen(s), i
        .byte   .strat(s, i) | $80
        .endrep
        .endmacro
msg_hello: .byte $8D
           hstr "LASER 128 CLOCK (REV 0.2) "
           .byte 0
msg_ok:    hstr "INSTALLED"
           .byte $8D, 0
msg_have:  hstr "NOT INSTALLED: A CLOCK IS ALREADY ACTIVE"
           .byte $8D, 0
msg_rtc:   hstr "NOT FOUND"
           .byte $8D, 0
        .assert * - msgs < 256, error, "messages too long"

chain_img:
        .org    $0300
chain_run:
        jsr     MLI
        .byte   $C8                     ; OPEN
        .word   p_open
        bcs     quit
        lda     p_open+5
        sta     p_read+1
        jsr     MLI
        .byte   $CA                     ; READ
        .word   p_read
        php
        jsr     MLI
        .byte   $CC                     ; CLOSE
        .word   p_close
        plp
        bcs     quit
        jmp     $2000
quit:   jsr     MLI
        .byte   $65                     ; QUIT
        .word   p_quit
p_open:  .byte  3
        .word   name, $1C00
        .byte   0
p_read:  .byte  4, 0
        .word   $2000, $7C00, 0
p_close: .byte  1, 0
p_quit:  .byte  4, 0, 0, 0, 0, 0, 0
name:   .byte   12, "BASIC.SYSTEM"
chain_end:
        .reloc
