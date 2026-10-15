"""
Executive Summary
=================
Dies ist eine lesbare Rekonstruktion von tuttifrutti.prg, an Python angelehnt.
Die Spiellogik läuft in einem Raster-Interrupt. Es gibt sechs Karten, drei
wiederkehrende Regelvarianten, höchstens fünf gleichzeitig aktive Gegner,
einen abprallenden Schuss und zwei Arten beweglicher Blöcke.

LESEREIHENFOLGE
1. Datenmodell und Begriffe
2. start() -> bild_tick() -> spiele_einen_tick()
3. Bewegung, Karte, Schuss, Gegner, Blöcke
4. Levelziele, Punkte, Tod, Darstellung und Musik
5. Grenzen der Rekonstruktion

Das ist KEIN ausführbares Python-Spiel. Objekte wie `spiel`, `spieler`,
`karte`, `bildschirm` und `ton` stehen für zusammengefasste Speicherstellen.
Zuweisungen an diese Objekte bedeuten Änderungen des Originalzustands.
Benannte Zeichen-, Grafik- und Tonoperationen sind erklärende Abstraktionen.
Die Funktionsnamen sind von mir vergeben; Originalnamen sind nicht erhalten.

Quellenbasis: ausschließlich die konkrete PRG-Datei in diesem Repository.
SHA-256: 63ba58701faf770d0305214e5a0aed384e9c92b6fd8afa70377e7ed2645955e7
$1234 bedeutet eine hexadezimale ORIGINAL-SPEICHERADRESSE, keine Zeilennummer.
Die vollständiger nachverfolgbare Befehlsfolge steht in analysis/disassembly.txt.

Genauigkeit:
  BELEGT        = aus Befehlen, Zugriffen und Daten unmittelbar abgeleitet.
  VEREINFACHT   = gleiche Idee mit verständlicherer Datenstruktur beschrieben;
                 Randfälle des 8-Bit-Rechnens müssen nicht identisch sein.
  INTERPRETIERT = Bedeutung/Name aus Nutzung oder Grafik erschlossen.
  OFFEN         = auffälliger Ablauf, dessen reale Wirkung nicht geklärt ist.

Wichtige Vereinfachung: Das Original nutzt auch die Zeichen auf dem Bildschirm
als Zahlenspeicher! `spiel.punkte`, `spiel.leben`, `spiel.bonus` und die Uhr
sind hier lesbare Stellvertreter für diese Zeichen.
"""


# ---------------------------------------------------------------------------
# 1. DATENMODELL UND BEGRIFFE
# ---------------------------------------------------------------------------

BREITE = 16                         # Karte: 16 × 12 logische Felder
HOEHE = 12
EINHEITEN_PRO_FELD = 8              # Interne Bewegungseinheiten, NICHT Pixel.
# Ein Kartenfeld wird mit 2 × 2 Bildschirmzeichen dargestellt, also 16 × 16 Pixel.
# Eine interne Bewegungseinheit entspricht deshalb 2 Bildschirmpixeln.

LEER = 0
ERDE = 1
KIRSCHE = 2
APFEL = 3                          # Fester/fallender Apfel; blockiert Gehen.
KIRSCHBLOCK = 4                     # Schiebbar; bei Hindernis zerbrechbar.
APFELBLOCK = 5                      # Schiebbar; zerbricht nicht beim Schieben.
WAND_6 = 6                         # Feste Sperre, eigene Farbe.
WAND_7 = 7                         # Weitere feste Sperre; siehe Zielprüfung.
AUSSERHALB = 15                    # Rückgabe des Kartenlesers außerhalb.
# Die Bezeichnungen von 1, 3, 4, 5 sind aus Funktion und Zeichengrafik erschlossen.
# Insbesondere WAND_7 nicht unbelegt als "unsichtbare Wand" voraussetzen.

LINKS, RECHTS, OBEN, UNTEN = 0, 1, 2, 3
SCHRITT = {LINKS: (-1, 0), RECHTS: (1, 0), OBEN: (0, -1), UNTEN: (0, 1)}
GEGENRICHTUNG = {LINKS: RECHTS, RECHTS: LINKS, OBEN: UNTEN, UNTEN: OBEN}
RICHTUNGSBIT = {LINKS: 4, RECHTS: 8, OBEN: 1, UNTEN: 2}  # $3EF4, $3EF8, $3EFC

# Das Original kombiniert eine Richtungsnummer mit einem Stopp-Bit:
#   $00..$03: aktiv in diese Richtung laufen
#   $80..$83: stehen bleiben, aber Blickrichtung behalten
#   $FF:      Figur inaktiv
# Im Pseudocode trennen wir das in richtung, steht und aktiv.

# `spiel` bündelt:
#   modus             $E2: 0=Startbild; 1,3,5=Übergang; 2,4,6=Spiel; 7=Game Over
#                     Zusätzlich markiert Bit 7 ($80) den Todesablauf.
#   tick              $E7: laufender 8-Bit-Bildzähler, läuft nach 255 auf 0 über
#   uebergang         $E6: Warte-/Musikzähler beim Start und Levelwechsel
#   karten_index      $E5: 0..5, Auswahl einer der sechs Spielkarten
#   schwierigkeitsstufe $B6: wächst auch nach Wiederholung der Karten weiter
#   tod_pause $90: Countdown für Tod bzw. Game Over
#   punkte            fünf Ziffern in $0C4A..$0C4E
#   leben             eine Ziffer in $0DB6
#   bonus             drei Ziffern in $0D3A..$0D3C
#   levelnummer       zwei Ziffern in $0E2A..$0E2B
#   uhr               Zeichen in $0CC2..$0CC7, Teiltakt in $B5
#   nachschub         $8C: noch nicht eingeplante zusätzliche Gegner
#   gegner_tempo      $88: Zuwachs für einen 8-Bit-Taktakkumulator
#   gegner_takt       $87: dessen aktueller Wert
#   bonus_halbtakt    $B4: Bonus sinkt bei jedem zweiten Gegner-Bewegungstakt
#   zufallszustand    $89..$8B: drei Bytes
#   highscore_platz   $B7: 0..7 oder 8=noch kein Platz

# `spieler` ist Figur 0; Figuren 1..5 sind Gegner.
# `figuren` und `gegner` bezeichnen unten dieselbe nach Originalindex geordnete
# Tabelle; gegner[1:6] sind die fünf Gegner, Index 0 ist der Spieler.
# Speicher ist für acht Einträge reserviert, Zeichnung/KI benutzen sechs.
# Felder eines Figureneintrags:
#   x                 $0360 + figur_index
#   y                 $0368 + figur_index
#   richtung/steht    $0370 + figur_index
#   spawn_countdown   $04F0 + figur_index; $FF=kein Erscheinen eingeplant

# `objekte[0..7]` sind andere bewegliche Dinge, getrennt von den Figuren:
#   x                 $0340 + index
#   y                 $0348 + index
#   dx                $0350 + index
#   dy                $0358 + index
#   fall_wartezeit    $0338 + index
#   richtung/aktiv    $0378 + index; $FF=inaktiv
# Slots 0..5: sechs im Level platzierte Äpfel, die fallen können.
# Slot 7: genau ein gerade geschobener Block. Slot 6 hat keine klare Hauptrolle.

# `schuss` bündelt $6A..$71:
#   dx, dy            $6A, $6B
#   status            $6C: 0=bereit, $C0=fliegt, sonst Wiederauflade-Countdown
#   x, y              $6D, $6E
#   war_schon_weg     $71: hat das Ausgangsfeld des Spielers bereits verlassen?

# `zerbrechen` bündelt $65..$69: Restzeit, Bildadresse und Feldkoordinaten.
# `spiel.schiebe_art` ($64) ist 0 für Apfelblock oder $28 für Kirschblock-Grafik.
# `eingabe`: Richtungsbits 0..3 plus Feuer; Feuer ist im Original aktiv-low.
# `sfx`: Frequenz ($83), Frequenzänderung ($84), Dauer ($85), Kurztonpause ($86).


# ---------------------------------------------------------------------------
# 2. START UND HAUPTABLAUF
# ---------------------------------------------------------------------------

def basic_start():
    # BASIC-Zeile 1 in der vorliegenden Datei:
    if speicher[8192] == 120:        # 120 ist der Opcode SEI an Adresse $2000.
        start()                     # SYS 8192: läuft regulär nicht zurück.

    # Danach stehen noch BASIC-Zeilen eines älteren Titel-/Ladeablaufs:
    # Zeichensatz umkopieren ($1500), Mastertronic-Titel mit PRINT/COLOR,
    # Eingabe abfragen, LOAD "CODE",1,1 usw.
    # In DIESER Datei wird dieser Zweig wegen der ersten Zeile übersprungen.
    # Deshalb ist das keine zweite, in BASIC geschriebene Spiellogik.


def start():                        # $2000..$2085
    interrupts_sperren()
    grafikmodus_und_farben_einstellen()
    # Zeichen bei $3800; Bildzeichen bei $0C00; Farben bei $0800.
    raster_interrupt_einrichten(callback=bild_tick)
    interrupts_freigeben()

    baue_seitenleiste_und_rahmen()   # $2800
    setze_anzeigen_zurueck()         # $2900
    spiel.modus = 0
    musik.teiltakt = 255
    musik.position = 255
    musik.durchlaeufe = 0

    while True:                    # Tatsächlich $2080: FF19 lesen, zurückspringen.
        warte_auf_interrupt()


def bild_tick():                    # $20A0..$20ED
    if interrupt_ist_keiner_vom_raster():
        return_zum_betriebssystem()

    raster_interrupt_bestaetigen()
    spiel.tick = (spiel.tick + 1) % 256

    if spiel.modus == 0:
        startbild_tick()
    elif spiel.modus == 7:
        game_over_tick()
    elif spiel.modus >= 128:
        tod_tick()
    elif spiel.modus % 2 == 1:      # Modi 1, 3, 5
        uebergang_tick()
    else:                          # Modi 2, 4, 6
        spiele_einen_tick()

    return_zum_betriebssystem()


def startbild_tick():               # $2200; Musikroutine $2B00
    spiele_titelmusik()
    aktualisiere_startbild_animation()
    # Belegt: Je nach Musikposition wird Karte 0 bzw. eine Spielkarte gezeichnet.
    # Karte 0 ist ein Rahmenmuster, kein siebtes spielbares Level.
    # Außerdem werden Titel, Credits und "press fire to start" eingeblendet.

    eingabe = lese_eingabe()
    if eingabe.feuer:
        spiel.modus = 1
        spiel.uebergang = 96
        spiel.karten_index = -1     # Original: $FF, nächstes INC ergibt 0.
        spiel.schwierigkeitsstufe = -1
        spiel.levelnummer = 0
        spiel.uhr = "00:00"
        spiel.uhr_teiltakt = 0
        spiel.highscore_platz = 8
        setze_anzeigen_zurueck()    # Punkte=00000, Leben=5, weitere Anzeigen.
        lade_naechste_karte()



def setze_anzeigen_zurueck():        # $2900
    spiel.punkte = 0
    spiel.leben = 5
    spiel.levelnummer = 0
    spiel.bonus = 0
    spiel.uhr = "00:00"
    # Highscores werden dabei nicht gelöscht.


def aktualisiere_startbild_animation():  # $2203..$2231
    if musik.teiltakt != 0:
        return
    if musik.durchlaeufe % 2 == 1 and musik.position % 32 == 0:
        lade_und_zeichne_karte(musik.position // 32 + 1)
    elif musik.durchlaeufe % 2 == 0 and musik.position == 0:
        lade_und_zeichne_karte(0)
        zeichne_titel_credits_und_startaufforderung()  # $2A40


def uebergang_tick():               # $2300, $23D0
    if spiel.uebergang != 0:
        spiel.uebergang -= 1
        if spiel.uebergang == 128:
            lade_naechste_karte()
        elif spiel.uebergang > 128:
            spiele_levelwechsel_melodie(spiel.uebergang)
        return

    entferne_get_ready_einblendung()  # Gesicherten Bildbereich restaurieren.
    spiel.modus += 1                 # 1->2, 3->4, 5->6
    musik.teiltakt = 255
    musik.position = 255


def spiele_einen_tick():            # $237E..$23CC: tatsächliche Aufrufreihenfolge
    begleite_spiel_mit_musik()      # $1780, über eine Taste ein-/ausschaltbar
    entferne_alte_figuren()         # $30A0
    bewege_aktive_objekte()         # $3380
    bestimme_spielerrichtung()      # $2E2C
    bewege_spieler()                # $2E80
    raeume_felder_unter_spieler()   # $2F30: Erde löschen, Kirschen einsammeln
    pruefe_karten_ziel()            # $2BF0
    versuche_block_zu_schieben()    # $2CB3
    beende_schiebebewegung_wenn_noetig()  # $2400
    aktiviere_fallende_aepfel()     # $32BF
    zerbrechen_tick()              # $2470
    versuche_zu_schiessen()         # $2700
    bewege_schuss()                # $2740
    soundeffekt_tick()             # $2560
    gegner_bewegungstakt()         # $1C00, inklusive Spawn-Countdown und Bonus
    pruefe_treffer_an_gegnern()     # $1D30: Schuss und bewegliche Objekte
    plane_gegnernachschub()         # $1E00
    sammle_figuren_zum_zeichnen()   # $3000
    sammle_objekte_zum_zeichnen()   # $3200
    zeichne_gesammelte_zeichen()    # $30C0
    animiere_gegnerausgang()        # $1FA0
    pruefe_alle_gegner_beseitigt()  # $1E34
    pruefe_spieler_getroffen()     # $1E50
    aktualisiere_uhr()              # $1A38
    aktualisiere_highscore()        # $20FA
    # Zustandswechsel mitten im Tick stoppen die restlichen Aufrufe nicht.


# ---------------------------------------------------------------------------
# 3. KARTE UND LEVELDATEN
# ---------------------------------------------------------------------------

def feld(x, y):                     # $2F80, Grenzenprüfung $2F10; BELEGT/GEPRÜFT
    if not (0 <= x < 16 and 0 <= y < 12):
        return AUSSERHALB
    byte = speicher[0x0600 + y * 8 + x // 2]
    if x % 2 == 0:
        return byte >> 4
    return byte & 15


def setze_feld(x, y, typ):          # $2FB0; BELEGT/GEPRÜFT
    # Aufrufer müssen gültige Koordinaten liefern; Original prüft hier NICHT.
    adresse = 0x0600 + y * 8 + x // 2
    vorher = speicher[adresse]
    if x % 2 == 0:
        speicher[adresse] = (vorher & 15) | (typ << 4)
    else:
        speicher[adresse] = (vorher & 240) | (typ & 15)
    # Zwei Kartenfelder pro Byte: 192 Felder benötigen nur 96 Bytes RAM.


def lade_und_zeichne_karte(nummer):  # $2940, $2A00, $2E00
    quelle = 0x3500 + nummer * 96
    for y in range(12):
        for x in range(16):
            typ = entpacke_halbbyte(speicher, quelle, x, y)
            zeichne_kartenfeld(x, y, typ)
    kopiere_bytes(quelle, ziel=0x0600, anzahl=96)
    # Karte 0: Rahmen für das Startbild. Karten 1..6: spielbare Vorlagen.
    # Zeichnung: vier Grafikzeichen je Feld aus Tabellen $1880..$189F.
    # Farben: $18A0 und je nach Zeile/Modus $34D0..$34E7.


def lade_naechste_karte():          # $315F..$31F0
    spiel.karten_index += 1
    spiel.levelnummer = (spiel.levelnummer + 1) % 100
    spiel.schwierigkeitsstufe += 1
    schwierigkeit = min(spiel.schwierigkeitsstufe, 15)
    spiel.nachschub = [0, 1, 2, 3, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 7, 8][schwierigkeit]
    spiel.gegner_tempo = [120, 128, 136, 144, 152, 160, 168, 176,
                         180, 184, 188, 192, 196, 200, 204, 208][schwierigkeit]
    # Original hält den Stufenzähler als Byte; nach 256 Schritten läuft er über.

    if spiel.karten_index == 6:
        spiel.karten_index = 0
    lade_und_zeichne_karte(spiel.karten_index + 1)
    sichere_bildbereich_und_zeige_get_ready()  # $233A; Text aus $3EEC

    # Je Karte 16 Startpositionsbytes: acht x-Werte, danach acht y-Werte.
    for i in range(8):
        objekte[i].x = speicher[0x37A0 + spiel.karten_index * 16 + i]
        objekte[i].y = speicher[0x37A0 + spiel.karten_index * 16 + 8 + i]
    setze_figuren_und_effekte_zurueck()


def setze_figuren_und_effekte_zurueck():  # $3194; auch nach Lebensverlust benutzt
    for objekt in objekte:
        objekt.dx = objekt.dy = 0
        objekt.aktiv = False
    for figur in figuren:
        figur.x = figur.y = 0
        figur.aktiv = False
    spieler.x, spieler.y = 56, 8
    spieler.richtung = UNTEN
    spieler.steht = False
    spieler.aktiv = True

    ton.stumm()
    zerbrechen.restzeit = 0
    schuss.status = 0
    sfx.frequenz = sfx.aenderung = sfx.dauer = 0
    # Das Original setzt $86 (Kurztonpause) hier nicht ausdrücklich zurück.
    for i, zeit in enumerate([32, 48, 64, 80, 96], start=1):
        gegner[i].spawn_countdown = zeit
    # Diese fünf Gegner sind der Grundbestand; nachschub kommt zusätzlich.
    spiel.gegner_takt = 0
    spiel.bonus_halbtakt = 0
    spiel.bonus = {1: 599, 2: 599, 3: 799, 4: 799, 5: 999, 6: 999}[spiel.modus & 127]
    # Nur Figuren/Effekte werden zurückgesetzt. Die ausgegrabene Karte bleibt
    # bei Lebensverlust erhalten; feste Äpfel können daher erneut fallen.


# ---------------------------------------------------------------------------
# 4. EINGABE UND SPIELERBEWEGUNG
# ---------------------------------------------------------------------------

def lese_eingabe():                 # $3100..$315C
    # Original liest die Tastatur-/Joystickmatrix über $FD30 und $FF08.
    # Mehrere Scans werden zu vier Richtungsbits und Feuer zusammengeführt.
    # Hier nur das Ergebnis der Hardwareabfrage:
    return Eingabe(richtungsmaske=hardware_richtungen(), feuer=hardware_feuer())


def waehle_richtung(maske):         # $2600; BELEGT/GEPRÜFT
    # Bei gleichzeitig gedrückten Richtungen gilt diese feste Priorität.
    for richtung in [UNTEN, OBEN, RECHTS, LINKS]:
        if maske & RICHTUNGSBIT[richtung]:
            return richtung
    return None


def bestimme_spielerrichtung():     # $2E2C, $2648, $2634
    spiel.eingabe = lese_eingabe()
    gewuenscht = spiel.eingabe.richtungsmaske

    if spieler.x % 8 != 0 or spieler.y % 8 != 0:
        # Zwischen zwei Feldern nur entlang der aktuellen Achse bewegen.
        erlaubte_achse = 12 if spieler.x % 8 != 0 else 3
        auswahl = gewuenscht & erlaubte_achse
        if auswahl == 0:
            # Ohne passende Eingabe bis zur nächsten Feldgrenze weiterlaufen.
            auswahl = RICHTUNGSBIT[spieler.richtung] & erlaubte_achse
        spieler.richtung = waehle_richtung(auswahl)
        spieler.steht = False
        return

    erlaubt = freie_nachbarn(spieler.x // 8, spieler.y // 8, fuer_spieler=True)
    richtung = waehle_richtung(gewuenscht & erlaubt)
    if richtung is not None:
        spieler.richtung = richtung
        spieler.steht = False
    else:
        # Bei blockierter Richtung Blickrichtung merken, aber nicht laufen.
        richtung = waehle_richtung(gewuenscht)
        if richtung is not None:
            spieler.richtung = richtung
        spieler.steht = True


def freie_nachbarn(x, y, fuer_spieler):  # $2EA0 bzw. $1C80
    maske = 0
    for richtung, (dx, dy) in SCHRITT.items():
        typ = feld(x + dx, y + dy)
        if (typ < 3 if fuer_spieler else typ == LEER):
            maske |= RICHTUNGSBIT[richtung]
    return maske
    # Spieler: darf durch leere Felder, Erde und Kirschen.
    # Gegner: ausschließlich durch leere Felder; sie graben NICHT.
    # VEREINFACHT: Original hat zusätzliche einzelne Randvergleiche.
    # Beim oberen Rand vergleicht es seltsamerweise mit $10 statt $FF.
    # Der Kartenleser weist das entstehende y=$FF aber ohnehin zurück.


def bewege_spieler():               # $2E80
    if spiel.tick % 2 == 0 and not spieler.steht:
        dx, dy = SCHRITT[spieler.richtung]
        spieler.x += dx
        spieler.y += dy
    # Ein Kartenfeld braucht 8 solche Schritte, also regulär 16 Bild-Ticks.


def raeume_felder_unter_spieler():   # $2F30, $2530
    x, y = spieler.x // 8, spieler.y // 8
    betrete_feld(x, y)
    if (spieler.x % 8 != 0 or spieler.y % 8 != 0) and not spieler.steht:
        # Die Figur kann gerade zwei Kartenfelder überdecken.
        if spieler.richtung in [LINKS, RECHTS]:
            betrete_feld(x + 1, y)
        else:
            betrete_feld(x, y + 1)


def betrete_feld(x, y):             # $2530
    typ = feld(x, y)
    if typ == APFEL:
        return
    if typ == KIRSCHE:
        addiere_punkte(25)          # $1B00, im Original getrennt +20 und +5
        starte_sound(frequenz=240, aenderung=-20, dauer=8)
    setze_feld(x, y, LEER)
    # Kartenlogik und sichtbare Grafik sind getrennt: die Figurenzeichnung
    # und das anschließende Löschen alter Figuren schaffen sichtbare Gänge.


# ---------------------------------------------------------------------------
# 5. SCHUSS: ABPRALLEN, RÜCKKEHR UND WIEDERAUFLADEN
# ---------------------------------------------------------------------------

def versuche_zu_schiessen():        # $2700
    if not spiel.eingabe.feuer or schuss.status != 0 or spiel.modus == 6:
        return
    # Überraschend: Der Schuss fliegt immer diagonal, aus vier Tabellenwerten.
    schuss.dx, schuss.dy = {
        LINKS: (-2, 2), RECHTS: (2, -2), OBEN: (2, -2), UNTEN: (-2, 2)
    }[spieler.richtung]
    schuss.x = (spieler.x // 8) * 8 + 4
    schuss.y = (spieler.y // 8) * 8
    schuss.status = 192            # $C0: fliegt
    schuss.war_schon_weg = False


def bewege_schuss():                # $2740
    if schuss.status != 192:
        return
    loesche_schusszeichen_an_alter_position()

    if feld((schuss.x + schuss.dx) // 8, schuss.y // 8) != LEER:
        schuss.dx = -schuss.dx
        spiele_abprallton()
    if feld(schuss.x // 8, (schuss.y + schuss.dy) // 8) != LEER:
        schuss.dy = -schuss.dy
        spiele_abprallton()
    if feld((schuss.x + schuss.dx) // 8, (schuss.y + schuss.dy) // 8) != LEER:
        schuss.dx = -schuss.dx
        schuss.dy = -schuss.dy
        spiele_abprallton()

    schuss.x += schuss.dx
    schuss.y += schuss.dy
    zeichne_schusszeichen()        # Vier Zeichenversionen nach Unterposition.
    merke_schuss_bildadresse()      # $1BF5; zum Löschen bei Spielertod.

    if (schuss.x // 8, schuss.y // 8) == (spieler.x // 8, spieler.y // 8):
        if schuss.war_schon_weg:
            loesche_schusszeichen_an_alter_position()
            schuss.status = 0     # Wieder eingesammelt: sofort schussbereit.
    else:
        schuss.war_schon_weg = True


def schuss_trifft_gegner(gegner):   # Teil von $1D30
    gegner.aktiv = False
    addiere_punkte(100)             # $1B10
    starte_sound(frequenz=192, aenderung=63, dauer=32)
    loesche_schusszeichen_an_alter_position()
    schuss.status = 128 + (zufallsbyte() & 63)  # 128..191 Ticks Aufladezeit


def schuss_wiederaufladen():        # $1D98
    if schuss.status not in [0, 192]:
        schuss.status -= 1
        if schuss.status == 32:
            starte_sound(frequenz=16, aenderung=130, dauer=16)


# ---------------------------------------------------------------------------
# 6. GEGNER: ERSCHEINEN, TEMPO, ZUFÄLLIGE WEGE UND TREFFER
# ---------------------------------------------------------------------------

def gegner_bewegungstakt():         # $1C00
    summe = spiel.gegner_takt + spiel.gegner_tempo
    spiel.gegner_takt = summe % 256
    if summe < 256:
        return
    # Erst beim Überlauf werden Gegner, Erscheinen und Bonus weitergeschaltet.
    # Ein höherer Tempo-Wert bedeutet häufigere Bewegung.
    for g in gegner[5:0:-1]:
        if g.spawn_countdown != 255:
            if g.spawn_countdown == 0:
                g.x, g.y = 56, 48
                g.richtung = RECHTS
                g.aktiv = True
            g.spawn_countdown = (g.spawn_countdown - 1) % 256

    for g in gegner[5:0:-1]:
        if not g.aktiv:
            continue
        dx, dy = SCHRITT[g.richtung]
        g.x += dx
        g.y += dy
        if g.x % 8 == 0 and g.y % 8 == 0:
            waehle_gegnerweg(g)
            setze_feld(g.x // 8, g.y // 8, LEER)
    bonus_tick()


def waehle_gegnerweg(g):            # $1C80..$1D20
    frei = freie_nachbarn(g.x // 8, g.y // 8, fuer_spieler=False)
    rueckwaerts = GEGENRICHTUNG[g.richtung]
    ohne_umkehr = frei & ~RICHTUNGSBIT[rueckwaerts]
    if ohne_umkehr == 0:
        g.richtung = rueckwaerts   # Sackgasse: umkehren.
        return
    while True:
        kandidat = zufallsbyte() & 3
        if ohne_umkehr & RICHTUNGSBIT[kandidat]:
            g.richtung = kandidat
            return
    # Keine Distanz zum Spieler, kein Pfadfinder, kein "Verfolgen" im Code.


def zufallsbyte():                  # $1FE0; BELEGT/GEPRÜFT
    spiel.zufallszustand = (spiel.zufallszustand + 0xB13579) % (2 ** 24)
    return spiel.zufallszustand >> 16
    # Ein einfacher deterministischer 24-Bit-Zähler mit großem Additionsschritt.
    # Der Initialwert wird in den untersuchten Startfunktionen nicht gesetzt.


def plane_gegnernachschub():        # $1E00
    for g in gegner[5:0:-1]:
        if spiel.nachschub == 0:
            return
        if not g.aktiv and g.spawn_countdown == 255:
            spiel.nachschub -= 1
            g.x, g.y = 56, 48
            g.spawn_countdown = 64 + (zufallsbyte() & 63)


def abstand_wie_im_original(a, b):  # In $1D30 und $1E50 mehrfach vorhanden.
    # Nicht ganz abs(a-b): negative Differenzen werden bitweise invertiert.
    # Beispiel: -1 -> 0, -6 -> 5. Grenzfälle sind daher leicht asymmetrisch.
    differenz = (a - b) % 256
    return differenz ^ 255 if differenz & 128 else differenz


def nahe(a, b, grenze):
    return (abstand_wie_im_original(a.x, b.x) < grenze
            and abstand_wie_im_original(a.y, b.y) < grenze)


def pruefe_treffer_an_gegnern():     # $1D30..$1DFD
    if schuss.status == 192:
        for g in gegner[5:0:-1]:
            if g.aktiv and nahe(g, schuss, grenze=6):
                schuss_trifft_gegner(g)
                # Original bricht die Schleife hier nicht ausdrücklich ab.
    schuss_wiederaufladen()

    for objekt in reversed(objekte):
        if not objekt.aktiv:
            continue
        for g in gegner[5:0:-1]:
            if g.aktiv and nahe(g, objekt, grenze=6):
                g.aktiv = False
                addiere_punkte(100 if spiel.modus == 6 else 250)  # $1B20
                starte_sound(frequenz=128, aenderung=63, dauer=32)
    # Auch ein geschobener Block (Slot 7) kann Gegner treffen.


# ---------------------------------------------------------------------------
# 7. FALLENDE ÄPFEL UND SCHIEBBARE BLÖCKE
# ---------------------------------------------------------------------------

def aktiviere_fallende_aepfel():    # $32BF..$3327
    if spiel.modus == 6:
        return                     # Im Schieberätsel keine Schwerkraft.
    for objekt in objekte[5::-1]:   # Nur sechs feste Apfelpositionen.
        x, y_darunter = objekt.x // 8, objekt.y // 8 + 1
        if feld(x, y_darunter) == LEER and y_darunter < 12:
            objekt.dx, objekt.dy = 0, 1
            if not objekt.aktiv or objekt.richtung != UNTEN:
                objekt.fall_wartezeit = 32   # $3370
            objekt.aktiv = True
            objekt.richtung = UNTEN
        elif objekt.aktiv:
            objekt.aktiv = False
            setze_feld(objekt.x // 8, objekt.y // 8, APFEL)
            zeichne_festes_objekt(objekt.x // 8, objekt.y // 8, APFEL)
            sfx.dauer = 0


def bewege_aktive_objekte():        # $3380
    for objekt in reversed(objekte):
        if not objekt.aktiv:
            continue
        if objekt.fall_wartezeit != 0:
            fall_verzoegerung(objekt)
        else:
            objekt.x += objekt.dx
            objekt.y += objekt.dy


def fall_verzoegerung(objekt):      # $2C90; OFFEN: auffälliger Stack-Ablauf!
    objekt.fall_wartezeit -= 1
    if objekt.fall_wartezeit == 0:
        setze_feld(objekt.x // 8, objekt.y // 8, LEER)
        starte_sound(frequenz=208, aenderung=-2, dauer=255)

    # Die naheliegende Lesart ist: kurz warten, dann den Apfel fallen lassen.
    # ABER: Im tatsächlichen Binärcode springt BNE $2CAC bei Restzeit != 0 zu
    # zwei PLA-Befehlen. Die zugehörigen PHA liegen nur im ANDEREN Zweig.
    # Das verändert den Rücksprung-Stack. Eine normale Verzögerung ist dadurch
    # nicht für alle Aufrufe nachgewiesen. Hier steht die semantische Lesart;
    # der auffällige Kontrollfluss wird ausdrücklich NICHT als gelöst ausgegeben.
    # Siehe auch den Hinweis am Dateiende. Keine stillschweigende "Reparatur".


def versuche_block_zu_schieben():   # $2CB3..$2DC0
    if zerbrechen.restzeit != 0 or objekte[7].aktiv:
        return
    if spieler.x % 8 != 0 or spieler.y % 8 != 0 or not spiel.eingabe.feuer:
        return
    dx, dy = SCHRITT[spieler.richtung]
    x = spieler.x // 8 + dx
    y = spieler.y // 8 + dy
    blocktyp = feld(x, y)
    if blocktyp < 3:
        return
    dahinter = feld(x + dx, y + dy)

    if blocktyp in [KIRSCHBLOCK, APFELBLOCK] and dahinter == LEER:
        spiel.schiebe_art = 40 if blocktyp == KIRSCHBLOCK else 0
        block = objekte[7]
        block.x, block.y = x * 8, y * 8
        block.dx, block.dy = dx, dy
        block.richtung = spieler.richtung
        block.aktiv = True
        setze_feld(x, y, LEER)
    elif blocktyp == KIRSCHBLOCK and dahinter != LEER:
        # Gegen ein Hindernis gedrückt: Kirschblock zerbricht statt zu rutschen.
        zeichne_festes_objekt(x, y, KIRSCHBLOCK)
        zerbrechen.x, zerbrechen.y = x, y
        zerbrechen.restzeit = 32
        starte_sound(frequenz=16, aenderung=32, dauer=6)
        addiere_punkte(25)
    # APFEL, WAND_6, WAND_7 und blockierter APFELBLOCK bleiben unverändert.
    # In normalen Leveln kann dieselbe Feuer-Eingabe auch einen Schuss auslösen.


def beende_schiebebewegung_wenn_noetig():  # $2400
    block = objekte[7]
    if not block.aktiv or block.x % 8 != 0 or block.y % 8 != 0:
        return
    x, y = block.x // 8, block.y // 8
    if feld(x + block.dx, y + block.dy) == LEER:
        return                     # Rutscht weiter, bis ein Hindernis kommt.
    block.aktiv = False
    block.dx = block.dy = 0
    typ = APFELBLOCK if spiel.schiebe_art == 0 else KIRSCHBLOCK
    setze_feld(x, y, typ)
    zeichne_festes_objekt(x, y, typ)
    spiele_abprallton()


def zerbrechen_tick():              # $2470
    if zerbrechen.restzeit == 0:
        return
    zerbrechen.restzeit -= 1
    if zerbrechen.restzeit == 0:
        setze_feld(zerbrechen.x, zerbrechen.y, LEER)
        loesche_die_vier_bildzeichen_des_blocks()
    elif zerbrechen.restzeit % 8 == 7:
        phase = 3 - zerbrechen.restzeit // 8
        zeichne_zerbrechphase(phase)  # Zeichen $30..$3F, vier Phasen.


# ---------------------------------------------------------------------------
# 8. LEVELZIELE UND WECHSEL
# ---------------------------------------------------------------------------

def pruefe_karten_ziel():           # $2BF0..$2C8E
    if spieler.x % 8 != 0 or spieler.y % 8 != 0:
        return                     # Ziele nur an Feldgrenzen prüfen.

    if spiel.modus == 2:
        fertig = keine_kirschen_mehr()
    elif spiel.modus == 4:
        # Es zählen wirklich sechs Äpfel auf der UNTERSTEN Kartenzeile.
        # Die genaue Bitmaske akzeptiert auch Typ 7; im regulären Sammellevel
        # entsteht das Ziel durch die sechs fallenden Äpfel (Typ 3).
        fertig = (keine_kirschen_mehr()
                  and sum((feld(x, 11) & 3) == 3 for x in range(16)) == 6)
    elif spiel.modus == 6:
        # Exakte Originalprüfung: bitweises UND der vier Eckfelder.
        # Die beabsichtigte Bedeutung ist: vier Apfelblöcke in den Ecken.
        # Typ 7 würde dieses UND zusammen mit Typ 5 ebenfalls bestehen.
        fertig = (feld(0, 0) & feld(0, 11) & feld(15, 0) & feld(15, 11)) == 5
    else:
        return

    if fertig:
        runde_mit_kartenziel_beenden()


def keine_kirschen_mehr():          # Original scannt alle 96 Bytes halbbyteweise.
    return all(feld(x, y) != KIRSCHE for y in range(12) for x in range(16))


def pruefe_alle_gegner_beseitigt():  # $1E34
    if spiel.nachschub == 0 and all(
        not g.aktiv and g.spawn_countdown == 255 for g in gegner[1:6]
    ):
        starte_levelwechsel()
    # Zweiter Weg zum nächsten Level! Keine Kirschen-/Eckprüfung nötig.
    # Hier wird nur der Restbonus gutgeschrieben, nicht der zusätzliche
    # Kartenziel-Bonus aus runde_mit_kartenziel_beenden().


def runde_mit_kartenziel_beenden():  # $1AA8
    starte_levelwechsel()
    zusatz = spiel.karten_index + 1
    if zusatz >= 4:
        zusatz -= 3
    addiere_punkte(zusatz * 1000)   # Also 1000, 2000, 3000, dann Wiederholung.


def starte_levelwechsel():         # $2C60 + $1A84
    spiel.uebergang = 224
    spiel.modus += 1               # 2->3, 4->5, 6->1
    if spiel.modus == 7:
        spiel.modus = 1
    addiere_punkte(spiel.bonus)    # Noch vorhandenen Bonus sofort gutschreiben.
    # Im Übergang wird bei Countdown 128 die nächste Karte geladen.
    # Die sechs Karten wiederholen sich, Gegner-Tempo/Nachschub steigen weiter.


# ---------------------------------------------------------------------------
# 9. PUNKTE, BONUS, UHR UND HIGHSCORE
# ---------------------------------------------------------------------------

def addiere_punkte(anzahl):         # $1AC0
    spiel.punkte = (spiel.punkte + anzahl) % 100000
    # Im Original: Ziffernzeichen direkt im Bildschirm-RAM addieren.
    # Zeichen $1C..$25 entsprechen 0..9. Ab $26 Übertrag nach links.
    # Es gibt hier keinen belegten Extraleben-Mechanismus.


def bonus_tick():                   # $1A00
    spiel.bonus_halbtakt ^= 1
    if spiel.bonus_halbtakt != 0:
        return
    spiel.bonus = (spiel.bonus - 1) % 1000
    if spiel.bonus == 0:
        starte_tod()
    # Bonus ist zugleich ein Zeitlimit. Sein Tempo hängt am Gegner-Takt.


def aktualisiere_uhr():             # $1A38
    spiel.uhr_teiltakt += 1
    if spiel.uhr_teiltakt == 60:
        spiel.uhr_teiltakt = 0
        spiel.uhr = erhoehe_mm_ss_anzeige(spiel.uhr)
    # Das Original zählt 60 Spiel-Ticks pro angezeigter Sekunde.
    # Das muss auf PAL nicht einer realen Sekunde entsprechen.
    # Die Minuten-Zehnerstelle läuft schon nach 5 wieder auf 0: Zyklus 60 min.
    # Während Übergängen, Todesablauf und Startbild steht diese Uhr still.


def aktualisiere_highscore():       # $20FA..$21BE
    # Acht Einträge, nur fünfstellige Punktzahlen, keine Namenseingabe.
    # Die Tabelle liegt direkt in der rechten Bildschirmspalte.
    # Eine laufende Partie kann sich schon während des Spielens einsortieren.
    platz = spiel.highscore_platz
    while platz > 0 and spiel.punkte > highscore[platz - 1]:
        if platz < 8:
            highscore[platz] = highscore[platz - 1]
        platz -= 1
    spiel.highscore_platz = platz
    if platz < 8:
        highscore[platz] = spiel.punkte
        markiere_eigenen_eintrag_mit_wechselnder_farbe(spiel.tick)
    # VEREINFACHT: Original vergleicht und verschiebt die Ziffern einzeln.
    # Tabelleninhalt bleibt zwischen Partien im RAM; kein Speichern auf Disk.


# ---------------------------------------------------------------------------
# 10. SPIELERTOD UND GAME OVER
# ---------------------------------------------------------------------------

def pruefe_spieler_getroffen():     # $1E50..$1EC0
    for objekt in objekte[5::-1]:
        if objekt.aktiv and nahe(objekt, spieler, grenze=4):
            starte_tod()
            return
    for g in gegner[5:0:-1]:
        if g.aktiv and nahe(g, spieler, grenze=4):
            starte_tod()
            return
    # Geschobener Block in Slot 7 ist in dieser Spielerprüfung nicht enthalten.


def starte_tod():                   # $1BDC sowie die Aufrufer
    spiel.modus |= 128
    spiel.tod_pause = 192
    if schuss.status == 192:
        loesche_schusszeichen_an_alter_position()
    # In $1BDC gibt es noch einen Vergleich mit Modus 6, nachdem Bit 7 bereits
    # gesetzt wurde; der Vergleich kann dann nicht mehr zutreffen.


def tod_tick():                     # $1F00
    if spiel.tod_pause != 0:
        spiel.tod_pause -= 1
        spiele_todeseffekt_falls_noetig(spiel.tod_pause)
        return
    spiel.leben -= 1
    if spiel.leben == 0:
        spiel.modus = 7
        spiel.tod_pause = 192
    else:
        setze_figuren_und_effekte_zurueck()
        spiel.modus &= 127
    # Erhalten bleiben u.a.: Karte, Punkte, Levelnummer, Uhr, Nachschubbudget.
    # Der Bonus und die fünf regulären Spawn-Zähler werden neu initialisiert.


def game_over_tick():               # $1B40
    if spiel.tod_pause == 0:
        spiel.modus = 0
        musik.teiltakt = musik.position = 255
        musik.durchlaeufe = 0
        return
    spiel.tod_pause -= 1
    if spiel.tod_pause == 160:
        zeichne_game_over_text()    # Daten $34A0, Bildbereich um $0D48.
    spiele_game_over_melodie_falls_noetig(spiel.tod_pause)
    # VEREINFACHT: Original setzt hier beim Rückweg auch den CPU-Stack zurück
    # und springt direkt in die Startbild-Initialisierung bei $204A.


# ---------------------------------------------------------------------------
# 11. DARSTELLUNG: ZEICHENGRAFIK STATT HARDWARE-SPRITES
# ---------------------------------------------------------------------------

def entferne_alte_figuren():        # $30A0
    for eintrag in zeichnen.alte_eintraege:
        bildschirm[eintrag.adresse] = LEERES_ZEICHEN
    zeichnen.neue_eintraege = []
    # Keine vollständige Bildschirm-Neuzeichnung und kein Hintergrund-Backup
    # für jede Figur. Gelöschte Figurzeichen hinterlassen leeren Boden.


def sammle_figuren_zum_zeichnen():  # $3000, $3090; VEREINFACHT
    for figur in reversed(figuren[0:6]):
        if not figur.aktiv:
            continue
        zelle_x, zelle_y = figur.x // 4, figur.y // 4
        # Je nach Richtung und Unterposition unterschiedliche Zeichengruppen.
        # Links/rechts haben getrennte Bilder; oben/unten teilen sich Bilder.
        phase = unterposition_fuer_animation(figur)
        grafik = figuren_grafiktabelle[figur.richtung, phase]
        if figur is not spieler:
            grafik = verschiebe_zeichennummern(grafik, um=30)
        fuege_grafik_zur_zeichenliste(grafik, zelle_x, zelle_y, farbe=0x79)
    # Adresstabellen $1850/$1868 vermeiden Multiplikation mit 40 pro Zeile.
    # Eigentliche Grafiktabellen: $3E80..$3EC7.


def sammle_objekte_zum_zeichnen():  # $3200, $3290, $32A2; VEREINFACHT
    for i, objekt in reversed(list(enumerate(objekte))):
        if not objekt.aktiv:
            continue
        grafik = objekt_grafiktabelle[objekt.richtung, unterposition(objekt)]
        if i == 7:
            grafik = verschiebe_zeichennummern(grafik, um=spiel.schiebe_art)
        farbe = 0x5A if spiel.modus == 6 else 0x08
        fuege_grafik_zur_zeichenliste(grafik, objekt.x // 4, objekt.y // 4, farbe)
    # Tabellen $3400..$3467; Einträge für glattes Verschieben über Zeichengrenzen.


def zeichne_gesammelte_zeichen():   # $30C0
    for eintrag in zeichnen.neue_eintraege:
        bildschirm[eintrag.adresse] = eintrag.zeichen
        farbspeicher[eintrag.adresse - 0x0400] = eintrag.farbe
    zeichnen.alte_eintraege = zeichnen.neue_eintraege
    # Original hält getrennte Arrays: Adress-Low $0380, -High $03D0,
    # Zeichen $0420, Farbe $0470. Hier ein lesbarer Eintrag pro Zeichen.


def zeichne_festes_objekt(x, y, typ):  # $33AC/$33B0, $2500
    erster_code = 0x40 if typ in [APFEL, APFELBLOCK] else 0x68
    zeichne_2x2_zeichen(x * 2, y * 2, [erster_code + i for i in range(4)])
    fuelle_2x2_farben(x * 2, y * 2, 0x5A if spiel.modus == 6 else 0x08)


def animiere_gegnerausgang():       # $1FA0
    zeichne_2x2_zeichen(14, 12, [0x1B] * 4)
    grundfarbe = 0x0E if any(g.spawn_countdown < 50 for g in gegner[1:6]) else 0x0A
    fuelle_2x2_farben(14, 12, grundfarbe | ((spiel.tick & 7) << 4))
    # INTERPRETIERT: Das farblich animierte Quadrat ist der Gegnerausgang.
    # Die Spawnposition der Gegner liegt genau bei x=56,y=48.


# ---------------------------------------------------------------------------
# 12. MUSIK UND SOUNDEFFEKTE
# ---------------------------------------------------------------------------

def spiele_titelmusik():            # $2B00; VEREINFACHT
    musik.teiltakt = (musik.teiltakt + 1) % 256
    if musik.teiltakt == 8:
        musik.teiltakt = 0
        musik.position = (musik.position + 1) % 256
        if musik.position == 192:
            musik.position = 0
            musik.durchlaeufe += 1
        notenpaar = speicher[0x3F00 + musik.position]
        stimme_1, stimme_2 = notenpaar >> 4, notenpaar & 15
        if stimme_1 != 1:          # Wert 1 hält die vorige Frequenz.
            ton.setze_stimme_1(nachschlagen_frequenz_1(stimme_1))
        ton.setze_stimme_2(nachschlagen_frequenz_2(stimme_2))
        ton.aktiviere_beide_stimmen()
    elif musik.teiltakt == 7:
        # Kurze Unterbrechung zwischen aufeinanderfolgenden Noten.
        schalte_stimmen_vor_naechster_note_passend_ab()
    # Zwei Noten in einem Byte, 192 Schritte, Notentabellen $3FC0..$3FFF.
    # Achtung: Tabellenzugriff $3FF0+15 liegt ein Byte außerhalb der Datei.
    # Ob dieser Eintrag tatsächlich benötigt wird, ist damit nicht gesagt.
    # Die Datei lädt nur bis einschließlich $3FFE.


def begleite_spiel_mit_musik():      # $1780..$17F2
    if musik_taste_ist_nicht_aktiv():
        ton.stimme_1_aus()
        return
    # Ähnliche 8-Tick-Sequenz wie im Titel, aber nur die obere Notenhälfte.
    # Die zweite Stimme bleibt für kurze Spielgeräusche verfügbar.
    spiele_naechsten_schritt_der_ersten_stimme()


def starte_sound(frequenz, aenderung, dauer):
    sfx.frequenz = frequenz % 256
    sfx.aenderung = aenderung % 256
    sfx.dauer = dauer


def soundeffekt_tick():             # $2560, $25A0
    if sfx.kurztonpause != 0:
        sfx.kurztonpause -= 1
        return
    if sfx.dauer == 0:
        ton.stimme_2_aus()
        return
    sfx.frequenz = (sfx.frequenz + sfx.aenderung) % 256
    ton.setze_stimme_2(sfx.frequenz, obere_bits=3)
    ton.stimme_2_an()
    sfx.dauer -= 1


def spiele_abprallton():            # $25E0 bzw. $25F8
    ton.setze_stimme_2(240, obere_bits=3)
    ton.stimme_2_an()
    sfx.kurztonpause = 1
    # Objekt-Aufprall benutzt eine Variante mit oberen Frequenzbits=0.


# ---------------------------------------------------------------------------
# 13. WAS DIESE REKONSTRUKTION LEISTET UND WO SIE ENDET
# ---------------------------------------------------------------------------
# Belegt und in isolierten ORIGINAL-Maschinencode-Routinen überprüft:
#   - Kartenformat, alle 1152 Spielfelder und Lesen außerhalb der Karte
#   - Schreiben eines Feldes ohne Änderung seines Nachbar-Halbbytes
#   - Richtungsnummern und Priorität gleichzeitiger Eingaben
#   - 25/100/250 Punkte und dezimaler Übertrag bis zum fünfstelligen Überlauf
#   - 24-Bit-Zufallsfortschaltung und Laden aller sechs Karten
#   - Anfangszustände aller sechs Karten und alle drei Kartenzielprüfungen
#   - Auffälliger Rücksprung beim Falltimer, isoliert mit Restzeit 2
# Prüfwerkzeug: python3 tools/verify_analysis.py
#
# Aus statischer Analyse abgeleitet, aber NICHT im vollständigen Emulatorlauf
# bestätigt: Interrupt-Zeitverhalten, Darstellung, Hardwareeingabe, Sound,
# Fallverzögerung, alle Wechselwirkungen über ganze Partien.
#
# Besonders offen: der unausgeglichene Stack-Pfad bei $2C90. Die vorliegende
# Datei enthält zudem zahlreiche NOP-Blöcke. Ob und welche davon auf spätere
# Änderungen zurückgehen, lässt sich ohne Vergleichsdatei nicht beweisen.
# Diese Datei ist daher eine Rekonstruktion DIESER PRG, keine Behauptung über
# den wortgetreuen ursprünglichen Quelltext von Shaun Southern.
#
# Bewusst abstrahiert:
#   Hardware-Registerwerte, Zeichenlisten-Details und Melodien stehen hinter
#   sprechenden Hilfsoperationen. Die Spiellogik oben ist weiter ausgearbeitet.
#   Byte-Überläufe sind nur dort ausdrücklich dargestellt, wo sie besonders
#   wichtig sind; Koordinaten/Index-Randfälle können vom Original abweichen.
#
# Extrahierte Karten samt fester Apfelpositionen: analysis/levelkarten.txt.
# Nachvollziehbare 6502-Befehle: analysis/disassembly.txt.
