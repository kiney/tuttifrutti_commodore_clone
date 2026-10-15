"""Minimal disassembler for the documented NMOS 6502 instructions.

Addresses are memory addresses, including the PRG's two-byte load address.
Linear output is a reading aid: data embedded in the range is not code.
"""
from pathlib import Path
import argparse

# Every entry has mnemonic and addressing mode; '?' denotes an undocumented opcode.
ROWS = [
'BRK:i ORA:ix ? ? ? ORA:z ASL:z ? PHP:i ORA:n ASL:a ? ? ORA:w ASL:w ?',
'BPL:r ORA:iy ? ? ? ORA:zx ASL:zx ? CLC:i ORA:wy ? ? ? ORA:wx ASL:wx ?',
'JSR:w AND:ix ? ? BIT:z AND:z ROL:z ? PLP:i AND:n ROL:a ? BIT:w AND:w ROL:w ?',
'BMI:r AND:iy ? ? ? AND:zx ROL:zx ? SEC:i AND:wy ? ? ? AND:wx ROL:wx ?',
'RTI:i EOR:ix ? ? ? EOR:z LSR:z ? PHA:i EOR:n LSR:a ? JMP:w EOR:w LSR:w ?',
'BVC:r EOR:iy ? ? ? EOR:zx LSR:zx ? CLI:i EOR:wy ? ? ? EOR:wx LSR:wx ?',
'RTS:i ADC:ix ? ? ? ADC:z ROR:z ? PLA:i ADC:n ROR:a ? JMP:ind ADC:w ROR:w ?',
'BVS:r ADC:iy ? ? ? ADC:zx ROR:zx ? SEI:i ADC:wy ? ? ? ADC:wx ROR:wx ?',
'? STA:ix ? ? STY:z STA:z STX:z ? DEY:i ? TXA:i ? STY:w STA:w STX:w ?',
'BCC:r STA:iy ? ? STY:zx STA:zx STX:zy ? TYA:i STA:wy TXS:i ? ? STA:wx ? ?',
'LDY:n LDA:ix LDX:n ? LDY:z LDA:z LDX:z ? TAY:i LDA:n TAX:i ? LDY:w LDA:w LDX:w ?',
'BCS:r LDA:iy ? ? LDY:zx LDA:zx LDX:zy ? CLV:i LDA:wy TSX:i ? LDY:wx LDA:wx LDX:wy ?',
'CPY:n CMP:ix ? ? CPY:z CMP:z DEC:z ? INY:i CMP:n DEX:i ? CPY:w CMP:w DEC:w ?',
'BNE:r CMP:iy ? ? ? CMP:zx DEC:zx ? CLD:i CMP:wy ? ? ? CMP:wx DEC:wx ?',
'CPX:n SBC:ix ? ? CPX:z SBC:z INC:z ? INX:i SBC:n NOP:i ? CPX:w SBC:w INC:w ?',
'BEQ:r SBC:iy ? ? ? SBC:zx INC:zx ? SED:i SBC:wy ? ? ? SBC:wx INC:wx ?',
]
OPS = [x.split(':') if ':' in x else ('???','i') for row in ROWS for x in row.split()]
assert len(OPS)==256
SIZES = dict(i=1,a=1,n=2,z=2,zx=2,zy=2,ix=2,iy=2,r=2,w=3,wx=3,wy=3,ind=3)

def decode(mem, pc):
    op, mode = OPS[mem[pc]]
    size = SIZES[mode]
    bs = mem[pc:pc+size]
    value = int.from_bytes(bs[1:], 'little')
    target = None
    if mode=='r':
        target = (pc+2+(value if value<128 else value-256))&65535
        operand = f'${target:04X}'
    else:
        operand = {'i':'','a':'A','n':f'#${value:02X}','z':f'${value:02X}',
            'zx':f'${value:02X},X','zy':f'${value:02X},Y','ix':f'(${value:02X},X)',
            'iy':f'(${value:02X}),Y','w':f'${value:04X}','wx':f'${value:04X},X',
            'wy':f'${value:04X},Y','ind':f'(${value:04X})'}[mode]
        if op in ('JSR','JMP') and mode=='w': target=value
    return size, op, operand, target

def load(path):
    data=Path(path).read_bytes(); base=int.from_bytes(data[:2],'little')
    mem=bytearray(65536); mem[base:base+len(data)-2]=data[2:]
    return mem,base,base+len(data)-2

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--start',type=lambda x:int(x,0),default=0x1a50)
    ap.add_argument('--end',type=lambda x:int(x,0),default=0x3450)
    args=ap.parse_args();mem,_,_=load('tuttifrutti.prg');pc=args.start
    while pc<args.end:
        size,op,operand,_=decode(mem,pc)
        print(f'{pc:04X}  {mem[pc:pc+size].hex(" "):8}  {op:3} {operand}')
        pc+=size
