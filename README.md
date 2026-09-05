# misterpfister.net — Werkplatz 02

Personal digital workshop for Kilian Pfister. Static HTML, CSS and JavaScript,
served from the root of `main` by GitHub Pages. Preserve `CNAME` and existing URLs.
No build step, framework, CDN, external font, tracking script or runtime package.

## What changed

- Selectable CSS-3D tool modules replace the unrelated cube. Pointer motion is
  smoothed with a short-lived animation frame loop; nothing rotates endlessly.
  Touch/keyboard selection, explicit pause and reduced motion are supported.
- Normal links remain available immediately. Cross-document View Transitions
  progressively connect project cards with the corresponding calculator panel.
- Grades: weighted mean, raw/rounded values, configurable grade steps and target
  basis, next-grade scenario, subjects, optional local saving, JSON backup/import,
  undo for destructive actions, and configurable linear points-to-grade conversion.
- Sleep: reactive 24-hour dial, wake/bedtime modes, arbitrary bedtime, Now action,
  minute-precise duration, latency, custom presets and optional local saving.
  Clock times only: no date/DST handling, alarms or sleep-stage predictions.
- SpasstoCSV project explanation uses fictional examples only. No password upload.

## Files

- `index.html`, `sechserrechner/index.html`, `sleepcalculator/index.html`
- `assets/site.css`: responsive shared design, CSS 3D, SVG styling, transitions
- `assets/theme.js`: existing persistent theme control
- `assets/workbench.js`: home interactions, no navigation interception
- `assets/tool-math.js`: pure calculator functions, also importable from Node
- `assets/grades.js`, `assets/sleep.js`: local UI/state logic
- `tests/math.test.js`, `tests/browser_review.py`: regression tests
- `docs/REDESIGN_QA.md`: actual checks and explicit verification limits

## Local development

```sh
python3 -m http.server 8000
```

Open `http://127.0.0.1:8000/` in a browser. No production compilation is required.

## Tests

```sh
node tests/math.test.js
python3 -m pip install playwright
python3 -m playwright install chromium
# In a second terminal, with the HTTP server running:
python3 tests/browser_review.py --base-url http://127.0.0.1:8000/
```

For restricted environments only, the browser runner also supports
`--offline-fixture`. This requires `beautifulsoup4` and embeds the same local
assets with a simulated Storage object. It is NOT a real navigation or native
localStorage test. `--chromium /path/to/chromium` selects an existing executable.
Reports/screenshots go to ignored `test-results/` or an explicit `--output` path.

## Data and safety

Inputs are not sent to a server. Local saving can be switched off independently
for each tool, which removes its saved data. Browser storage is not a durable
backup: export important grades. Import validates format, size and bounds before
replacement and supports undo. Imported text is not inserted as HTML.
Theme preferences keep the existing storage key.

The grade target can explicitly apply to either the exact average or its rounded
appearance. Grade-step settings constrain planned future grades, not historical
entries. School-specific grading policies remain authoritative.

## Deployment

Stage related files together, test, then fast-forward `main`. GitHub Pages handles
publication. Do not force-push or change the hosting/domain configuration.
