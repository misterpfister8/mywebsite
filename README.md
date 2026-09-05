# misterpfister.net

Digitaler Werkplatz von Kilian Pfister: [Startseite](https://misterpfister.net/),
[Notenrechner](https://misterpfister.net/sechserrechner/) und
[Schlafrechner](https://misterpfister.net/sleepcalculator/).

Statisches HTML, CSS und JavaScript. Keine Laufzeitpakete, externen Schriftdateien,
Konten oder Tracking-Skripte. GitHub Pages veröffentlicht `main` aus dem Repository-
Root. `CNAME` und die drei bestehenden URLs bleiben erhalten.

## Funktionen

- Auswählbare räumliche Werkzeugkarten mit Tastatur, Touch, Pause und Reduced
  Motion. Die direkten Toollinks funktionieren unabhängig von der Szene.
- Native Cross-Document View Transitions verbinden die sichtbare Vorschau mit
  dem Rechner. Bei fehlender Unterstützung bleiben es normale Links.
- Noten: gewichteter Schnitt, Anzeige-Rundung, unabhängig gewichtete Simulation,
  Zielplanung, Fächer, Prüfungsnamen, lokale Entwürfe, Undo, JSON-Export/Import
  und lineare Punkteumrechnung.
- Schlaf: 24-Stunden-Uhr, frei wählbare Bett-/Aufstehzeit, minutengenaue Dauer,
  Einschlafzeit, «Jetzt ins Bett», eigene Presets mit Undo und lokale Speicherung.
- SpasstoCSV: Formatillustration mit erfundenen Daten und Verweis auf das
  [lokale Python-Projekt](https://github.com/misterpfister8/spasstocsv).
  Unterstützte Formate laut dessen öffentlicher README: Raw-, Chrome- und
  Proton-CSV sowie Bitwarden JSON. Die Website nimmt keine Passwortdateien an.

## Rechenregeln und Datensicherung

Noten liegen zwischen 1 und 6, Gewichte zwischen 0.01 und 100; maximal zwei
Dezimalstellen, mit Punkt oder Komma. Höchstens 30 Fächer mit je 100 Zeilen.
Die Anzeige wird kaufmännisch auf 0.01, 0.1, 0.5 oder 1 gerundet. Der zusätzlich
angezeigte Rechenwert ist auf vier Dezimalstellen angenähert. Die Zielplanung
vergleicht intern ganzzahlige Kreuzprodukte; sie sucht die kleinste erreichbare
Note in Schritten von 0.01, 0.1, 0.25, 0.5 oder 1. Historische Noten bleiben
unverändert. Die Markierung bei 4 ist keine allgemeine Bestehensgarantie.

Schlafdauer: 1–16 Stunden; Einschlafdauer: 0–180 ganze Minuten. Uhrzeiten ohne
Datum, Alarm oder medizinisches Zyklusmodell. Zeitumstellungen werden nicht
berücksichtigt. Die Punkteformel ist linear, keine universelle Schulregel;
Maximum grösser null und höchstens 1 000 000, Notenskala innerhalb von 1–6.

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
.venv/bin/python tests/contrast_review.py
```

Die Browserprüfungen benötigen den laufenden HTTP-Server. Sie laden die echten
externen Dateien und verwenden nativen Browser-Speicher. Speicherfehler-Injektion
ist ein separater Testfall. `persistence_review.py` prüft echte Browser-Neustarts
und in Chromium zusätzlich nativ deaktivierten Speicher. `interaction_review.py`
prüft Touch und laufende Übergänge; optional `--axe /pfad/zu/axe.min.js` für einen
lokal bereitgestellten axe-core-Scan. Testausgaben unter `output/playwright/`
bleiben ausserhalb von Git. Das [Prüfprotokoll](docs/REDESIGN_QA.md) trennt
beobachtete Ergebnisse und offene Geräteprüfungen.

## Dateien und Veröffentlichung

Die drei HTML-Seiten verwenden `assets/site.css` und `assets/theme.js`.
`tool-math.js` enthält reine Rechenfunktionen, `tool-storage.js` kapselt den
Browser-Speicher, `grades.js` und `sleep.js` steuern die Rechner. `workbench.js`
steuert die Vorschauen, `transitions.js` erweitert die native Navigation.

Der bestehende Workflow `Workshop regression tests` prüft Rechenlogik, HTTP-
Bedienung und Browser-Neustarts. Vor dem Push Remote-Änderungen abgleichen, den
geprüften Stand ohne Force-Push nach `main` übernehmen und anschliessend den
separaten Workflow `pages build and deployment` sowie die Live-Seiten prüfen.
