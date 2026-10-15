"""Extract packed map data and object starting positions from the original PRG."""
from pathlib import Path
from disassemble import load

m, _, _ = load('tuttifrutti.prg')
symbols = '.:*AKO#X'
lines = [
    'Tutti Frutti: direkt aus tuttifrutti.prg extrahierte Karten',
    '========================================================',
    '',
    '16 Spalten × 12 Zeilen; zwei Felder pro Byte; 96 Bytes pro Karte.',
    'Legende (die Namen sind funktional erschlossen):',
    '  . = 0 leer     : = 1 Erde    * = 2 Kirsche    A = 3 fester Apfel',
    '  K = 4 Kirschblock          O = 5 Apfelblock',
    '  # = 6 feste Sperre         X = 7 weitere feste Sperre',
    'Richtungen: links=0, rechts=1, oben=2, unten=3.',
    'Spieler startet auf Feld (7, 1), Gegner erscheinen auf Feld (7, 6).',
    'Koordinaten zählen ab 0. Interne Bewegungskoordinaten / 8 = Feldposition.',
    '',
]
for index in range(7):
    address = 0x3500 + index*96
    title = 'Startbild-Rahmen' if index == 0 else f'Spielkarte {index}'
    lines += [f'{title} (${address:04X}..${address+95:04X})', '    0123456789ABCDEF']
    counts = {n:0 for n in range(8)}
    for y in range(12):
        raw = m[address+y*8:address+(y+1)*8]
        vals = [n for b in raw for n in [b>>4,b&15]]
        assert all(n<8 for n in vals)
        for n in vals: counts[n] += 1
        lines.append(f'{y:2}  '+''.join(symbols[n] for n in vals))
    lines += ['Feldanzahlen: '+', '.join(f'{symbols[n]}={c}' for n,c in counts.items() if c)]
    if index:
        base = 0x37a0 + (index-1)*16
        positions = [(m[base+i],m[base+8+i]) for i in range(6)]
        lines += ['Feste Apfelslots 0..5 (interne x/y): '+str(positions)]
        if index in [1,4]: rule='Modus 2: alle Kirschen sammeln.'
        elif index in [2,5]: rule='Modus 4: alle Kirschen sammeln und sechs Äpfel auf die unterste Zeile bringen.'
        else: rule='Modus 6: Apfelblöcke in alle vier Ecken schieben; keine Schüsse/Schwerkraft.'
        lines += [rule, 'Alternativ führt das Beseitigen aller Gegner einschließlich Nachschub weiter.']
    lines += ['']
Path('analysis/levelkarten.txt').write_text('\n'.join(lines)+'\n')
print('Wrote analysis/levelkarten.txt')
