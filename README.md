# misterpfister.net

Personal digital workshop for Kilian Pfister. Hosted on GitHub Pages with a custom domain.

**Live:** [misterpfister.net](https://misterpfister.net)

---

## Projects

| Project | Description | Type |
|---|---|---|
| [SpasstoCSV](https://github.com/misterpfister8/spasstocsv) | Local Samsung Pass `.spass` converter for CSV and Bitwarden JSON | Open Source |
| [Notenrechner](https://misterpfister.net/sechserrechner/) | Weighted calculator for the Swiss 1–6 grade scale | Tool |
| [Schlafrechner](https://misterpfister.net/sleepcalculator/) | Bedtime and wake-time planner with configurable sleep latency | Tool |

---

## Stack

Pure HTML, CSS, JavaScript — no frameworks, tracking scripts, or build step.

- Shared responsive workshop design in `assets/site.css`
- CSS 3D sculpture with pointer interaction, pause control, reduced-motion and offscreen handling in `assets/sculpture.js`
- Persistent dark/light theme handling in `assets/theme.js`
- System fonts only; no external font requests
- Semantic HTML and responsive CSS Grid layouts
- Deployed via GitHub Pages with custom domain (CNAME)

---

## Local Development

```bash
git clone git@github.com:misterpfister8/mywebsite.git
cd mywebsite
python3 -m http.server 8000
```

Open [localhost:8000](http://localhost:8000).

---

## Structure

```
mywebsite/
├── assets/
│   ├── favicon.svg
│   ├── site.css
│   ├── theme.js
│   └── sculpture.js
├── index.html
├── sechserrechner/
│   └── index.html
├── sleepcalculator/
│   └── index.html
├── CNAME
└── README.md
```

---

© 2026 misterpfister.net

## Verification

Browser checks cover weighted grades, decimal commas, rounding, target planning,
invalid inputs, row controls, reset, Enter, sleep modes, midnight rollover,
320–1440px layouts, theme persistence, reduced motion and navigation.
With a local server running and Playwright CLI installed:

```bash
playwright-cli open http://localhost:8000
playwright-cli run-code "$(cat tests/browser-checks.js)"
```

The check function returns a list of passed assertions and throws on failure.
No build step or runtime dependency is needed. GitHub Pages publishes the root
of `main`; preserve `CNAME` and push only fast-forward updates.
