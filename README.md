# misterpfister.net

Personal project index for Kilian Pfister. Hosted on GitHub Pages with a custom domain.

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

- Shared design system in `assets/site.css`
- System fonts only; no external font requests
- Semantic HTML and responsive CSS Grid layouts
- Deployed via GitHub Pages with custom domain (CNAME)

---

## Local Development

```bash
git clone git@github.com:misterpfister8/mywebsite.git
cd mywebsite
python -m http.server 8000
```

Open [localhost:8000](http://localhost:8000).

---

## Structure

```
mywebsite/
├── assets/
│   ├── favicon.svg
│   └── site.css
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
