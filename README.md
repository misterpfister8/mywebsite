# misterpfister.net

Eine moderne, minimalistische Portfolio-Website mit nützlichen Web-Tools.

## 🎯 Übersicht

Diese Website dient als zentrale Anlaufstelle für verschiedene Web-Tools und Projekte. Sie wurde mit Fokus auf Clean Design, Benutzerfreundlichkeit und Responsivität entwickelt.

**Live:** [misterpfister.net](https://misterpfister.net)

## ✨ Features

### Design
- 🎨 **Professionelles Dark Theme** mit Slate-Farbpalette
- 💜 **Violette Akzentfarbe** für moderne Optik
- 📱 **Vollständig responsiv** - optimiert für Desktop und Mobile
- ⚡ **Premium Hover-Effekte** mit smooth Transitions
- ♿ **Accessibility-Features** inklusive reduced-motion Support

### Projekte

#### 📊 Sechserrechner
Notendurchschnitt-Rechner mit intelligenten Features:
- **Auto-Berechnung** während der Eingabe
- **Farbcodiertes Feedback** (Grün/Blau/Gelb/Orange/Rot)
- **Prozentanzeige** neben der Note
- Gewichtete Notenberechnung

#### 😴 Sleep Calculator
Intelligenter Schlafrechner basierend auf Schlafzyklen:
- **Schnellauswahl** für gängige Schlafdauern (7h, 8h, 9h)
- **"Jetzt schlafen" Button** für sofortige Berechnung
- **Schlafzyklen-Info** (90-Minuten-Zyklen)
- Berücksichtigt 10 Minuten Einschlafzeit

#### 🍳 Mealie
Self-hosted Rezeptverwaltung und Meal Planning (externer Service)

#### 🔄 SpasstoCSV
Daten-Konverter für SPASS-Format
- [GitHub Repository](https://github.com/misterpfister8/spasstocsv)

## 🛠️ Technologien

- **Pure HTML/CSS/JavaScript** - Keine Frameworks, keine Dependencies
- **Inter Font** von Google Fonts
- **CSS Custom Properties** für konsistente Theming
- **CSS Grid** für modernes Layout
- **Semantic HTML** für bessere Accessibility

## 🎨 Design-System

### Farben
```css
--bg-primary: #0f172a;      /* Haupthintergrund */
--bg-secondary: #1e293b;    /* Sekundärer Hintergrund */
--card-border: #334155;     /* Borders */
--color-accent: #7c3aed;    /* Akzentfarbe Violett */
--color-text-primary: #f8f9fa;
--color-text-secondary: #adb5bd;
```

### Typografie
- **Haupt-Font:** Inter (400, 500, 600, 700)
- **Monospace:** SF Mono, Monaco, Roboto Mono

## 📱 Browser-Support

- ✅ Chrome/Edge (neueste Version)
- ✅ Firefox (neueste Version)
- ✅ Safari (neueste Version)
- ✅ Mobile Browser (iOS Safari, Chrome Mobile)

## 🚀 Deployment

Die Website wird automatisch über GitHub Pages deployed:
- **Branch:** `main`
- **Custom Domain:** misterpfister.net (via CNAME)

## 📂 Struktur

```
mywebsite/
├── index.html              # Hauptseite
├── sleepcalculator/
│   └── index.html         # Sleep Calculator Tool
├── sechserrechner/
│   └── index.html         # Notenrechner Tool
├── CNAME                  # Custom Domain Config
└── README.md             # Diese Datei
```

## 🔧 Lokale Entwicklung

1. Repository klonen:
```bash
git clone git@github.com:misterpfister8/mywebsite.git
cd mywebsite
```

2. Mit einem lokalen Server öffnen:
```bash
# Python 3
python -m http.server 8000

# Node.js (mit npx)
npx http-server

# VS Code Live Server Extension
# Rechtsklick auf index.html → "Open with Live Server"
```

3. Browser öffnen: `http://localhost:8000`

## 🎯 Roadmap

- [ ] Dark/Light Mode Toggle
- [ ] Weitere Tools hinzufügen
- [ ] PWA Support (Offline-Funktionalität)
- [ ] Erweiterte Statistiken im Sechserrechner
- [ ] Export-Funktion für Berechnungen

## 📝 Changelog

### v2.0.0 (2026-02-12)
- ✨ Komplettes Redesign mit Dark Theme
- ✨ 2×2 Grid Layout mit Icons und Beschreibungen
- ✨ Auto-Berechnung im Sechserrechner
- ✨ Farbcodiertes Feedback
- ✨ Sleep Calculator mit Preset-Buttons
- ✨ "Jetzt schlafen" Feature
- ✨ Schlafzyklen-Anzeige

### v1.0.0
- 🎉 Initiales Release
- Basic Design mit Gradient-Hintergrund
- Einfache Tool-Links

## 📄 Lizenz

© 2026 misterpfister.net - Alle Rechte vorbehalten.

## 🤝 Kontakt

- 🌐 Website: [misterpfister.net](https://misterpfister.net)
- 💻 GitHub: [@misterpfister8](https://github.com/misterpfister8)

---

**Made with 💜 and Claude Sonnet 4.5**
