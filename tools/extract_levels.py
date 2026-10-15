"""Extract packed map data and object starting positions from the original PRG."""
from pathlib import Path
from disassemble import load

m, _, _ = load('tuttifrutti.prg')
symbols = '.:*ACB#X'
lines = [
    'Tutti Frutti: maps extracted directly from tuttifrutti.prg',
    '========================================================',
    '',
    '16 columns × 12 rows; two tiles per byte; 96 bytes per map.',
    'Legend (names inferred from behavior):',
    '  . = 0 empty    : = 1 earth    * = 2 cherry    A = 3 stationary apple',
    '  C = 4 cherry block         B = 5 apple block',
    '  # = 6 fixed barrier        X = 7 another fixed barrier',
    'Directions: left=0, right=1, up=2, down=3.',
    'Player starts on tile (7, 1); enemies appear on tile (7, 6).',
    'Coordinates are zero-based. Internal movement coordinates / 8 = tile position.',
    '',
]
for index in range(7):
    address = 0x3500 + index*96
    title = 'Title-screen border' if index == 0 else f'Playable map {index}'
    lines += [f'{title} (${address:04X}..${address+95:04X})', '    0123456789ABCDEF']
    counts = {n:0 for n in range(8)}
    for y in range(12):
        raw = m[address+y*8:address+(y+1)*8]
        vals = [n for b in raw for n in [b>>4,b&15]]
        assert all(n<8 for n in vals)
        for n in vals: counts[n] += 1
        lines.append(f'{y:2}  '+''.join(symbols[n] for n in vals))
    lines += ['Tile counts: '+', '.join(f'{symbols[n]}={c}' for n,c in counts.items() if c)]
    if index:
        base = 0x37a0 + (index-1)*16
        positions = [(m[base+i],m[base+8+i]) for i in range(6)]
        lines += ['Fixed apple slots 0..5 (internal x/y): '+str(positions)]
        if index in [1,4]: rule='Mode 2: collect every cherry.'
        elif index in [2,5]: rule='Mode 4: collect every cherry and bring six apples to the bottom row.'
        else: rule='Mode 6: push apple blocks into all four corners; no shooting or gravity.'
        lines += [rule, 'Alternatively, defeating all enemies including reserves advances to the next round.']
    lines += ['']
Path('analysis/level_maps.txt').write_text('\n'.join(lines)+'\n')
print('Wrote analysis/level_maps.txt')
