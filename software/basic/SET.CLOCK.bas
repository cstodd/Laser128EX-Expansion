10 TEXT : D$ = CHR$(4) : PRINT D$;"PR#3" : PRINT CHR$(17); : POKE 49167,0 : HOME
15 PRINT CHR$(15);"   Laser 128 RAM Expansion Clock Util   ";CHR$(14); : POKE 34,1 : HOME : PRINT
20 PRINT D$;"BLOAD CLOCK.SET"
30 INPUT "Year (2000-2099): ";Y : IF Y < 2000 OR Y > 2099 THEN 30
40 INPUT "Month (1-12): ";M : IF M < 1 OR M > 12 THEN 40
50 INPUT "Day (1-31): ";D : IF D < 1 OR D > 31 THEN 50
60 INPUT "Hour (0-23): ";H : IF H < 0 OR H > 23 THEN 60
70 INPUT "Minute (0-59): ";N : IF N < 0 OR N > 59 THEN 70
80 REM WEEKDAY 1=SUNDAY (ZELLER)
90 Y1 = Y : M1 = M : IF M1 < 3 THEN M1 = M1 + 12 : Y1 = Y1 - 1
100 W = D + INT(13 * (M1 + 1) / 5) + Y1 + INT(Y1 / 4) - INT(Y1 / 100) + INT(Y1 / 400)
110 W = W + 6 : W = W - INT(W / 7) * 7 + 1
120 PRINT : PRINT "The seconds start at 0 on Return."
130 INPUT "Press Return to set: ";A$
140 POKE 768,Y - 2000 : POKE 769,M : POKE 770,D : POKE 771,H : POKE 772,N : POKE 773,0 : POKE 774,W
150 CALL 24576
160 IF PEEK(775) <> 0 THEN PRINT "Clock not found." : POKE 34,0 : END
170 PRINT "Clock set." : POKE 34,0
