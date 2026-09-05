# Werkplatz 02 — verification, 2026-09-05

## Scope implemented

Homepage with functional navigation, selectable CSS-3D tool modules, pointer
smoothing without an idle render loop, pause/reduced motion, tool previews,
fictional format example and project explanation. Both calculators were rebuilt
around their results, with mobile layouts, optional local state, validation and
additional planning features. Points-to-grade is included. Network tools, PWA,
calendar/DST planning and accounts were deliberately not added in this iteration.

## Executed

- `node tests/math.test.js`: **11,203 assertions passed**. Includes weighted means,
  decimal parsing, rounding boundaries, algebraic target planning compared with
  brute-force grade-step enumeration, midnight rollover, sleep-duration limits,
  and linear points conversion.
- `python3 tests/browser_review.py --offline-fixture --chromium /usr/bin/chromium`:
  **94 assertions passed** in headless Chromium, with no page JavaScript errors.
- The browser fixture loads the actual local HTML/CSS/JS and executes real form,
  button, select, keyboard, file-import/export and SVG-update interactions. It
  substitutes an in-memory Storage implementation because this environment's
  browser policy rejects navigation to the local HTTP server.
- Both themes and all three pages checked at 320, 375, 402, 680, 768, 1024 and
  1440 CSS-pixel widths. No horizontal page overflow in these checks. Explicit
  checks cover the first mobile tool/input positions, reduced motion, motion
  pause, invalid data, undo, subjects, presets, opt-out, blocked Storage and
  imported text not becoming executable markup.
- Desktop/mobile screenshots inspected in both themes. Decorative perspective
  overflow and mobile touch/input sizing were corrected during the review.

## Not verified here

Real iPhone hardware, mobile Safari/desktop Safari, native iOS keyboard behaviour,
production FPS/Lighthouse measurements, cross-document transition playback,
real-origin localStorage, and complete live network navigation were **not**
verified by the offline fixture. Native Storage is not claimed to have been
end-to-end tested. Run the default HTTP test mode and check actual Apple devices
for these remaining integration checks.

The deployed source and GitHub Pages workflow are checked separately during
publication. A successful Pages deployment is not a substitute for a hardware
performance test. No 60-fps or Lighthouse score is claimed.

## Intentional limits

Sleep plans use clock times, not calendar dates, and do not create alarms or claim
medical precision. Grade rules are user-configurable, not a universal school
policy. No real password files are accepted by the SpasstoCSV illustration.
