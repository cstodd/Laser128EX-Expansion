# minimal 65C02 disassembler
import sys
M={}
def op(code,mn,mode): M[code]=(mn,mode)
tbl="""
00 BRK imp|01 ORA izx|04 TSB zp|05 ORA zp|06 ASL zp|07 RMB0 zp|08 PHP imp|09 ORA imm|0A ASL acc|0C TSB abs|0D ORA abs|0E ASL abs|0F BBR0 zpr
10 BPL rel|11 ORA izy|12 ORA izp|14 TRB zp|15 ORA zpx|16 ASL zpx|17 RMB1 zp|18 CLC imp|19 ORA aby|1A INC acc|1C TRB abs|1D ORA abx|1E ASL abx|1F BBR1 zpr
20 JSR abs|21 AND izx|24 BIT zp|25 AND zp|26 ROL zp|27 RMB2 zp|28 PLP imp|29 AND imm|2A ROL acc|2C BIT abs|2D AND abs|2E ROL abs|2F BBR2 zpr
30 BMI rel|31 AND izy|32 AND izp|34 BIT zpx|35 AND zpx|36 ROL zpx|37 RMB3 zp|38 SEC imp|39 AND aby|3A DEC acc|3C BIT abx|3D AND abx|3E ROL abx|3F BBR3 zpr
40 RTI imp|41 EOR izx|45 EOR zp|46 LSR zp|47 RMB4 zp|48 PHA imp|49 EOR imm|4A LSR acc|4C JMP abs|4D EOR abs|4E LSR abs|4F BBR4 zpr
50 BVC rel|51 EOR izy|52 EOR izp|55 EOR zpx|56 LSR zpx|57 RMB5 zp|58 CLI imp|59 EOR aby|5A PHY imp|5D EOR abx|5E LSR abx|5F BBR5 zpr
60 RTS imp|61 ADC izx|64 STZ zp|65 ADC zp|66 ROR zp|67 RMB6 zp|68 PLA imp|69 ADC imm|6A ROR acc|6C JMP ind|6D ADC abs|6E ROR abs|6F BBR6 zpr
70 BVS rel|71 ADC izy|72 ADC izp|74 STZ zpx|75 ADC zpx|76 ROR zpx|77 RMB7 zp|78 SEI imp|79 ADC aby|7A PLY imp|7C JMP iax|7D ADC abx|7E ROR abx|7F BBR7 zpr
80 BRA rel|81 STA izx|84 STY zp|85 STA zp|86 STX zp|87 SMB0 zp|88 DEY imp|89 BIT imm|8A TXA imp|8C STY abs|8D STA abs|8E STX abs|8F BBS0 zpr
90 BCC rel|91 STA izy|92 STA izp|94 STY zpx|95 STA zpx|96 STX zpy|97 SMB1 zp|98 TYA imp|99 STA aby|9A TXS imp|9C STZ abs|9D STA abx|9E STZ abx|9F BBS1 zpr
A0 LDY imm|A1 LDA izx|A2 LDX imm|A4 LDY zp|A5 LDA zp|A6 LDX zp|A7 SMB2 zp|A8 TAY imp|A9 LDA imm|AA TAX imp|AC LDY abs|AD LDA abs|AE LDX abs|AF BBS2 zpr
B0 BCS rel|B1 LDA izy|B2 LDA izp|B4 LDY zpx|B5 LDA zpx|B6 LDX zpy|B7 SMB3 zp|B8 CLV imp|B9 LDA aby|BA TSX imp|BC LDY abx|BD LDA abx|BE LDX aby|BF BBS3 zpr
C0 CPY imm|C1 CMP izx|C4 CPY zp|C5 CMP zp|C6 DEC zp|C7 SMB4 zp|C8 INY imp|C9 CMP imm|CA DEX imp|CB WAI imp|CC CPY abs|CD CMP abs|CE DEC abs|CF BBS4 zpr
D0 BNE rel|D1 CMP izy|D2 CMP izp|D5 CMP zpx|D6 DEC zpx|D7 SMB5 zp|D8 CLD imp|D9 CMP aby|DA PHX imp|DB STP imp|DD CMP abx|DE DEC abx|DF BBS5 zpr
E0 CPX imm|E1 SBC izx|E4 CPX zp|E5 SBC zp|E6 INC zp|E7 SMB6 zp|E8 INX imp|E9 SBC imm|EA NOP imp|EC CPX abs|ED SBC abs|EE INC abs|EF BBS6 zpr
F0 BEQ rel|F1 SBC izy|F2 SBC izp|F5 SBC zpx|F6 INC zpx|F7 SMB7 zp|F8 SED imp|F9 SBC aby|FA PLX imp|FD SBC abx|FE INC abx|FF BBS7 zpr
"""
for part in tbl.replace("\n","|").split("|"):
    part=part.strip()
    if part: c,mn,md=part.split(); op(int(c,16),mn,md)
L={'imp':1,'acc':1,'imm':2,'zp':2,'zpx':2,'zpy':2,'izx':2,'izy':2,'izp':2,'rel':2,'abs':3,'abx':3,'aby':3,'ind':3,'iax':3,'zpr':3}
def dis1(d,i,base):
    c=d[i]
    if c not in M: return 1,f".db ${c:02X}",None,None
    mn,md=M[c]; n=L[md]
    if i+n>len(d): return 1,f".db ${c:02X}",None,None
    a=d[i+1] if n>1 else 0; w=a|(d[i+2]<<8) if n==3 else a
    pc=base+i
    f={'imp':'','acc':'A','imm':f'#${a:02X}','zp':f'${a:02X}','zpx':f'${a:02X},X','zpy':f'${a:02X},Y','izx':f'(${a:02X},X)','izy':f'(${a:02X}),Y','izp':f'(${a:02X})',
       'rel':f'${(pc+2+(a-256 if a>127 else a))&0xFFFF:04X}','abs':f'${w:04X}','abx':f'${w:04X},X','aby':f'${w:04X},Y','ind':f'(${w:04X})','iax':f'(${w:04X},X)',
       'zpr':f'${a:02X},${(pc+3+((d[i+2]-256) if d[i+2]>127 else d[i+2]))&0xFFFF:04X}'}[md]
    return n,f"{mn} {f}".strip(),md,w
def run(fn,start,end,bank_base=0xC000,bankoff=0):
    d=open(fn,'rb').read()
    i=start
    while i<end:
        n,txt,md,w=dis1(d,i,bank_base-bankoff)
        print(f"{bank_base-bankoff+i:04X} [{i:04X}] {' '.join(f'{x:02X}' for x in d[i:i+n]):9} {txt}")
        i+=n
if __name__=="__main__":
    fn=sys.argv[1]; s=int(sys.argv[2],16); e=int(sys.argv[3],16)
    bankoff = 0x4000 if s>=0x4000 else 0
    run(fn,s,e,0xC000,bankoff)
