# Prüfprotokoll – digitaler Werkplatz

## Werkplatz 5 · Liquid Glass Lab (2026-09-29)

Diese Prüfung betrifft den Neubau «Werkplatz 5» im Arbeitsstand des Repositorys
(noch nicht committet): neues WebGL-Glasobjekt auf der Startseite, neu gebaute
Rechner, gemeinsame Grundlage `core.css`/`motion.js` statt `site.css`. Alle
Werte unten wurden am 2026-09-29 in dieser Sitzung beobachtet (dritter
Prüfdurchgang, nach den Korrekturen aus der Review-Runde an Startseite,
Grundlage, Notenrechner und Schlafrechner); nichts ist aus früheren Läufen
übernommen.

### Umgebung

macOS 27.0.1 (ARM64), Python 3.13.0, Node 26.7.0, Playwright 1.62.0, Chromium
151.0.7922.34 (headless, WebGL2 über ANGLE/SwiftShader, Glasobjekt deshalb
standardmässig in der Stufe `still`). Auf Port 8000 lief bereits ein
statischer Server für den Arbeitsstand (nicht von dieser Prüfung gestartet;
`python3 -m http.server` hängt in dieser Sandbox bei der Namensauflösung); alle
Läufe nutzten die Standard-`--base-url`. Die Suiten liefen nacheinander, nicht
parallel. Playwright-WebKit ist nicht installiert und wurde nicht
heruntergeladen.

### Angepasste und neue Prüfungen

Die Suiten prüfen das neue DOM und das neue Verhalten. Keine bestehende
Prüfung wurde entfernt; Selektoren wurden nur dort angepasst, wo sich das Markup
bewusst geändert hat (zum Beispiel `textContent` statt `innerText` für
Grossbuchstaben-Tags).

- `tests/math.test.js`: Zifferblatt-Mathematik aus Spec §7.5 (`pointerAngle`,
  `dialMinutes`, `dialDuration`) mit allen Spec-Fällen, Wertebereich und
  Schrittraster über −720° bis 720°, exakter Rundlauf Zeiger → Winkel → Minute
  für alle 1440 Minuten, Umkehrung von `sleepPlan` für beide Modi und
  Begrenzung auf 1–16 h auf der Seite, von der der Zug kam.
- `tests/browser_review.py`:
  - Startseite: Glasobjekt erreicht einen ruhenden Zustand
    (`data-glass-state` ∈ `idle`/`still`/`fallback`), `HeroGL` spiegelt die
    DOM-Attribute, HUD-Texte und `data-glass-form` folgen der Auswahl,
    `benchselect` wird einmal mit `init` und danach mit `user` ausgelöst,
    Vorauswahl beim Zurückkommen vom Schlafrechner, erzwungene Stufen
    `?gl=still` und `?gl=off` (Fallback ohne Warnung, SVG-Überblendung), Pfad
    ganz ohne WebGL (genau eine `console.warn`, kein Fehler), Forced Colors,
    Seite ohne JavaScript, CSS-Failsafe nach 4 s bei blockiertem Engine-Skript,
    magnetischer Primärbutton, Zähler der Toolkarten, Formatwechsel mit
    einmaliger Kippbewegung, «Über mich» mit `aria-labelledby="about-title"`.
    Farbschema: `themechange` genau einmal mit `detail.theme`, `theme-color`
    `#0B0D0F`/`#F2F3EE`, gespeicherte Wahl und Beschriftung des Schalters.
  - Notenrechner: klebendes Ergebnis bei 1440×1000 (Klasse und berechnetes
    `position: sticky`, Position beim Scrollen), Balkendiagramm mit vier Balken
    und Simulationsbalken, Werte der Skala (`--avg`, `--sim`, `--target`,
    Füllung, Bogen), Differenz-Chip ▲/▼/= mit Regex aus dem Spec,
    Gewichts-Chips in beide Richtungen, Zielkarte `secured`/`danger`,
    Fachname im Ergebnis, Fächer-Zusammenfassung mit Sprung zur Übersicht,
    «Aktiv»-Badge ausserhalb des Buttons, Einstellungsknopf öffnet «Fach &
    Datensicherung», Punkteformeln, kompakte Leiste auf Handys. Neu im zweiten
    Durchgang: Fokus nach Löschen und Rückgängig (Zeiger → «Rückgängig» bzw.
    «Note hinzufügen», Tastatur → nächste bzw. erste Note, nie `<body>`),
    Glanzeffekt nach Beispiel laden und Fachwechsel, nie beim Tippen und nie
    unter Reduced Motion, Zeilenlayout (Index und «#» erst ab 681 px, zweizeilig
    bei 360 px), volles Fach mit 100 Noten (100 Balken, `data-dense`, keine
    101. Zeile, Rückgängig stellt die Fächer wieder her).
  - Schlafrechner: ARIA-Werte beider Griffe in beiden Modi, Tastatur (±5, ±1,
    ±60, Home/End, Umbruch über Mitternacht, Begrenzung 1–16 h), Speichern per
    Tastatur, Mausziehen beider Griffe mit genau einem Speicherzugriff pro Zug,
    Tippen auf den Ring, Griffe liegen geometrisch auf dem Ring, Nachtbalken mit
    Mitternachtsmarke (Anteil `--mid` und Randlage), Preset-Modus und Aufbau
    der Preset-Chips, deaktivierte Griffe bei ungültiger Eingabe mit stabiler
    Anzeigehöhe, kompakte Leiste bei 402 und 768 px, klebendes Zifferblatt
    bei 1440×1000 ohne kompakte Leiste.
  - Alle Seiten: Überlaufprüfung bei 320, 370, 371, 375, 390, 402, 680, 681,
    768, 900, 901, 1024, 1025, 1150, 1151, 1440, 1600, 1601 und 1920 px, beide
    Farbschemas, beide Bewegungsmodi, zusätzlich `/?gl=off`; Phone-Budgets
    inklusive Band ≤ 170 px; keine fokussierbaren Elemente in
    `aria-hidden`/`role=img`; alle ARIA-Verweise lösen auf; keine
    Endlosanimationen; Touch-Ziele ≥ 44 px bei 320 und 402 px; Details öffnen
    unter Reduced Motion sofort; alle Assets lokal mit `?v=werkplatz-5`; keine
    Anfrage verlässt die eigene Origin; kein Canvas und weder `hero-gl.js` noch
    `workbench.js` auf den Rechnerseiten; `Motion.countUp` verweigert echte
    Ergebnisse.
- `tests/interaction_review.py`: Glasband auf Handys, Ziehen eines
  Zifferblatt-Griffs per Touch (CDP) ohne Seitenscroll, Scroll-Morph des
  Handy-Bands Notenskala → Ring → Würfel mit mitlaufenden Beschriftungen,
  Warten auf den ruhenden Zustand vor der Frame-Zählung, `?gl=force` (live →
  idle, Frames stoppen ≤ 1.2 s nach Zeigerbewegung, Auswahl, Ziehen und
  Themawechsel, sofort ausserhalb des Sichtbereichs; Hover-Cursor; Klick aufs
  Objekt öffnet das Tool), `?gl=off`, Reduced Motion ohne Frame-Anforderungen,
  keine wiederholte Einblendung nach der View Transition, keine ungefangene
  Promise-Ablehnung beim Grössenwechsel während der Ankunfts-Transition. Neu
  im zweiten Durchgang: Band und Live-Stufe auf simulierten 3×-Bildschirmen,
  damit die Grenzen DPR ≤ 1.25 (Touch) und ≤ 1.5 (Desktop) wirklich greifen;
  Transition-Typen `forward`/`back`; `html.vt-arrived` nach der Ankunft;
  Navigation unter Reduced Motion ohne View Transition; CLS beim Laden aller
  drei Seiten bei 1440, 402 und 360 px (verzögerte `defer`-Skripte wie im
  Mobilnetz, Grenze 0.02).
- `tests/contrast_review.py`: alle drei Seiten in beiden Farbschemas
  (Notenrechner leer und mit Beispiel); Toolkarten, Ergebnisinstrument, alle
  Verlaufsstopps von `.film-text` gegen `--bg`, HUD-Zeilen, alle Texte der
  Schilder sowie `.dial-tip` und `.midnight`.
- `tests/persistence_review.py`: zusätzlich überlebt eine Zifferblatt-Änderung
  einen echten Browser-Neustart im unveränderten Speicherformat.

Neu oder angepasst im dritten Durchgang:

- Bewusst geänderte Erwartungen (Schlafrechner): Der Tipp am Endgriff zeigt
  nur noch die Dauer (`8 h`); der Moduswechsel behält dieselbe Nacht (Wecker
  07:30 → Bettzeit 23:20 → zurück 07:30) statt die Uhrzeit umzudeuten; die
  bisher nur zufällig grüne Prüfung `7:5` → `—:—` ist ersetzt durch: halb
  getippte Zeiten (`''`, `0`, `2`, `07:`, `7.4`, `064`, `233`, `7:5`) warten
  ohne Fehler, ohne Neuberechnung und ohne Speichern; erst Verlassen
  entscheidet (`7:5` → Fehler, `1` + Enter → 01:00); `7:7`, `99` und `24:00`
  sind sofort ungültig.
- `tests/browser_review.py`:
  - Stylesheets: Chromium nimmt jede Deklaration (var() gegen `:root`
    aufgelöst), jeden Selektor und jede `@media`-/`@supports`-Bedingung an
    (unbekannte Media-Features werden über `matchMedia` erkannt). Erlaubt sind
    nur bewusst browserübergreifende Regeln (`hanging-punctuation`,
    `-webkit-backdrop-filter`, einzelne `::-moz-range-*`-Selektoren).
  - Startseite: Die Einblendung, eingefroren bei 0–900 ms, schneidet Lead,
    CTAs und Hinweis nie per `clip-path` an; nach dem Laden ist kein Herotext
    abgeschnitten, von einem Vorfahren beschnitten oder transparent
    (1440, 1024, 390 px). Dock und Vorschau-Hinweis im ersten Bild bei
    1280×720, 1366×768, 1440×790, 1536×730, 1100×700, 1024×600, 1366×657;
    Frontschild frei vom Dock (901–1200 px hart, kurze Höhen weich). Das
    Formatabzeichen bleibt bei 320–390 px in der Demokarte (CSV und JSON).
    Beide Navigationslinks im Handy-Header. Kartenzahlen zählen mit Bewegung
    tatsächlich hoch, das Mini-Gauge folgt jedem Frame.
  - Alle Seiten: Jeder Tab-Stopp ist sichtbar, mindestens 8×8 px und im
    Sichtbereich (1440 und 390 px); Reveals sind vollständig eingeblendet,
    sobald ihr Block ganz sichtbar ist; die Fussmarke behält ihre Unterlängen
    (320–1920 px).
  - Notenrechner: Escape schliesst das Fach-Formular; nur das falsche
    Punktefeld wird markiert und benannt; Beispiel bei eigenen Noten als neues
    Fach «Beispiel»; unerreichbares Ziel nennt den besten Schnitt; ungültige
    Note dimmt das Diagramm; Ergebnis klebt ganz sichtbar bei 1366×657,
    1024×640, 1280×560; Schieberegler ≥ 400 px (1440/1151/768), Planung im
    ersten 1440×900-Bild, Namensfeld ≥ 150 px bei 901/1150, Fach-Icons in
    einer Zeile; schwebender Hinweis nie über dem Ergebnis; leeres Diagramm
    auf Handys versteckt; ohne JavaScript kein Rechner.
  - Schlafrechner: Mausziehen zeigt den Tipp ausserhalb des Rings; die
    Zusammenfassung schweigt während des Ziehens und folgt danach; kein
    Fokusring nach Mausziehen, aber nach Tab; passendes Preset gedrückt;
    Preset-Formular als Disclosure mit Escape; Latenz-Legende («Sofort
    eingeschlafen», «3 h Einschlafen»); «Am Vortag» für 12:00 am Vortag;
    klebendes Panel bei 1366×657 und 1024×600, Kompaktleiste bei 1280×560.
- `tests/interaction_review.py`: Touch-Ziehen zeigt den gezogenen Wert in der
  Mitte, der Tipp unter dem Finger bleibt verborgen; der Test wartet jetzt auf
  das Ende der `load-rise`-Einblendung, bevor er den Fingerweg berechnet
  (Ursache des sporadischen 06:15 statt 06:00: das Panel glitt noch um bis zu
  16 px). CLS zusätzlich bei 320 px und mit gespeicherten Daten (drei Fächer,
  sechs Noten; fünf Presets). axe mit WCAG 2.2 AA und Best Practices, zusätzlich
  im JSON-Zustand mit offenen Details, mit Fächerübersicht und mit offenem
  Preset-Formular (24 Scans statt 12).
- `tests/math.test.js`: «Am Vortag» vor 17:00 des Vortags, Grenze 17:00
  (`Am Vorabend`) und 16:59 (`Am Vortag`), Tageslabel im Rundlauf über alle
  Zeiten, Dauern, Latenzen und Modi.

Die neuen Prüfungen wurden gegen die alten Fehler gegengeprüft (Datei per
Route ersetzt): altes `h-rise` mit `clip-path`, `margin-bottom` statt
`padding-bottom` an der Fussmarke, alte `animation-range` der Reveals,
fehlendes `tabindex="-1"` am versteckten Submit, fehlendes Reservierungsskript
im Notenrechner (CLS mit Daten 0.030–0.232) und absichtlich ungültiges CSS
(`#12g`, `colr`, gemischte `::-moz-`-Liste, `100pxx`). Alle schlagen an.

Abweichung vom Spec §9: Das Eckpixel der Bühne entspricht nicht exakt `--bg`,
weil Seitenlicht und Körnung (core.css) diese Stelle auch ohne Canvas tönen
(gemessen `rgb(19 22 21)` statt `rgb(11 13 15)`). Geprüft wird deshalb, dass
die Ecke mit und ohne Canvas identisch ist (Differenz 0) und dass der Canvas an
allen vier Ecken Alpha 0 hat. Das weist «kein grauer Schleier» direkter nach.

### Tatsächlich ausgeführt

- `node tests/math.test.js`: **77 926 Assertions bestanden** (0.2 s; vorher
  75 882).
- `tests/browser_review.py`: **Rot.** 795 Prüfungen bestanden (vorher 673),
  alle harten Prüfungen grün, 7 weiche Prüfungen mit 3 offenen
  Produktfehlern (Punkte 1–3 unten) scheitern; Laufzeit 74–76 s. Keine
  JavaScript-Fehler, keine fehlgeschlagenen oder externen Anfragen.
- `tests/persistence_review.py`: **bestanden** (1.7 s), inklusive nativ
  deaktiviertem Speicher und Zifferblatt-Neustart.
- `tests/interaction_review.py --axe …/axe.min.js` (axe-core 4.11.3, lokale
  Kopie): **bestanden**, 24 axe-Scans ohne Verstoss, Laufzeit 148 s. CLS beim
  Laden 0 auf allen Seiten und Breiten, mit gespeicherten Daten im
  Notenrechner 0.0017–0.0034 (Grenze 0.02), im Schlafrechner 0. Letzter Frame
  879–888 ms nach der letzten Eingabe (Grenze 1.2 s), Band 585 ms; Backbuffer
  1047×1047 bei 698 px Bühne und 3×, Band 503×191 bei 402 px und 3×. Der von
  zwei Seitenverantwortlichen einmal gesehene Fehler «Transition was skipped»
  trat in drei vollständigen Läufen nicht auf.
- `tests/contrast_review.py`: **314 Farbpaare ≥ 4.5:1**, Minimum **5.1:1**
  (leere Anzeige `-.--` im dunklen Notenergebnis), 2.2 s.
- Das CLS-Problem des Notenrechners aus dem zweiten Durchgang ist behoben
  (Reservierung im Seitenkopf) und jetzt auch mit gespeicherten Daten
  abgedeckt.

### Offene Produktpunkte (nicht in Testdateien behoben)

1. **Zeitleiste widerspricht der Anzeige** (`assets/sleep.js:168`,
   Schlafrechner): Aufstehen 07:00, 16 h, 180 min ergibt in der Anzeige
   «Am Vortag» (Bettzeit 12:00), die Zeitleiste zeigt bei Bettzeit und
   Einschlafen aber «Vorabend». Die Zeile setzt für jede Zeit vor Mitternacht
   `Vorabend`; nötig ist `p[id] < -420 ? 'Vortag' : p[id] < 0 ? 'Vorabend' : …`.
2. **Frontschild überdeckt das Dock auf kurzen Laptop-Bildschirmen**
   (`assets/home.css`, Startseite): Vermutlich seit die Bühne ab 901 px auch
   nach der Fensterhöhe begrenzt wird (mindestens 440 px), ragt das vordere
   Schild in das Dock: 19 px bei 1366×657, 7 px bei 1280×720, 6 px bei
   1536×730 und 1024×600, 3 px bei 1366×768. Gemessen betrifft das jede Breite
   ab 1201 px bei Höhen unter etwa 790 px und 901–1200 px bei Höhen bis 600 px.
   Bei 901–1200 px und 1000 px Höhe bleiben 6–33 px Abstand.
3. **Kartenzahlen zählen von 0 statt 1** (`assets/motion.js:81`, Grundlage):
   `initCounters` übergibt kein `from`, deshalb zeigt der Schnitt der
   Notenkarte zuerst 0.00 bis 0.99, also Werte unter der Notenskala;
   `data-count-from="1"` im Markup wird ignoriert. Nötig ist
   `countUp(el, {from: Number(el.dataset.countFrom) || 0, …})` und derselbe
   Startwert beim Vorbelegen des Texts. Das Mini-Gauge folgt der Zahl bereits
   in jedem Frame.
4. **Dateibudgets laut Spec §8.4** (keine automatische Prüfung; 1 KB = 1024
   Byte): über dem Budget liegen `sleep.js` 25 717 / 18 432, `grades.css`
   26 381 / 22 528, `sleep.css` 21 464 / 18 432, `grades.js` 30 120 / 27 648,
   `home.css` 32 955 / 30 720, `workbench.js` 7 690 / 7 168, `hero-gl.js`
   22 729 / 22 528 und `transitions.js` 3 166 / 3 072. Innerhalb: `core.css`
   46 003 / 46 080, `motion.js`, `theme.js`. Der Brief nennt für das Hero-Modul
   «idealerweise ≤ 25 KB»; das hält `hero-gl.js` ein.
5. **Inline-Skript im Notenrechner** (`sechserrechner/index.html`, Kopf): Die
   Layout-Reservierung gegen CLS ist ein Inline-`<script>`. Der Brief verlangt
   Code aus `assets/`; die Prüfung der Assets erfasst nur `script[src]`.
   Entscheidung offen, ob es nach `assets/` wandert.

Randnotiz: Die Panels gleiten beim Laden mit Bewegung um bis zu 16 px
(`load-rise`). Wer währenddessen schon am Zifferblatt zieht, bewegt den Griff
leicht an der Fingerposition vorbei. Kein Testfehler mehr, weil der Touch-Test
jetzt das Ende der Einblendung abwartet.

### Verbleibende Prüfgrenzen

- Kein WebKit-, Firefox- oder Safari-Lauf (Browser nicht installiert), kein
  physisches iPhone und kein Screenreader-Test.
- Die Live-Stufe wurde nur auf SwiftShader (CPU) gemessen, nicht auf einer
  echten Grafikkarte. Keine FPS- oder GPU-Zeitmessung für die Budgets
  (≤ 6 ms, 60 fps); `?gl=force` ist dort langsam, aber funktional.
- `document.hidden` blieb in der Automation `false`; der Hintergrund-Tab-Pfad
  ist wie bisher nur im Code geprüft.
- Der CI-Lauf auf Ubuntu wurde nicht beobachtet. Dort ist entweder SwiftShader
  (Stufe `still`) oder kein WebGL (Stufe `fallback`) zu erwarten; beide Pfade
  sind lokal geprüft. Die CLS-, DPR- und axe-Prüfungen laufen nur lokal in
  `interaction_review.py`, nicht in CI. Solange die Punkte 1–3 offen sind,
  endet `browser_review.py` auch in CI rot.
- Die Stylesheet-Prüfung löst `var()` nur gegen `:root` auf; 23–32
  Deklarationen je Seite mit lokal gesetzten Variablen bleiben ungeprüft.
  Sie läuft nur in Chromium.

---

## Historie: Prüfprotokoll vom 2026-09-05

Datum: 2026-09-05. Diese Prüfung betrifft die echte Website im Repository,
keine eingebettete HTML-Kopie und keine Übernahme früherer Testergebnisse.
Die Bilder aus dem Auftrag dienten ausschliesslich als Gestaltungsreferenz.

### Stand und Umfang

Ausgehend vom live abgerufenen Commit `40bde4c` wurde der Umbau vervollständigt.
Der während der Arbeit hinzugekommene CI-Commit `c2b2119` wurde per Fast-forward
integriert. Uncommittete fremde Änderungen gab es beim Start nicht.

Überarbeitet: drei Seiten, gemeinsame Gestaltung, räumliche Auswahl, Karten-
übergänge, getrennte Simulationsgewichte, ganzzahlige Zielnotenvergleiche,
Speicherzugriff, 24-Stunden-Eingabe, Presets, Sicherung und Testabdeckung.
Die Domain-Datei und der vorhandene GitHub-Pages-Prozess bleiben erhalten.

### Tatsächlich ausgeführt

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

### Verbleibende Prüfgrenzen

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

### Bewusste Produktgrenzen

Uhrzeitplaner ohne Datum, Zeitumstellungslogik oder Alarm. Kein medizinisches
Schlafmodell. Keine universelle Schulrundung. Browser-Speicher ist kein Backup.
SpasstoCSV bleibt ein lokales Projekt; auf der Website gibt es nur erfundene
Formatbeispiele. Keine Accounts, Kalenderintegration, PWA oder weiteren Rechner.

Testberichte, Screenshots und Videos liegen lokal unter `output/playwright/`
und sind von Git ausgeschlossen. Der Veröffentlichungsnachweis erfolgt
zusätzlich nach dem Push anhand des Pages-Workflows und der ausgelieferten
Dateien; der Commit allein gilt nicht als Deploymentbestätigung.
