; CLOCK.SYSTEM: ProDOS 8 system program. Put it before BASIC.SYSTEM on the boot disk.
; Detects the Laser 128 RAM+clock card, disconnects /RAM, copies the clock driver body into
; auxiliary memory, installs the stub in ProDOS's clock-driver slot, then runs BASIC.SYSTEM.
        .include "defs.inc"
AUXPG   = $0C                           ; aux-memory pages $0C-$0D for the body copy
TMPPG   = $10                           ; scratch pages $10-$11 for relocation / detection
STUB    = $D742

        .segment "SYS"
start:  ldx     #msg_hello-msgs
        jsr     print
        lda     DATETIME+1              ; ProDOS clock slot where we expect it?
        cmp     #<STUB
        bne     fail_pd
        lda     DATETIME+2
        cmp     #>STUB
        bne     fail_pd
        lda     MACHID                  ; need 128K for the aux copy
        and     #$30
        cmp     #$30
        bne     fail_128
; detection: run the body from main memory once and see whether it produced an hour
        lda     #TMPPG
        ldx     #TMPPG
        jsr     reloc
        lda     #$FF
        sta     TIME+1
        jsr     TMPPG*256
        lda     TIME+1
        cmp     #24
        bcs     fail_rtc
        jsr     ramoff
; aux copy
        lda     #AUXPG
        ldx     #TMPPG
        jsr     reloc
        ldy     #0
        sta     RAMWRTON
:       lda     TMPPG*256,y
        sta     AUXPG*256,y
        lda     TMPPG*256+256,y
        sta     AUXPG*256+256,y
        iny
        bne     :-
        sta     RAMWRTOFF
; stub into the language card (bank 1, write-enabled by two reads of $C08B)
        lda     $C08B
        lda     $C08B
        ldx     #STUBLEN-1
:       lda     stubimg,x
        sta     STUB,x
        dex
        bpl     :-
        lda     #AUXPG
        sta     STUB+6
        lda     $C082                   ; ROM back, LC write-protected
        lda     #$4C                    ; DATETIME = JMP STUB
        sta     DATETIME
        lda     MACHID
        ora     #$01                    ; clock present
        sta     MACHID
        ldx     #msg_ok-msgs
        bne     msgchain
fail_pd: ldx    #msg_pd-msgs
        bne     msgchain
fail_128: ldx   #msg_128-msgs
        bne     msgchain
fail_rtc: ldx   #msg_rtc-msgs
msgchain:
        jsr     print
; move the chain loader to $0300 and run it (BASIC.SYSTEM loads over us at $2000)
        ldx     #chain_end-chain_run
:       lda     chain_img-1,x
        sta     chain_run-1,x
        dex
        bne     :-
        jmp     chain_run

; print message at msgs+X (high-bit ASCII, 0-terminated)
print:  lda     msgs,x
        beq     :+
        jsr     COUT
        inx
        bne     print
:       rts

; disconnect /RAM (ProDOS 8 Technical Reference, "Disconnecting /RAM")
ramoff: lda     DEVADR32
        cmp     NODEV
        bne     :+
        lda     DEVADR32+1
        cmp     NODEV+1
        beq     rdone                   ; already disconnected
:       ldx     DEVCNT
:       lda     DEVLST,x
        and     #$F0
        cmp     #$B0                    ; slot 3, drive 2
        beq     :+
        dex
        bpl     :-
        bmi     rdone
:       lda     DEVLST+1,x              ; close the gap
        sta     DEVLST,x
        cpx     DEVCNT
        beq     :+
        inx
        bne     :-
:       dec     DEVCNT
        lda     NODEV
        sta     DEVADR32
        lda     NODEV+1
        sta     DEVADR32+1
rdone:  rts

        .include "reloc.inc"

stubimg: .incbin "build/stub.bin"
STUBLEN = * - stubimg
        .assert STUBLEN <= 125, error, "stub exceeds ProDOS's 125-byte clock slot"

msgs:
        .feature string_escapes
        .macro  hstr s
        .repeat .strlen(s), i
        .byte   .strat(s, i) | $80
        .endrep
        .endmacro
msg_hello: .byte $8D
           hstr "LASER 128 CLOCK "
           .byte 0
msg_ok:    hstr "INSTALLED"
           .byte $8D, 0
msg_pd:    hstr "NOT INSTALLED: UNEXPECTED PRODOS"
           .byte $8D, 0
msg_128:   hstr "NOT INSTALLED: NEEDS 128K"
           .byte $8D, 0
msg_rtc:   hstr "NOT FOUND"
           .byte $8D, 0
        .assert * - msgs < 256, error, "messages too long"

; ---- chain loader: assembled for $0300, copied there at run time
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
