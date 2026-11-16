; IRQ.TEST: are interrupts handled safely with ALTZP on and aux LC bank 2 switched in, during a
; ProDOS MLI call? (Driver v2 question 1, docs/design-notes.md section 9.)
;
; Interrupt source: serial port 2's 6551 transmit-empty interrupt at 9600 baud (about 960 per second,
; no cable needed). 1) count interrupts during a spin loop in main memory (baseline); 2) install a
; temporary clock driver that does exactly what v2 will (trampoline at $0200 -> spin loop in aux LC
; bank 2 at $D100 with interrupts on -> back), call GET_TIME 50 times, compare. Everything touched is
; restored, including the real clock driver.
        .setcpu "65C02"
        .include "common.inc"
ACIA_D  = $C0A8         ; port 2 (modem port) 6551
ACIA_S  = $C0A9
ACIA_C  = $C0AA
ACIA_K  = $C0AB
SPIN    = 16            ; spin length: SPIN * 256 * 5 cycles (about 20 ms at 1 MHz)
CALLS   = 50

        .segment "BIN"
start:  print   title
        lda     $BF98                   ; MACHID: need 128K
        and     #$30
        cmp     #$30
        beq     :+
        print   no128
        rts
:       jsr     save_all                ; slot, DATETIME, aux $D100 page
        jsr     alloc
        bcc     :+
        print   noalloc
        jmp     restore_all
:       lda     #$1E                    ; 9600 baud, 8N1
        sta     ACIA_K
        lda     #$07                    ; DTR on, receive IRQ off, transmit IRQ on
        sta     ACIA_C
        sta     ACIA_D                  ; prime the transmitter
; ---- baseline: same spin in main memory, interrupts on
        stz     count
        stz     count+1
        cli
        ldx     #CALLS
:       jsr     mainspin
        dex
        bne     :-
        sei
        lda     count
        sta     base
        lda     count+1
        sta     base+1
        print   m_base
        lda     base+1
        ldx     base
        jsr     prhex16
        jsr     CROUT
        lda     base
        ora     base+1
        bne     :+
        print   noirq                   ; nothing to test with
        jmp     finish
; ---- the v2 path, inside real MLI calls
:       jsr     install
        stz     count
        stz     count+1
        cli
        lda     #CALLS
        sta     ncall
:       jsr     MLI
        .byte   $82                     ; GET_TIME
        .word   0
        dec     ncall
        bne     :-
        sei
        print   m_aux
        lda     count+1
        ldx     count
        jsr     prhex16
        jsr     CROUT
        ; pass if aux count >= 7/8 of baseline (and we're still alive)
        lda     base                    ; t = base - base/8
        sta     tmp
        lda     base+1
        sta     tmp+1
        ldx     #3
:       lsr     tmp+1
        ror     tmp
        dex
        bne     :-
        sec
        lda     base
        sbc     tmp
        sta     tmp
        lda     base+1
        sbc     tmp+1
        sta     tmp+1
        lda     count                   ; count - t
        cmp     tmp
        lda     count+1
        sbc     tmp+1
        bcc     fail
        print   m_pass
        jmp     finish
fail:   print   m_fail
finish: lda     #$0B                    ; transmit IRQ off, RTS low, receive IRQ off
        sta     ACIA_C
        jsr     dealloc
        jmp     restore_all

; ---- spin in main memory with interrupts on (registers only)
mainspin:
        phx
        ldx     #SPIN
        ldy     #0
:       dey
        bne     :-
        dex
        bne     :-
        plx
        rts

; ---- interrupt handler (ProDOS ALLOC_INTERRUPT)
handler:
        cld
        lda     ACIA_S
        bpl     notours                 ; bit 7: this ACIA interrupted
        and     #$10                    ; transmit register empty?
        beq     :+
        stz     ACIA_D                  ; send a NUL: clears the interrupt
:       inc     count
        bne     :+
        inc     count+1
:       clc
        rts
notours:
        sec
        rts

alloc:  jsr     MLI
        .byte   $40                     ; ALLOC_INTERRUPT
        .word   aparm
        rts
dealloc:
        lda     aparm+1
        sta     dparm+1
        jsr     MLI
        .byte   $41
        .word   dparm
        rts
aparm:  .byte   2, 0
        .word   handler
dparm:  .byte   1, 0

; ---- save / install / restore
; slot address: DATETIME+1/+2. The 125 driver bytes are in LC bank 1.
save_all:
        sei
        lda     DATETIME
        sta     sv_dt
        lda     DATETIME+1
        sta     sv_dt+1
        sta     PTR
        lda     DATETIME+2
        sta     sv_dt+2
        sta     PTR+1
        lda     RWBNK1                  ; read LC bank 1
        lda     RWBNK1
        ldy     #124
:       lda     (PTR),y
        sta     sv_slot,y
        dey
        bpl     :-
        lda     ROMIN
        ; aux LC bank 2 page $D100: ALTZP on (no stack use until off)
        sta     ALTZPON
        lda     RDBNK2
        ldy     #0
:       lda     $D100,y
        sta     sv_aux,y                ; writes go to main memory (RAMWRT off)
        iny
        bne     :-
        lda     ROMIN
        sta     ALTZPOFF
        cli
        rts

install:
        sei
        lda     sv_dt+1                 ; slot address again (printing used PTR)
        sta     PTR
        lda     sv_dt+2
        sta     PTR+1
        ldy     #15                     ; trampoline at $0200
:       lda     tramp,y
        sta     $0200,y
        dey
        bpl     :-
        sta     ALTZPON                 ; spin routine into aux LC bank 2 $D100
        lda     RWBNK2
        lda     RWBNK2
        ldy     #auxspin_end-auxspin-1
:       lda     auxspin,y
        sta     $D100,y
        dey
        bpl     :-
        lda     ROMIN
        sta     ALTZPOFF
        lda     RWBNK1                  ; test stub into the ProDOS clock slot
        lda     RWBNK1
        ldy     #tstub_end-tstub-1
:       lda     tstub,y
        sta     (PTR),y
        dey
        bpl     :-
        lda     ROMIN
        lda     #$4C                    ; DATETIME = JMP slot
        sta     DATETIME
        rts

restore_all:
        sei
        lda     sv_dt+1
        sta     PTR
        lda     sv_dt+2
        sta     PTR+1
        lda     RWBNK1
        lda     RWBNK1
        ldy     #124
:       lda     sv_slot,y
        sta     (PTR),y
        dey
        bpl     :-
        lda     ROMIN
        lda     sv_dt
        sta     DATETIME
        sta     ALTZPON
        lda     RWBNK2
        lda     RWBNK2
        ldy     #0
:       lda     sv_aux,y
        sta     $D100,y
        iny
        bne     :-
        lda     ROMIN
        sta     ALTZPOFF
        cli
        print   m_done
        rts

prhex16:                                ; A = high, X = low
        jsr     PRBYTE
        txa
        jmp     PRBYTE

        .include "prstr.inc"

; ---- code copied elsewhere (position-independent or fixed-address)
; trampoline, runs at $0200 (16 bytes; TN #1 lets a clock driver use $0200-$0210)
tramp:  sta     ALTZPON                 ; $0200
        lda     RDBNK2                  ; $0203 aux LC bank 2 readable
        jmp     $D100                   ; $0206
        lda     RDBNK1                  ; $0209 back: LC bank 1
        sta     ALTZPOFF                ; $020C
        rts                             ; $020F
; spin loop, runs at aux LC $D100: interrupts on, registers only, JMP back
auxspin:
        ldx     #SPIN
        ldy     #0
        cli
:       dey
        bne     :-
        dex
        bne     :-
        sei
        jmp     $0209
auxspin_end:
; test clock driver in the ProDOS slot (position-independent)
tstub:  php
        sei
        jsr     $0200
        lda     RWBNK1                  ; LC bank 1 read/write, as the MLI had it
        lda     RWBNK1
        plp
        rts
tstub_end:

title:  .byte   $8D, "IRQ.TEST: INTERRUPTS WITH ALTZP + AUX LC", $8D
        .byte   "USES SERIAL PORT 2 (NOTHING NEED BE", $8D
        .byte   "CONNECTED). ABOUT 2 SECONDS.", $8D, $8D, 0
no128:  .byte   "NEEDS 128K.", $8D, 0
noalloc: .byte  "ALLOC_INTERRUPT FAILED (TABLE FULL?)", $8D, 0
noirq:  .byte   "NO INTERRUPTS SEEN IN THE BASELINE:", $8D
        .byte   "PORT 2 TX INTERRUPT NOT WORKING HERE.", $8D
        .byte   "TEST INCONCLUSIVE.", $8D, 0
m_base: .byte   "BASELINE IRQS (MAIN MEMORY): $", 0
m_aux:  .byte   "IRQS WITH ALTZP + AUX LC BANK 2: $", 0
m_pass: .byte   $8D, "PASS: INTERRUPTS HANDLED NORMALLY.", $8D, 0
m_fail: .byte   $8D, "FAIL: INTERRUPTS LOST WITH ALTZP ON.", $8D, 0
m_done: .byte   "RESTORED. DONE.", $8D, 0

count:  .word   0
base:   .word   0
tmp:    .word   0
ncall:  .byte   0
sv_dt:  .res    3
sv_slot: .res   125
sv_aux: .res    256
