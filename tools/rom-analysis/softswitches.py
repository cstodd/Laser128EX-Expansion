# linear sweep: find abs-mode references to $C000-$C0FF (and $C0xx,X) in each ROM bank
import sys,collections
sys.path.insert(0,'.')
from dis65c02 import dis1
fn=sys.argv[1]; d=open(fn,'rb').read()
refs=collections.defaultdict(list)
for i in range(len(d)-2):
    n,txt,md,w=dis1(d,i,0xC000-(0x4000 if i>=0x4000 else 0))
    if md in('abs','abx','aby') and 0xC000<=w<=0xC0FF:
        refs[w].append((i,txt))
for w in sorted(refs):
    print(f"${w:04X}: {len(refs[w]):3d}  e.g. " + ", ".join(f"{i:04X}:{t}" for i,t in refs[w][:4]))
