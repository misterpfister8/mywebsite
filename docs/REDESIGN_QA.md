# Prüfprotokoll – digitaler Werkplatz

Datum: 2026-09-05. Diese Prüfung betrifft die echte Website im Repository,
keine eingebettete HTML-Kopie und keine Übernahme früherer Testergebnisse.
Die Bilder aus dem Auftrag dienten ausschliesslich als Gestaltungsreferenz.

## Stand und Umfang

Ausgehend vom live abgerufenen Commit `40bde4c` wurde der Umbau vervollständigt.
Der während der Arbeit hinzugekommene CI-Commit `c2b2119` wurde per Fast-forward
integriert. Uncommittete fremde Änderungen gab es beim Start nicht.

Überarbeitet: drei Seiten, gemeinsame Gestaltung, räumliche Auswahl, Karten-
übergänge, getrennte Simulationsgewichte, ganzzahlige Zielnotenvergleiche,
Speicherzugriff, 24-Stunden-Eingabe, Presets, Sicherung und Testabdeckung.
Die Domain-Datei und der vorhandene GitHub-Pages-Prozess bleiben erhalten.

## Tatsächlich ausgeführt

Umgebung: macOS ARM64, Python 3.13.0, Node 26.7.0, Playwright 1.62.0,
Chromium 151.0.7922.34 und Playwright WebKit 26.5. Lokaler Server:
`python3 -m http.server 8000 --bind 127.0.0.1`.

- `node tests/math.test.js`: **25 614 Assertions bestanden**. Enthalten sind alle
  Auftragsbeispiele, Grenzen knapp unter Rundungsschwellen, Ziele ausserhalb
  des Anzeigerasters und unabhängige BigInt-Vergleiche aller erreichbaren
  Noten mit Gewichten von 0.01 bis 100. Schlaf: Mitternacht, unübliche Minuten,
  Null-Einschlafdauer und Grenzwerte. Punkte: 45/60 = 4.75 und ungültige Grenzen.
- `tests/browser_review.py`: vollständige HTTP-Bedienprüfung in Chromium und
  WebKit, jeweils **319 Assertions bestanden**. Geprüft wurden alle drei Seiten in beiden Themes, jeweils mit und
  ohne Reduced Motion, bei 320, 375, 402, 768, 1024 und 1440 CSS-Pixeln sowie
  370/371, 680/681, 900/901, 1025, 1150/1151 und 1600/1601. Kein horizontaler
  Seitenüberlauf, keine JavaScript-/Konsolenfehler, keine fehlenden Assets.
- Echte Navigation: Hero- und Projektlinks, Werkzeugwechsel, Zurück, Vorwärts,
  Reload, Direktaufruf und erneutes Öffnen in einem separaten Browser-Tab.
- Noten: Eingaben mit Komma, ungültige Werte, getrennte Simulations- und
  Zielgewichte, Zeilen/Fächer/Umbenennen, Löschen/Undo, Schutz neuerer Eingaben
  beim verzögerten Undo, Export und bestätigter/abgebrochener Import.
  Ungültiges JSON, Schema, Notenbereich und übergrosse Dateien wurden abgewiesen.
  Importierte HTML-Zeichenfolgen bleiben Text und führen keinen Code aus.
- `tests/persistence_review.py`: native Browserprofile über **vier echte
  Prozessstarts**, in Chromium und WebKit. Notenentwürfe, letzte gültige
  Schlafzeiten und Opt-out bleiben korrekt erhalten. In Chromium zusätzlich
  `--disable-local-storage`: beide Rechner bleiben funktionsfähig und zeigen
  den Speicherfehler. Quota-/SecurityError-Injektionen im Bedienlauf sind
  separat gekennzeichnet; sie ersetzen diese nativen Speicherprüfungen nicht.
- `tests/interaction_review.py`: alle räumlichen Karten und normalen
  Auswahlknöpfe mit Touch bei 320, 375 und 402 Pixeln in beiden Engines.
  Tastaturauswahl inklusive Leertaste, Pfeilen, Home/End im Bedienlauf.
- Laufende Animationen in Chromium und WebKit aufgezeichnet und anhand
  zeitlich versetzter Browserbilder betrachtet. Unterschiedliche Zwischen-
  transformationen und der ruhende Endzustand wurden gemessen. Nach dem
  Einpendeln, bei Pause und bei einer nicht sichtbaren Szene im Dokument
  werden keine weiteren Szenen-Frames angefordert. Reduced Motion schaltet
  die Szenenanimation aus. Keine FPS- oder CPU-Prozentwerte behauptet.
- Native Cross-Document View Transitions: `ready` und `finished` beim Wechsel
  zur Notenseite sowie zurück in **beiden Engines tatsächlich beobachtet**.
  Die Links wurden nicht durch JavaScript-Navigation ersetzt.
- axe-core 4.13.0: zwölf Scans (drei Seiten, zwei Themes, 402/1440 Pixel),
  keine automatisch erkannten WCAG-A/AA-Verstösse. Die nicht automatisch
  bewertbaren Farbverläufe und Markenfarben wurden zusätzlich geprüft:
  `tests/contrast_review.py`, 96 tatsächliche Browser-Farbpaare, mindestens
  **5.16:1** Textkontrast. Dies ist keine vollständige Barrierefreiheitszertifizierung.
- Screenshots in beiden Themes betrachtet, insbesondere 320, 402, 768, 1024
  und 1440 Pixel. Korrigiert wurden Schriftgrössen, mobile Dichte, der mobile
  Abschnittsabstand, Theme-Zwischenkontraste und blockierte Touch-Flächen
  durch die unsichtbare CSS-3D-Bühnenebene.
- Abschliessend tatsächlichen Diff, neue Dateien, Syntax, externe Ressourcen,
  Importausgabe, Datenverlustpfade und Scope geprüft. Keine echten Noten,
  Passwortdateien oder Zugangsdaten in Testdateien/Commits.

## Verbleibende Prüfgrenzen

- WebKit ist ein realer Browsermotor, aber kein physisches iPhone und kein
  manueller Safari-/VoiceOver-Gerätetest. Native iOS-Tastatur und Zoom auf
  echter Hardware wurden nicht geprüft.
- Die Automationsbrowser meldeten `document.hidden` auch nach Vordergrund-
  wechsel und Minimieren des Testfensters weiter als `false`. Deshalb ist der
  spezielle Hintergrundtab-Pfad nicht als native Integration geprüft markiert.
  Der Visibility-Handler wurde im Code geprüft; Leerlauf, Pause und Offscreen
  sind dagegen tatsächlich getestet. Es wurde kein falscher Sichtbarkeitswert
  eingesetzt, um diesen Test als bestanden auszugeben.
- Kein Lighthouse- oder Hardware-FPS-Benchmark. axe meldet bei einigen
  SVG-/Verlaufsflächen eine manuelle Prüfung; die Farbpaare und Ansichten
  wurden geprüft, ein Screenreader-Nutzungstest bleibt offen.

## Bewusste Produktgrenzen

Uhrzeitplaner ohne Datum, Zeitumstellungslogik oder Alarm. Kein medizinisches
Schlafmodell. Keine universelle Schulrundung. Browser-Speicher ist kein Backup.
SpasstoCSV bleibt ein lokales Projekt; auf der Website gibt es nur erfundene
Formatbeispiele. Keine Accounts, Kalenderintegration, PWA oder weiteren Rechner.

Testberichte, Screenshots und Videos liegen lokal unter `output/playwright/`
und sind von Git ausgeschlossen. Der Veröffentlichungsnachweis erfolgt
zusätzlich nach dem Push anhand des Pages-Workflows und der ausgelieferten
Dateien; der Commit allein gilt nicht als Deploymentbestätigung.
