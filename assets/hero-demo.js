/* Disposable sample controls: shared calculator math, no storage or real inputs. */
(() => {
  'use strict';
  const doc = document, M = globalThis.WorkshopMath;
  const panel = doc.querySelector('[data-hero-demo]'), bench = doc.querySelector('[data-workbench]');
  const visual = doc.querySelector('[data-glass]');
  if (!panel || !bench || !M) return;
  const grade = panel.querySelector('[data-demo-grade]'), sleep = panel.querySelector('[data-demo-sleep]');
  const material = panel.querySelector('[data-look-material]'), palette = panel.querySelector('[data-look-palette]');
  const light = panel.querySelector('[data-look-light]'), look = panel.querySelector('[data-look-panel]');
  const hint = visual.querySelector('[data-object-hint]');
  const base = M.summary([4.5, 5.5, 5, 6].map(value => ({grade: String(value), weight: '1'})));
  const write = (selector, value, scope = panel) => { const el = scope.querySelector(selector); if (el) el.textContent = value; };
  const modulo = n => ((n % 1440) + 1440) % 1440;
  const pt = (degrees, radius) => { const a = degrees * Math.PI / 180; return [24 + Math.sin(a) * radius, 24 - Math.cos(a) * radius]; };
  let sample;

  function sync() {
    const next = Number(grade.value), length = Number(sleep.value);
    const average = (base.sum + next) / (base.weight + 1);
    const night = M.sleepPlan('wake', '07:00', Math.floor(length / 60), length % 60, 10);
    sample = {average, length, wake: night.wake, bed: night.bed, onset: night.onset};
    write('[data-demo-grade-value]', next.toFixed(2));
    write('[data-demo-average]', M.round(average, .01).toFixed(2));
    write('[data-demo-duration]', M.duration(length));
    write('[data-demo-bed]', M.clock(night.bed));
    grade.setAttribute('aria-valuetext', `${next.toFixed(2)}; neuer Schnitt ${M.round(average, .01).toFixed(2)}`);
    sleep.setAttribute('aria-valuetext', `${M.duration(length)}; um ${M.clock(night.bed)} ins Bett`);
    grade.style.setProperty('--progress', `${(next - 1) / 5 * 100}%`);
    sleep.style.setProperty('--progress', `${(length - 360) / 180 * 100}%`);

    const score = bench.querySelector('.module-score');
    score.dataset.demoModuleAverage = '';
    const decimal = doc.createElement('span'); decimal.textContent = '.' + M.round(average, .01).toFixed(2).split('.')[1];
    score.replaceChildren(doc.createTextNode(String(Math.floor(M.round(average, .01)))), decimal);
    write('.module-grade-label', 'Beispiel · mit nächster Note', bench);
    const t = (average - 1) / 5;
    bench.querySelector('.mini-scale > i').style.insetInlineEnd = `${(1 - t) * 100}%`;
    bench.querySelector('.mini-scale > b').style.left = `${t * 100}%`;
    const bed = bench.querySelector('.mini-clock-read b');
    bed.dataset.demoModuleBed = ''; bed.textContent = M.clock(night.bed);
    const duration = bench.querySelector('.module-meta b');
    duration.dataset.demoModuleDuration = ''; duration.textContent = `${M.duration(length)} Schlaf`;
    const arc = bench.querySelector('.module-sleep circle[pathLength="100"]');
    arc.setAttribute('stroke-dasharray', `${length / 1440 * 100} ${100 - length / 1440 * 100}`);
    arc.setAttribute('transform', `rotate(${modulo(night.onset) / 4 - 90} 80 80)`);
    bench.querySelector('.module-sleep circle[pathLength="1440"]').setAttribute('transform', `rotate(${modulo(night.bed) / 4 - 90} 80 80)`);

    // SVG and WebGL represent the same sample, including disabled graphics.
    const gauge = visual.querySelector('.glass-fallback [data-form="grade"]');
    const [x, y] = pt(-135 + 270 * t, 16), [nx, ny] = pt(-135 + 270 * t, 10);
    gauge.querySelector('path[stroke="url(#fbFilmG)"]').setAttribute('d', `M12.69 35.31A16 16 0 ${t > 2 / 3 ? 1 : 0} 1 ${x.toFixed(3)} ${y.toFixed(3)}`);
    gauge.querySelector('path[stroke="var(--ink)"]').setAttribute('d', `M24 24 ${nx.toFixed(3)} ${ny.toFixed(3)}`);
    const bead = gauge.querySelector('circle[fill="url(#fbFilmG)"]'); bead.setAttribute('cx', x); bead.setAttribute('cy', y);
    const ring = visual.querySelector('.glass-fallback [data-form="sleep"]');
    const [sx, sy] = pt(modulo(night.onset) / 4, 17), [ex, ey] = pt(modulo(night.wake) / 4, 17);
    ring.querySelector('path[stroke="url(#fbFilmS)"]').setAttribute('d', `M${sx.toFixed(3)} ${sy.toFixed(3)}A17 17 0 ${length > 720 ? 1 : 0} 1 ${ex.toFixed(3)} ${ey.toFixed(3)}`);
    bench.dispatchEvent(new CustomEvent('benchdemo', {detail: sample}));
    selection();
  }

  function selection() {
    const name = bench.dataset.selection;
    panel.dataset.selection = name;
    panel.querySelectorAll('[data-demo-panel]').forEach(el => { el.hidden = el.dataset.demoPanel !== name; });
    if (!sample) return;
    const {average, length, bed} = sample;
    const texts = name === 'grade'
      ? [`Ø ${M.round(average, .01).toFixed(2)} · nächste ${Number(grade.value).toFixed(2)}`, `Beispiel: 4 Noten mit Schnitt 5.25 + eine ${Number(grade.value).toFixed(2)} → ${M.round(average, .01).toFixed(2)}.`]
      : name === 'sleep'
        ? [`${M.clock(bed)} → 07:00 · ${M.duration(length)}`, `Beispiel: ${M.clock(bed)} ins Bett, 10 min Einschlafen, ${M.duration(length)} Schlaf bis 07:00.`]
        : ['.spass → .csv / .json · lokal', 'Erfundene Daten. Den Formatwechsel weiter unten ausprobieren.'];
    write('[data-hud-data]', texts[0], bench);
    write('[data-scene-note]', texts[1], bench);
  }
  function appearance() {
    light.style.setProperty('--progress', `${(Number(light.value) + 100) / 2}%`);
    light.setAttribute('aria-valuetext', Number(light.value) === 0 ? 'Licht mittig' : `Licht ${Math.abs(Number(light.value))} % ${Number(light.value) < 0 ? 'links' : 'rechts'}`);
    bench.dispatchEvent(new CustomEvent('benchlook', {detail: {material: material.value, palette: palette.value, light: Number(light.value) / 100}}));
  }
  const input = name => { bench.querySelector(`[data-select="${name}"]`).click(); sync(); };
  // Focusing a sample must lock its form before keyboard scrolling can hide it.
  grade.addEventListener('focus', () => bench.querySelector('[data-select="grade"]').click());
  sleep.addEventListener('focus', () => bench.querySelector('[data-select="sleep"]').click());
  grade.addEventListener('input', () => input('grade')); sleep.addEventListener('input', () => input('sleep'));
  material.addEventListener('change', appearance); palette.addEventListener('change', appearance); light.addEventListener('input', appearance);
  panel.querySelector('[data-look-reset]').addEventListener('click', () => { material.value = 'default'; palette.value = 'original'; light.value = '0'; appearance(); });
  look.addEventListener('keydown', event => { if (event.key === 'Escape') { look.open = false; look.querySelector('summary').focus(); } });
  const availability = () => { look.hidden = !globalThis.HeroGL || visual.dataset.glassTier === 'fallback'; };
  new MutationObserver(availability).observe(visual, {attributes: true, attributeFilter: ['data-glass-tier']});
  bench.addEventListener('benchselect', selection);

  // Discovery hint disappears after an actual drag, without remembering visitors.
  let start = null;
  visual.addEventListener('pointerdown', event => { if (!event.target.closest('a,button,input,select,summary')) start = event.clientX; }, {passive: true});
  visual.addEventListener('pointermove', event => { if (start !== null && Math.abs(event.clientX - start) > 6) { hint.hidden = true; start = null; } }, {passive: true});
  visual.addEventListener('pointerup', () => { start = null; }, {passive: true});
  visual.addEventListener('pointercancel', () => { start = null; }, {passive: true});
  const open = bench.querySelector('[data-scene-link]');
  const openText = doc.createElement('span'); openText.className = 'scene-open-label'; openText.textContent = 'Tool öffnen'; open.prepend(openText);
  sync(); appearance(); availability(); panel.hidden = false;
})();
