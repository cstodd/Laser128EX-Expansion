10 TEXT : D$ = CHR$(4) : PRINT D$;"PR#3" : PRINT CHR$(17); : POKE 49167,0 : HOME : DEF FN B(X) = INT(X / 16) * 10 + X - INT(X / 16) * 16
20 PRINT CHR$(15);"   Laser 128 RAM Expansion Clock Test   ";CHR$(14); : POKE 34,1 : HOME : PRINT
30 PRINT D$;"BLOAD CARDTEST"
40 HOME : PRINT "Speed: 1) 1 MHz 2) 2.3 MHz 3) 3.6 MHz"
50 INPUT "Choose (1-3): ";S : IF S < 1 OR S > 3 THEN 50
60 SP = 0 : S$ = "1" : IF S = 2 THEN SP = 128 : S$ = "2.3"
70 IF S = 3 THEN SP = 192 : S$ = "3.6"
80 POKE 49268,SP
90 HOME : PRINT "Speed: ";S$;" MHz" : PRINT : PRINT "1) Quick RAM test (keeps RAM disk)"
100 PRINT "2) Full address test (erases RAM disk)"
110 PRINT "3) Battery check (after test 2)"
120 PRINT "4) Clock test"
125 PRINT "5) Bank hop test (keeps RAM disk)"
130 PRINT "6) Change speed"
135 PRINT "7) Quit"
140 INPUT "Choose (1-7): ";C : IF C < 1 OR C > 7 THEN 140
150 IF C = 7 THEN POKE 34,0 : HOME : END
160 IF C = 6 THEN 40
170 IF C = 4 THEN 400
180 IF C = 2 THEN INPUT "Erase all RAM disk data (Y/N)? ";A$ : IF A$ <> "Y" AND A$ <> "y" THEN 90
185 IF C = 3 THEN GOSUB 800 : IF A$ <> "Y" AND A$ <> "y" THEN 900
190 POKE 768,C : POKE 777,0 : POKE 778,(C = 3) : PRINT "Testing ";
200 CALL 24576
210 IF C = 2 AND PEEK(769) = 0 THEN POKE 768,3 : CALL 24576
220 PRINT : R = PEEK(769)
230 IF R = 255 THEN PRINT "Card not responding." : GOTO 900
240 IF R = 0 THEN PRINT "Pass." : GOTO 300
250 E = PEEK(775) + 256 * PEEK(776)
260 PRINT "Fail: ";E;" errors"; : IF E = 65535 THEN PRINT " or more";
270 PRINT : N = PEEK(770) + 256 * PEEK(771) + 65536 * PEEK(772)
280 PRINT "First at $"; : GOSUB 600 : PRINT ": wrote ";PEEK(773);", read ";PEEK(774)
290 GOTO 900
300 IF C <> 2 THEN 320
302 PRINT "Pattern left in RAM; RAM disk erased."
304 PRINT "To check the battery: power off, wait"
306 PRINT "a while, boot, then run test 3."
320 GOTO 900
400 POKE 768,4 : CALL 24576 : IF PEEK(769) <> 0 THEN PRINT "Clock not found." : GOTO 900
410 S0 = PEEK(784) : PRINT "Checking the clock..."
420 FOR I = 1 TO 600 : POKE 768,4 : CALL 24576 : IF PEEK(784) <> S0 THEN 450
430 NEXT I
440 PRINT "Clock not running (seconds stuck)." : GOSUB 500 : GOTO 470
450 PRINT "Clock running." : GOSUB 500
470 GOTO 900
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
600 H$ = "0123456789ABCDEF" : FOR K = 4 TO 0 STEP - 1 : P = 16 ^ K : D = INT(N / P) : N = N - D * P : PRINT MID$(H$,D + 1,1); : NEXT K : RETURN
700 PRINT RIGHT$("0" + STR$(V),2); : RETURN
800 PRINT "Was test 2 run before the last"
810 INPUT "power-off (Y/N)? ";A$ : IF A$ = "Y" OR A$ = "y" THEN 840
820 PRINT "Run test 2 first: it fills the RAM with" : PRINT "a pattern. Then power off, wait, boot,"
830 PRINT "and run test 3 to see if it survived." : RETURN
840 PRINT "Checking 960K (first 64K skipped: the" : PRINT "boot reformats the RAM disk there)." : RETURN
900 PRINT : PRINT "Press any key for the menu."; : GET K$ : GOTO 90
