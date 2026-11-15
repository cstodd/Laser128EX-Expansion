; Laser 128 RAM + clock card: shared definitions

; --- expansion RAM ("slinky") registers on the Laser motherboard (Tech Ref sec. 7)
XAL      = $C0D0        ; address register low
XAM      = $C0D1        ; address register mid
XAH      = $C0D2        ; address register high nibble
PORT     = $C0D3        ; data register; in RTC mode: the card's I2C port
XEN      = $C500        ; any access to $C5xx enables the expansion RAM

; --- RTC port (CPLD, RTC mode). Write: bit0 = pull SDA low, bit1 = pull SCL low,
;     bit7 = lock (leave RTC mode). Read: %101101 scl sda
RTCSIG   = %10110100
RTCMASK  = %11111100

; --- 128K memory switches
RAMRDOFF = $C002
RAMRDON  = $C003
RAMWRTOFF= $C004
RAMWRTON = $C005

; --- ProDOS 8 global page
MLI      = $BF00
DATETIME = $BF06        ; JMP clock driver (RTS when none)
NODEV    = $BF10
DEVADR32 = $BF26        ; slot 3 drive 2 (/RAM) driver vector
DEVNUM   = $BF30
DEVCNT   = $BF31
DEVLST   = $BF32
DATE     = $BF90        ; DATELO, DATEHI
TIME     = $BF92        ; minute, hour
MACHID   = $BF98

GETBUFR  = $BEF5        ; BASIC.SYSTEM: allocate A pages, returns page in A (C=1 on error)
COUT     = $FDED
CROUT    = $FD8E

; --- body layout (one page)
BODY_SIG_OFS = 3        ; "CLK1" at body+3
BODY_PAGES   = 2        ; body occupies 2 pages; whole 512 bytes sum to 0
