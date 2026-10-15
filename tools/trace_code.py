import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from disassemble import load,decode
m,base,end=load('tuttifrutti.prg')
# Entry points and independently identified routine starts. See pseudocode.py.
roots=[0x1500,0x2000,0x20a0,0x1780,0x1a00,0x1a38,0x1a84,0x1aa8,0x1ac0,0x1b00,0x1b10,0x1b20,0x1b40,0x1bb0,0x1bdc,0x1bf5,0x1c00,0x1c60,0x1c80,0x1d30,0x1e00,0x1e34,0x1e50,0x1f00,0x1f50,0x1fa0,0x1fe0,0x20fa,0x2200,0x2300,0x233a,0x237e,0x23d0,0x2400,0x2470,0x2500,0x2530,0x2560,0x2570,0x25a0,0x2600,0x2634,0x2648,0x2700,0x2740,0x2800,0x2900,0x2940,0x2a00,0x2a40,0x2b00,0x2bf0,0x2c90,0x2cb3,0x2e00,0x2e2c,0x2e80,0x2ea0,0x2f10,0x2f30,0x2f80,0x2fb0,0x3000,0x3090,0x30a0,0x30c0,0x3100,0x315f,0x3200,0x3290,0x32a2,0x32bf,0x332c,0x3370,0x3380,0x33ac,0x33b0]
seen={};targets=set(roots); todo=roots[:]
while todo:
 pc=todo.pop()
 while base<=pc<end and pc not in seen:
  size,op,arg,target=decode(m,pc);seen[pc]=(size,op,arg,target)
  if op=='???': print('UNKNOWN',hex(pc));break
  if target is not None:
   targets.add(target)
   if base<=target<end:todo.append(target)
  if op in ('RTS','RTI','BRK','JMP'):break
  pc+=size
out=['; Statically followed 6502 control flow from tuttifrutti.prg.', '; Gaps are omitted. Labels and boundaries are analyst-generated.', '; Embedded tables are not decoded. This is not original source code.']; prev=None
for pc,(size,op,arg,target) in sorted(seen.items()):
 if prev!=pc:out.append('')
 if pc in targets:out.append(f'L_{pc:04X}:')
 out.append(f'{pc:04X}  {m[pc:pc+size].hex(" "):8}  {op:3} {arg}')
 prev=pc+size
Path('analysis/disassembly.txt').write_text('\n'.join(out)+'\n')
print('Instructions',len(seen),'bytes',sum(t[0] for t in seen.values()))
