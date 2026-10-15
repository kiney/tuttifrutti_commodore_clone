"""Check deductions by executing isolated routines from the original PRG.

This deliberately small CPU runner is NOT a Plus/4 emulator: no TED, ROM,
interrupts, sound, cycle timing, decimal arithmetic or keyboard emulation.
Only the documented instructions needed by the selected routines are supported.
Run from the repository root: python3 tools/verify_analysis.py
"""
from disassemble import load, OPS, SIZES


class CPU:
    def __init__(self):
        self.m, _, _ = load('tuttifrutti.prg')
        self.a = self.x = self.y = 0
        self.sp = 255
        self.c = self.z = self.n = self.v = False

    def push(self, value):
        self.m[0x100 + self.sp] = value & 255
        self.sp = (self.sp - 1) & 255

    def pop(self):
        self.sp = (self.sp + 1) & 255
        return self.m[0x100 + self.sp]

    def nz(self, value):
        value &= 255
        self.z = value == 0
        self.n = bool(value & 128)
        return value

    def run(self, start, limit=200000):
        assert self.sp == 255
        self.push(0xff)
        self.push(0xfd)  # RTS to $FFFE terminates the isolated call.
        pc = start
        for _ in range(limit):
            if pc == 0xfffe:
                assert self.sp == 255
                return
            op, mode = OPS[self.m[pc]]
            size = SIZES[mode]
            value = int.from_bytes(self.m[pc+1:pc+size], 'little')
            pc += size
            addr = None
            if mode == 'n': data = value
            elif mode in ('z', 'w'): addr = value
            elif mode == 'zx': addr = (value + self.x) & 255
            elif mode == 'zy': addr = (value + self.y) & 255
            elif mode == 'wx': addr = (value + self.x) & 65535
            elif mode == 'wy': addr = (value + self.y) & 65535
            elif mode == 'iy':
                addr = (self.m[value] + 256*self.m[(value+1)&255] + self.y) & 65535
            elif mode == 'ix':
                p = (value + self.x) & 255
                addr = self.m[p] + 256*self.m[(p+1)&255]
            if addr is not None: data = self.m[addr]
            if op in ('LDA', 'LDX', 'LDY'):
                setattr(self, op[-1].lower(), self.nz(data))
            elif op in ('STA', 'STX', 'STY'):
                self.m[addr] = getattr(self, op[-1].lower())
            elif op in ('AND', 'ORA', 'EOR'):
                self.a = self.nz({'AND':self.a & data, 'ORA':self.a | data,
                                  'EOR':self.a ^ data}[op])
            elif op in ('ADC', 'SBC'):
                operand = data if op == 'ADC' else data ^ 255
                result = self.a + operand + self.c
                self.v = bool((~(self.a ^ operand) & (self.a ^ result)) & 128)
                self.c = result > 255
                self.a = self.nz(result)
            elif op in ('CMP', 'CPX', 'CPY'):
                reg = {'CMP':self.a, 'CPX':self.x, 'CPY':self.y}[op]
                self.c = reg >= data
                self.nz(reg-data)
            elif op in ('ASL', 'LSR', 'ROL', 'ROR'):
                old = self.a if mode == 'a' else data
                carry = self.c
                self.c = bool(old & (128 if op in ('ASL','ROL') else 1))
                result = {'ASL':old<<1, 'LSR':old>>1,
                          'ROL':(old<<1)|carry, 'ROR':(old>>1)|(carry<<7)}[op]
                result = self.nz(result)
                if mode == 'a': self.a = result
                else: self.m[addr] = result
            elif op in ('INC', 'DEC'):
                self.m[addr] = self.nz(data + (1 if op == 'INC' else -1))
            elif op in ('INX', 'DEX', 'INY', 'DEY'):
                reg = op[-1].lower()
                setattr(self, reg, self.nz(getattr(self, reg) + (1 if op[0]=='I' else -1)))
            elif op in ('TAX','TAY','TXA','TYA','TSX','TXS'):
                src, dst = op[1].lower(), op[2].lower()
                val = self.sp if src=='s' else getattr(self, src)
                if dst=='s': self.sp = val
                else: setattr(self, dst, self.nz(val))
            elif op == 'PHA': self.push(self.a)
            elif op == 'PLA': self.a = self.nz(self.pop())
            elif op == 'JSR':
                self.push((pc-1)>>8); self.push(pc-1); pc = value
            elif op == 'RTS': pc = ((self.pop() | self.pop()<<8) + 1) & 65535
            elif op == 'JMP' and mode=='w': pc = value
            elif op == 'CLC': self.c = False
            elif op == 'SEC': self.c = True
            elif op in ('BNE','BEQ','BCC','BCS','BPL','BMI','BVC','BVS'):
                taken = {'BNE':not self.z,'BEQ':self.z,'BCC':not self.c,'BCS':self.c,
                         'BPL':not self.n,'BMI':self.n,'BVC':not self.v,'BVS':self.v}[op]
                if taken: pc = (pc + (value if value<128 else value-256)) & 65535
            elif op in ('NOP','SEI','CLI'): pass
            else: raise RuntimeError(f'Unsupported instruction {op} at ${pc-size:04X}')
        raise RuntimeError('Instruction limit exceeded')


def verify():
    cpu = CPU()
    # Compare the original nibble getter with a separately decoded level.
    for level in range(1, 7):
        raw = cpu.m[0x3500+96*level:0x3500+96*(level+1)]
        cpu.m[0x600:0x660] = raw
        for y in range(12):
            for x in range(16):
                cpu.x, cpu.y = x, y
                cpu.run(0x2f80)
                expected = (raw[y*8+x//2] >> (4 if x%2==0 else 0)) & 15
                assert cpu.a == expected
    for x,y in [(16,0),(0,12),(255,0),(0,255)]:
        cpu.x,cpu.y=x,y;cpu.run(0x2f80);assert cpu.a==15
    print('OK: Original map getter: 6 × 192 cells and boundary checks')
    for x in range(16):
        for value in range(8):
            cpu.m[0x600:0x660]=bytes([0xab])*96
            cpu.x,cpu.y,cpu.a=x,5,value
            cpu.run(0x2fb0)
            expected = (value<<4|11) if x%2==0 else (0xa0|value)
            assert cpu.m[0x600+5*8+x//2]==expected
    print('OK: Original map setter preserves the adjacent half-byte')
    for mask, expected in [(0,255),(4,0),(8,1),(1,2),(2,3),(15,3)]:
        cpu.a=mask;cpu.run(0x2600);assert cpu.a==expected
    print('OK: Direction encoding and simultaneous-input priority')
    for start, increment in [(0x1b00,25),(0x1b10,100),(0x1b20,250)]:
        for score in [0,9,99,999,99990]:
            cpu.m[0xc4a:0xc4f]=bytes(int(n)+0x1c for n in f'{score:05d}')
            cpu.m[0xe2]=2;cpu.run(start)
            got=''.join(str(n-0x1c) for n in cpu.m[0xc4a:0xc4f])
            assert int(got)==(score+increment)%100000
    print('OK: Cherry = 25, shot hit = 100, falling-object hit = 250 points')
    for stage in [0,1,2,0xabcdef,0xffffff]:
        cpu.m[0x89:0x8c]=stage.to_bytes(3,'little');cpu.run(0x1fe0)
        assert int.from_bytes(cpu.m[0x89:0x8c],'little')==(stage+0xb13579)&0xffffff
    print('OK: Pseudorandom state advances by $B13579, modulo 2^24')
    for level in range(1,7):
        cpu.m[0xe2]=2;cpu.x=level;cpu.run(0x2940)
        assert cpu.m[0x600:0x660]==cpu.m[0x3500+96*level:0x3500+96*(level+1)]
    print('OK: Original level loader copies all six packed maps to $0600')
    for level in range(6):
        cpu.m[0xe5]=(level-1)&255
        cpu.m[0xb6]=255
        cpu.m[0xe2]=[1,3,5][level%3]
        cpu.m[0xe2a:0xe2c]=bytes([0x1c,0x1c])
        cpu.run(0x315f)
        assert cpu.m[0xe5]==level
        assert cpu.m[0x360]==56 and cpu.m[0x368]==8
        assert list(cpu.m[0x4f1:0x4f6])==[32,48,64,80,96]
        assert list(cpu.m[0xd3a:0xd3d])==[0x21+2*(level%3),0x25,0x25]
    print('OK: All six round initializations: player, spawns, bonus 599/799/999')
    for mode in [2,4,6]:
        cpu.m[0x600:0x660]=bytes(96)
        if mode==4:
            for x in range(6):
                cpu.x,cpu.y,cpu.a=x,11,3;cpu.run(0x2fb0)
        elif mode==6:
            for x,y in [(0,0),(15,0),(0,11),(15,11)]:
                cpu.x,cpu.y,cpu.a=x,y,5;cpu.run(0x2fb0)
        cpu.m[0xe2]=mode
        cpu.m[0xe5]=0
        cpu.m[0xc4a:0xc4f]=bytes([0x1c])*5
        cpu.m[0xd3a:0xd3d]=bytes([0x1d,0x1e,0x1f])  # bonus 123
        cpu.m[0x360]=cpu.m[0x368]=0
        cpu.run(0x2bf0)
        assert cpu.m[0xe2]==(mode+1 if mode<6 else 1)
        assert cpu.m[0xe6]==224
        assert list(cpu.m[0xc4a:0xc4f])==[0x1c,0x1d,0x1d,0x1e,0x1f] # 01123
    print('OK: All three map goals and transition with remaining bonus + 1000')
    # Preserve an observed anomaly rather than silently treating it as a delay.
    probe=CPU();probe.x=0;probe.m[0x338]=2
    try:
        probe.run(0x2c90)
    except RuntimeError as error:
        assert 'BRK at $0001' in str(error) and probe.sp==1
    else:
        raise AssertionError('Expected anomalous return path at $2C90')
    print('OBSERVED: $2C90 with delay=2 consumes unmatched stack entries')


if __name__ == '__main__':
    verify()
