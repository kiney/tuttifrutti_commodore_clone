# Tutti Frutti – Commodore Plus/4 im Browser


Ein vollständig clientseitiger Klon des Commodore-16-/Plus/4-Spiels von Shaun
Southern. Alle sechs Karten, der Zeichensatz, Figurengrafiken und die
Melodiedaten stammen aus der im Repository enthaltenen `tuttifrutti.prg`.
Die gesamte Spieloberfläche ist auf Englisch, unabhängig von der Chatsprache.

## Spielen und lokal starten

Die fertige Website liegt in **[web/](web/)**. Es gibt keine externen
JavaScript-Bibliotheken, Fonts, Bilddienste, CDNs, Accounts oder Server-APIs.
Ein Build und `npm install` sind zum Spielen nicht erforderlich.

Aus dem Projektordner:

```sh
python3 -m http.server 8000 --directory web
```

Danach **http://localhost:8000** öffnen. Alternativ kann `web/index.html` direkt
im Browser geöffnet werden; die klassischen Scripts benötigen weder `fetch`
noch einen Modulserver. Ob der Browser lokale Highscores bei `file://`
dauerhaft speichert, hängt von dessen Einstellungen ab.

## Auf einem statischen Webspace hosten

Den **Inhalt** von `web/` in ein beliebiges Verzeichnis des Webspace kopieren.
`index.html` und die sieben anderen Dateien müssen nebeneinander liegen.
Relative Assetpfade erlauben auch Unterverzeichnisse wie `/spiele/tutti/`.
Es werden weder PHP noch Node.js, eine Datenbank, Rewrite-Regeln oder eine
Internetverbindung nach dem Laden der Dateien benötigt.

Optional ein fertiges Upload-Archiv erstellen:

```sh
python3 tools/package_web.py
```

Das erzeugt **`dist/tutti-frutti-web.zip`** (derzeit etwa 23 kB). Auf dem Webspace entpacken; die
Startdatei ist `index.html`. Die PRG, Analysewerkzeuge und Tests werden zum
Spielen nicht mit hochgeladen.

## Steuerung

| Aktion | Tastatur / Touch |
| --- | --- |
| Starten / neue Partie | Enter, Leertaste oder Startknopf |
| Bewegen | Pfeiltasten oder WASD; auf Touchgeräten Steuerkreuz |
| Schießen | Leertaste oder F; auf Touchgeräten Feuer |
| Schieben / Kirschblock zerbrechen | Feuer halten und in Richtung des Blocks steuern |
| Pause / weiter | P, Escape oder Pauseknopf |
| Ton an / aus | M oder Tonknopf |
| Vollbild | Vollbildknopf, sofern vom Browser unterstützt |

Audio startet erst nach einer Interaktion. Bei Fokusverlust oder Wechsel in
einen anderen Tab pausiert die Partie. Die Highscores der letzten besten acht
abgeschlossenen Partien und die Ton-Einstellung werden ausschließlich lokal
im Browser gespeichert. Blockierter Browserspeicher verhindert das Spielen
nicht. Eine Partie selbst wird nicht gespeichert.

## Spielumfang

- Fünf Leben, sechs wiederkehrende Originalkarten und steigendes Gegnertempo
  samt Nachschub über weitere Runden.
- Karten 1/4: alle Kirschen sammeln. Karten 2/5: zusätzlich sechs Äpfel auf die
  unterste Zeile bringen. Karten 3/6: vier Apfelblöcke in die vier Ecken schieben.
- Gegner durch bereits gegrabene Gänge, abprallender Schuss mit Rückkehr und
  Aufladezeit, fallende Äpfel und bis zum Hindernis rutschende Blöcke.
- Auch das Beseitigen aller Gegner samt Nachschub beendet eine Runde.
- Punkte, Bonus-Zeitlimit, Lebensverlust, Rundenwechsel, Game Over und Neustart.
- Canvas mit nativen 320 × 200 Pixeln und Original-Zeichengrafik, responsive
  Oberfläche, Touch-Eingabe einschließlich gleichzeitiger Richtung und Feuer.
- Original-Melodiefolge und lokal synthetisierte Geräusche über Web Audio.

Die Regeln wurden aus dem disassemblierten Programm rekonstruiert. Dies ist
kein 6502-/TED-Emulator: Palette und Klangerzeugung sind angenähert, nicht
zyklengenau. Der auffällige Stack-Pfad im ursprünglichen Falltimer wurde durch
eine reguläre Verzögerung ersetzt. Randkollisionen und das Zurücksetzen
beweglicher Objekte nach einem Lebensverlust werden im Klon stabilisiert.

## Quelltext und Prüfungen

| Datei | Aufgabe |
| --- | --- |
| `web/engine.js` | Spiellogik ohne Browserabhängigkeit; feste 50 Ticks/s |
| `web/renderer.js` | Zeichensatz, Figuren und Oberfläche im Canvas |
| `web/audio.js` | Zwei lokal synthetisierte Tonstimmen |
| `web/app.js` | Tastatur/Touch, DOM, Pause, Highscores und Animationsschleife |
| `web/assets.js` | Aus der PRG extrahierte Karten, Grafik- und Musikdaten |
| `tools/extract_web_assets.py` | Reproduzierbare Erzeugung der Asset-Datei |

Tests benötigen nur Node.js 18+; es müssen keine npm-Pakete installiert werden:

```sh
npm test
# gleichwertig:
node tests/engine.test.cjs
```

Die 14 Prüfungen umfassen den Abgleich mit den PRG-Daten, Spielerbewegung,
Punkte, Schuss, Gegner, Fallen und Schieben, alle drei Levelziele, Kartenzyklus,
Lebensverlust, Zeitlimit, komplette Laufwege durch beide Sammelkarten sowie
längere deterministische Partien mit allen sechs Karten.

`tests/browser-smoke.js` enthält zusätzlich eine im Browser ausführbare
Testfunktion. Dazu die Seite mit `?debug=1` öffnen und die Funktion aus der Datei
in den Browser-Entwicklerwerkzeugen aufrufen. Sie prüft echte DOM- und
Animationseingaben, Pause/Hilfe, gleichzeitige Touch-Eingaben, Highscores,
Neustart, Canvas und lokale Ressourcen. Geprüft in Chromium bei 1280 × 900,
390 × 844 und 320 × 740 Pixeln, direkt per `file://`, unter einem HTTP-
Unterverzeichnis aus dem entpackten ZIP sowie nach dem Laden ohne Netzwerk.
Vollbild und die normale Ansicht ohne Debugparameter wurden ebenfalls geprüft.
Der Debugzugriff und die manuelle
Zeitschaltung sind ohne diesen URL-Parameter nicht aktiviert.


## license
Original Tutti Frutti is from Mr. Chip published by Mastertronic.
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
