import sys
d=open(sys.argv[1],'rb').read()
cur=[];start=0
for i,b in enumerate(d+b'\0'):
    c=b&0x7f
    if 32<=c<127 and i<len(d): 
        if not cur: start=i
        cur.append(chr(c))
    else:
        if len(cur)>=int(sys.argv[2] if len(sys.argv)>2 else 5): print(f"{start:04X}: {''.join(cur)}")
        cur=[]
