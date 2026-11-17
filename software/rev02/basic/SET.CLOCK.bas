10 TEXT : D$ = CHR$(4) : PRINT D$;"PR#3" : PRINT CHR$(17); : POKE 49167,0 : HOME : DEF FN B(X) = INT(X / 16) * 10 + X - INT(X / 16) * 16
15 PRINT CHR$(15);"   Laser 128 RAM Expansion Clock Util   ";CHR$(14); : POKE 34,1 : HOME : PRINT
20 PRINT D$;"BLOAD CLOCK.SET"
22 POKE 777,1 : CALL 24576 : IF PEEK(775) <> 0 THEN PRINT "Clock not found." : POKE 34,0 : END
24 PRINT "The clock reads:" : GOSUB 500
26 PRINT : INPUT "Set the date and time (Y/N)? ";A$ : IF A$ <> "Y" AND A$ <> "y" THEN POKE 34,0 : END
28 PRINT
30 INPUT "Year (2000-2099): ";Y : IF Y < 2000 OR Y > 2099 THEN 30
40 INPUT "Month (1-12): ";M : IF M < 1 OR M > 12 THEN 40
50 INPUT "Day (1-31): ";D : IF D < 1 OR D > 31 THEN 50
60 INPUT "Hour (0-23): ";H : IF H < 0 OR H > 23 THEN 60
70 INPUT "Minute (0-59): ";N : IF N < 0 OR N > 59 THEN 70
80 REM WEEKDAY 1=SUNDAY (ZELLER)
90 Y1 = Y : M1 = M : IF M1 < 3 THEN M1 = M1 + 12 : Y1 = Y1 - 1
100 W = D + INT(13 * (M1 + 1) / 5) + Y1 + INT(Y1 / 4) - INT(Y1 / 100) + INT(Y1 / 400)
110 W = W + 6 : W = W - INT(W / 7) * 7 + 1
112 PRINT : PRINT "Save battery: skip temperature"
114 INPUT "compensation when off (Y/N)? ";B$
116 POKE 776,(B$ = "Y" OR B$ = "y")
120 PRINT : PRINT "The seconds start at 0 on Return."
130 INPUT "Press Return to set: ";A$
140 POKE 768,Y - 2000 : POKE 769,M : POKE 770,D : POKE 771,H : POKE 772,N : POKE 773,0 : POKE 774,W : POKE 777,0
150 CALL 24576
160 IF PEEK(775) <> 0 THEN PRINT "Clock not found." : POKE 34,0 : END
170 PRINT : PRINT "Clock set. It now reads:"
180 POKE 777,1 : CALL 24576 : GOSUB 500 : POKE 34,0 : END
500 M = PEEK(789) : IF M > 127 THEN M = M - 128
505 H = PEEK(786) : IF H > 63 THEN H = H - 64
510 W = PEEK(787) : IF W >= 1 AND W <= 7 THEN PRINT MID$("SunMonTueWedThuFriSat",W * 3 - 2,3);" ";
520 PRINT 2000 + FN B(PEEK(790));"-"; : V = FN B(M) : GOSUB 700 : PRINT "-"; : V = FN B(PEEK(788)) : GOSUB 700
530 PRINT " "; : V = FN B(H) : GOSUB 700 : PRINT ":"; : V = FN B(PEEK(785)) : GOSUB 700 : PRINT ":"; : V = FN B(PEEK(784)) : GOSUB 700 : PRINT
540 T = PEEK(801) * 4 + INT(PEEK(802) / 64) : IF T > 511 THEN T = T - 1024
550 C = T / 4 : F = INT((C * 1.8 + 32) * 10 + .5) / 10
560 PRINT "Temperature: ";C;" C / ";F;" F"
570 IF PEEK(799) > 127 THEN PRINT "Note: the clock stopped since it was" : PRINT "set (battery?): time may be wrong." : PRINT "Run SET.CLOCK."
580 RETURN
700 PRINT RIGHT$("0" + STR$(V),2); : RETURN
