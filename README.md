# misterpfister.net

Digitaler Werkplatz von Kilian Pfister: [Startseite](https://misterpfister.net/),
[Notenrechner](https://misterpfister.net/sechserrechner/),
[Schlafrechner](https://misterpfister.net/sleepcalculator/) und die Seite zur App
[Wisperpfister](https://misterpfister.net/wisperpfister/).

Statisches HTML, CSS und JavaScript. Keine Laufzeitpakete, externen Schriftdateien,
Konten oder Tracking-Skripte. GitHub Pages veröffentlicht `main` aus dem Repository-
Root. `CNAME` und die drei bestehenden URLs bleiben erhalten.

## Funktionen

- Startseite «Werkplatz 5 · Liquid Glass Lab»: Ein selbst geschriebenes
  WebGL-Glasobjekt (Raymarching, kein Framework) morpht zwischen Notenskala,
  24-Stunden-Ring und Datenwürfel. Es reagiert auf Zeiger, Scrollen, Auswahl und
  Klick und hört danach ganz auf zu rendern. Im hellen Farbschema wird es zu
  Porzellan mit irisierender Glasur. Auf Handys läuft es als schmales Band, das
  beim Scrollen die drei Formen durchläuft. Auswahlknöpfe und horizontales
  Wischen halten die gewählte Form fest; vertikales Scrollen bleibt möglich.
- Kleine Demos im Hero: Eine fiktive nächste Note verändert Schnitt und
  Glas-Skala, eine Schlafdauer verändert Bettzeit und Ring. «Look anpassen»
  öffnet Material-, Farb- und Lichtregler direkt in der Vorschau. Diese Werte
  bleiben in der Sitzung und berühren keine gespeicherten Rechnerdaten.
- Drei Darstellungsstufen: `live` (Animation mit Grafikkarte), `still` (ein
  einzelnes gerendertes Standbild bei Software-Rendering, `saveData`, wenigen
  CPU-Kernen oder Reduced Motion) und `fallback` (statisches SVG, wenn WebGL
  fehlt, bei Forced Colors oder wenn das Skript nicht startet; nach 4 s greift
  ein reiner CSS-Failsafe). Ohne JavaScript bleiben alle Texte lesbar; die
  Rechner zeigen dann einen Hinweis.
- Räumliche Werkzeugkarten als «Museumsschilder» ab Tablet-Breite: Das vordere
  Schild öffnet sein Tool, die anderen kommen zuerst nach vorne. Bedienbar ist die
  Auswahl über das Dock (Pfeiltasten, Home/End) und per Touch; das HUD nennt Kanal
  und Beispielwerte. Auf Handys bleibt die Auswahl neben dem kompakten Glasband.
  Die direkten Toollinks funktionieren unabhängig von der Szene.
- Native Cross-Document View Transitions verbinden Karte oder Schild mit dem
  Ergebnis des Rechners und das Glasobjekt mit dem Tool-Symbol. Das Farbschema
  wechselt mit einer Kreisblende. Bei fehlender Unterstützung oder Reduced Motion
  bleiben es normale Links und ein sofortiger Wechsel.
- Noten: gewichteter Schnitt, Anzeige-Rundung, Simulation und Zielplanung mit dem
  Gewicht der nächsten Note (Schnellwahl 0.5 / 1 / 2), Fächer mit Übersicht und
  Gesamtschnitt, Prüfungsnamen, Eingabe per Enter, lokale Entwürfe, Undo,
  JSON-Export/Import und lineare Punkteumrechnung inklusive nötiger Punkte für
  eine Wunschnote. Das Ergebnis ist ein 270°-Instrument mit Punkt (aktuell),
  Ring (Simulation), Dreieck (Ziel) und gestrichelter Marke bei 4.0, dazu ein
  Balkendiagramm (Breite = Gewicht, Höhe = Note), ein Differenz-Chip (▲/▼/=) und
  Antwortkarten mit Symbolen. Ein leerer Rechner bietet das vorhandene Beispiel
  direkt im Ergebnis an. Ab 901 px bleibt das Ergebnis beim Scrollen
  sichtbar, sofern es in die Fensterhöhe passt; auf schmaleren Bildschirmen
  erscheint eine kompakte Ergebnisleiste.
- Schlaf: 24-Stunden-Uhr, frei wählbare Bett-/Aufstehzeit (07:00, 7.00, 700 oder
  7), minutengenaue Dauer mit Schnellwahl 7–9 h, Einschlafzeit (Standard 10 min),
  «Jetzt ins Bett», eigene Presets mit Undo und lokale Speicherung. Die beiden
  Griffe am Zifferblatt lassen sich ziehen, antippen oder per Tastatur bewegen
  (Pfeile ±5 min, mit Shift ±1 min, Bild auf/ab ±60 min, Home/End). Der
  Anker-Griff setzt die Zeit, der End-Griff die Dauer (1–16 h). Die Eingabefelder
  bleiben die einzige Quelle; gespeichert wird einmal pro Zug. Ab 901 px (und
  mindestens 720 px Fensterhöhe) bleibt das Zifferblatt beim Scrollen sichtbar;
  bis 900 px erscheint stattdessen eine kompakte Ergebnisleiste.
- SpasstoCSV: animierter Weg vom Export über drei Feldzuordnungen zur CSV-/JSON-
  Vorschau mit erfundenen Daten und Verweis auf das
  [lokale Python-Projekt](https://github.com/misterpfister8/spasstocsv).
  Unterstützte Formate laut dessen öffentlicher README: Raw-, Chrome- und
  Proton-CSV sowie Bitwarden JSON. Die Website nimmt keine Passwortdateien an.

- Wisperpfister (`/wisperpfister/`): Kurzvorstellung der Diktier-App für Mac
  und iPhone (Beta), verlinkt über einen Teaser auf der Startseite. Ein
  endliches Beispiel zeigt Halten, Sprechen und Loslassen und die Bereinigung
  («ähm der Termin ist am Dienstag, äh, nein, am Mittwoch» → «Der Termin ist am
  Mittwoch.», ein Regressionsfall der App). Die Mac/iPhone-Auswahl funktioniert
  ohne JavaScript; Reduced Motion zeigt sofort das Ergebnis. Beta-Anfragen per
  E-Mail an die Projektadresse. Die Datenschutzsätze fassen den freigegebenen
  Wortlaut der App zusammen; eine Datenschutzerklärung ist hier nicht
  veröffentlicht.

## Rechenregeln und Datensicherung

Noten liegen zwischen 1 und 6, Gewichte zwischen 0.01 und 100; maximal zwei
Dezimalstellen, mit Punkt oder Komma. Höchstens 30 Fächer mit je 100 Zeilen.
Die Anzeige wird kaufmännisch auf 0.01, 0.1, 0.5 oder 1 gerundet. Der zusätzlich
angezeigte Rechenwert ist auf vier Dezimalstellen angenähert. Die Zielplanung
vergleicht intern ganzzahlige Kreuzprodukte; sie sucht die kleinste erreichbare
Note in Schritten von 0.01, 0.1, 0.25, 0.5 oder 1. Historische Noten bleiben
unverändert. Die Markierung bei 4 ist keine allgemeine Bestehensgarantie. Der
Gesamtschnitt der Fächerübersicht ist das Mittel der gerundeten Fachschnitte
(jeweils mit der Rundung des Fachs), angezeigt auf 0.01. Ältere Sicherungen mit
separatem Simulationsgewicht bleiben importierbar; es wird ignoriert.

Schlafdauer: 1–16 Stunden; Einschlafdauer: 0–180 ganze Minuten. Uhrzeiten ohne
Datum, Alarm oder medizinisches Zyklusmodell. Zeitumstellungen werden nicht
berücksichtigt. Die Punkteformel ist linear, keine universelle Schulregel;
Maximum grösser null und höchstens 1 000 000, Notenskala innerhalb von 1–6. Nötige
Punkte für eine Wunschnote sind ein Mindestwert ohne Aufrundung.

Die Speicherung ist für beide Tools einzeln abschaltbar. Abschalten entfernt
nur deren gespeicherte Daten, die Sitzung bleibt benutzbar. Notenentwürfe werden
auch mit unvollständigen Eingaben bewahrt; beim Schlafrechner bleiben die letzten
gültigen Zeiten erhalten. Unlesbare Sicherungen werden nicht automatisch
überschrieben. Speicherfehler werden angezeigt. Browserdaten sind kein dauerhaftes
Backup: wichtige Noten als JSON exportieren. Importdateien werden auf Grösse
(maximal 512 KiB), Schema, Typen und Werte geprüft. Ersetzen erfordert Bestätigung
und lässt sich rückgängig machen. Auch verzögertes Undo überschreibt neuere
Noteneingaben nur nach ausdrücklicher Bestätigung.

## Lokal starten und testen

```bash
python3 -m http.server 8000 --bind 127.0.0.1
```

Danach [localhost:8000](http://127.0.0.1:8000/) öffnen. Kein Build nötig.

```bash
python3 -m venv .venv
.venv/bin/pip install -r tests/requirements.txt
.venv/bin/playwright install chromium webkit
node tests/math.test.js
.venv/bin/python tests/browser_review.py
.venv/bin/python tests/browser_review.py --browser webkit --output output/playwright/webkit
.venv/bin/python tests/persistence_review.py
.venv/bin/python tests/persistence_review.py --browser webkit
.venv/bin/python tests/interaction_review.py --headed
.venv/bin/python tests/interaction_review.py --axe /pfad/zu/axe.min.js
.venv/bin/python tests/contrast_review.py
.venv/bin/python tests/showcase_review.py
```

Alle Browserprüfungen akzeptieren `--base-url`, falls der Server nicht auf Port
8000 läuft (zum Beispiel `--base-url http://127.0.0.1:8810/`).

Die Browserprüfungen benötigen den laufenden HTTP-Server. Sie laden die echten
externen Dateien und verwenden nativen Browser-Speicher. `browser_review.py`
prüft zusätzlich, dass keine Anfrage die eigene Origin verlässt, alle Assets
den Cache-Parameter `?v=werkplatz-5-demo1` tragen, Chromium jede Deklaration, jeden
Selektor und jede Media-Bedingung der Stylesheets annimmt (ausgenommen bewusst
browserübergreifende Regeln), jeder Tab-Stopp sichtbar ist und die
Einblendung der Startseite keinen Text anschneidet. Speicherfehler-Injektion
ist ein separater Testfall. `persistence_review.py` prüft echte Browser-Neustarts
und in Chromium zusätzlich nativ deaktivierten Speicher. `interaction_review.py`
prüft Touch (inklusive Ziehen am Zifferblatt), das Einschwingen der Szene, die
Stufen des Glasobjekts, gestoppte Frames im Leerlauf, ausserhalb des Sichtbereichs
und im Hintergrund, die Obergrenzen für Pixeldichte und Backbuffer (auf einem
simulierten 3×-Bildschirm), Layout-Verschiebungen beim Laden (CLS ≤ 0.02, bei
den Rechnern auch mit gespeicherten Daten) sowie die View Transitions samt
Richtung (`forward`/`back`); optional `--axe /pfad/zu/axe.min.js` für einen
lokal bereitgestellten axe-core-Scan (WCAG 2.2 AA und Best Practices).
`contrast_review.py` misst Textkontraste auf allen drei Seiten in beiden
Farbschemas gegen jede Verlaufsfarbe. `showcase_review.py` prüft die Hero-Demos,
Look-Regler mit tatsächlicher Bildänderung, Touch-Auswahl, Formatablauf und
unveränderte gespeicherte Rechnerdaten. Testausgaben unter `output/playwright/`
bleiben ausserhalb von Git. Das [Prüfprotokoll](docs/REDESIGN_QA.md) trennt
beobachtete Ergebnisse und offene Geräteprüfungen.

### Darstellungsstufe des Glasobjekts erzwingen

Für QA und Fehlersuche lässt sich die Stufe per URL-Parameter festlegen:

| Parameter | Wirkung |
|---|---|
| `/?gl=off` | Statischer SVG-Fallback, kein WebGL-Kontext |
| `/?gl=still` | Ein Standbild, auch auf schneller Hardware |
| `/?gl=force` | Live-Stufe auch bei Software-Rendering oder `saveData` |

Reduced Motion gewinnt immer: Auch mit `?gl=force` gibt es dann nur ein Standbild.
Der aktuelle Zustand steht in `.hero-visual[data-glass-state]` (`boot`,
`compiling`, `live`, `idle`, `still`, `fallback`) und `[data-glass-tier]`;
`HeroGL.stats` in der Browserkonsole zeigt Renderer, Frames und
Backbuffer-Grösse, `HeroGL.render()` erzwingt ein Bild.

## Dateien und Veröffentlichung

| Datei | Inhalt |
|---|---|
| `assets/core.css` | Farb- und Masstokens, gemeinsame Komponenten, Bewegung, View Transitions (ersetzt `site.css`) |
| `assets/home.css` | Startseite: Hero-Bühne, Schilder, Dock, Toolkarten, Projekt, Über mich |
| `assets/hero-demo.js`, `assets/hero-demo.css` | Fiktive Hero-Demos, Material-/Lichtregler und Bedienhinweise |
| `assets/conversion.js`, `assets/conversion.css` | Endlicher Export-/Zuordnungs-/Formatablauf mit Beispieldaten |
| `assets/grades.css` | Notenrechner: Instrument, Diagramm, Zeilen, Planung, Übersicht, Punkte |
| `assets/sleep.css` | Schlafrechner: Zifferblatt, Griffe, Nachtbalken, Feintuning |
| `assets/hero-gl.js` | WebGL-Glasobjekt mit Stufen, Leerlauf-Stopp und Handy-Band |
| `assets/motion.js` | Scroll-Reveals (mit Fallback), magnetische Buttons, Spotlight, dekorative Zähler |
| `assets/workbench.js` | Auswahl der Startseiten-Vorschau, HUD, `benchselect`-Ereignis |
| `assets/theme.js` | Farbschema (gespeichert unter `misterpfister-theme`), Kreisblende |
| `assets/transitions.js` | Erweitert die native Navigation um benannte View Transitions |
| `assets/tool-math.js` | Reine Rechenfunktionen, inklusive Zifferblatt-Mathematik |
| `assets/tool-storage.js` | Kapselt den Browser-Speicher |
| `assets/grades.js`, `assets/sleep.js` | Steuern die beiden Rechner |
| `assets/wisper.css`, `assets/wisper.js` | Wisperpfister-Seite: Beispielablauf, Plattformen, Datenschutz, Beta |

Die Speicherschlüssel und -formate bleiben unverändert
(`misterpfister-grades-v2`, `misterpfister-sleep-v2` und die zugehörigen
`-saving`-Schalter). Alte Sicherungen und Browserdaten laden weiter.

Der bestehende Workflow `Workshop regression tests` prüft Rechenlogik, HTTP-
Bedienung, Browser-Neustarts und Showcase-Demos. Vor dem Push Remote-Änderungen
abgleichen, den
geprüften Stand ohne Force-Push nach `main` übernehmen und anschliessend den
separaten Workflow `pages build and deployment` sowie die Live-Seiten prüfen.
