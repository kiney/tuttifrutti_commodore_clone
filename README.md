# Reverse engineering and recreation project of the classic commodore plus/4 game Tutti Frutti

## license
Original Tutti Frutti is from Mr. Chip published by Matertronic.
According to this interview with an ex Mastertronic executive those games are now basically free:
https://www.lemon64.com/page/anthony-guter-interview


## Lesbare Rekonstruktion

[pseudocode.py](pseudocode.py) erklärt das Programm auf Deutsch in Python-artigem
Pseudocode. Es ist zum Lesen gedacht und kein ausführbares Remake. Einstieg:
Datenmodell, `start()`, `bild_tick()` und `spiele_einen_tick()`. Originaladressen
und offene Fragen stehen jeweils dabei.

- [Extrahierte Levelkarten](analysis/levelkarten.txt)
- [Nachverfolgte 6502-Befehle](analysis/disassembly.txt), als technische Referenz

Die Analysewerkzeuge benötigen nur Python 3 und werden aus dem Projektordner
aufgerufen:

```sh
python3 tools/extract_levels.py
python3 tools/trace_code.py
python3 tools/verify_analysis.py
```

Die Prüfungen führen ausgewählte Routinen aus der Originaldatei mit einem
kleinen CPU-Runner aus. Sie ersetzen keinen vollständigen Plus/4-Emulatorlauf.
Ein auffälliger Stack-Pfad im Falltimer ist im Pseudocode ausdrücklich markiert.
