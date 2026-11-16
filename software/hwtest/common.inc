; shared definitions for the hardware test programs (BRUN from BASIC.SYSTEM)
MLI      = $BF00
DATETIME = $BF06
COUT     = $FDED
PRBYTE   = $FDDA
CROUT    = $FD8E
RDKEY    = $FD0C
ALTZPOFF = $C008
ALTZPON  = $C009
RDBNK2   = $C080        ; read LC RAM bank 2, no write
RWBNK2   = $C083        ; read/write LC RAM bank 2 (read twice)
RDBNK1   = $C088        ; read LC RAM bank 1, no write
RWBNK1   = $C08B        ; read/write LC RAM bank 1 (read twice)
PTR      = $06          ; zero page $06-$07 are free for user programs
ROMIN    = $C082        ; ROM read, no write (BASIC.SYSTEM's normal state)

; print a high-bit string terminated by 0: pass address in A (lo) / X (hi)
.macro  print   str
        lda     #<str
        ldx     #>str
        jsr     prstr
.endmacro
