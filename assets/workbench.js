/* Home workbench: selection (single owner), HUD, label shortcuts, CSS tilt fallback, format demo. */
(() => {
  'use strict';
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const fine = matchMedia('(hover: hover) and (pointer: fine)');
  const bench = document.querySelector('[data-workbench]');
  if (bench) {
    const stage = bench.querySelector('.scene-stage'), scene = bench.querySelector('.scene');
    const link = bench.querySelector('[data-scene-link]'), note = bench.querySelector('[data-scene-note]');
    const hud = [bench.querySelector('[data-hud-channel]'), bench.querySelector('[data-hud-data]')];
    const visual = bench.closest('.hero-visual');
    const modules = {
      grade: { href: './sechserrechner/', label: 'Notenrechner öffnen', note: 'Beispiel: (4.5 + 5.5 + 5 + 6) ÷ 4 = 5.25.', hud: ['CH 01 · NOTEN', 'Ø 5.25 · 4 Noten'] },
      sleep: { href: './sleepcalculator/', label: 'Schlafrechner öffnen', note: 'Beispiel: 22:50 ins Bett, 10 min Einschlafen, 8 h Schlaf bis 07:00.', hud: ['CH 02 · SCHLAF', '22:50 → 07:00 · 8 h'] },
      code: { href: 'https://github.com/misterpfister8/spasstocsv', label: 'SpasstoCSV auf GitHub öffnen', note: 'Formatbeispiel: .spass zu CSV oder Bitwarden JSON. Der Konverter läuft lokal.', hud: ['CH 03 · DATEN', '.spass → .csv · lokal'] },
    };
    let visible = true, frame = 0, selectionUntil = 0;
    let x = 0, y = 0, tx = 0, ty = 0;
    const glLive = () => visual?.dataset.glassTier === 'live'; // engine owns the tilt
    const mayMove = () => !glLive() && !reduced.matches && fine.matches && visible && !document.hidden && performance.now() >= selectionUntil;
    function stop() {
      if (frame) cancelAnimationFrame(frame);
      frame = 0; x = y = tx = ty = 0;
      if (!glLive()) { stage.style.removeProperty('--tilt-x'); stage.style.removeProperty('--tilt-y'); }
    }
    function tick() {
      frame = 0;
      if (!mayMove()) { stop(); return; }
      x += (tx - x) * 0.15; y += (ty - y) * 0.15;
      stage.style.setProperty('--tilt-x', `${x.toFixed(3)}deg`);
      stage.style.setProperty('--tilt-y', `${y.toFixed(3)}deg`);
      if (Math.abs(tx - x) + Math.abs(ty - y) > 0.015) frame = requestAnimationFrame(tick);
    }
    const syncMotion = () => { if (!mayMove()) stop(); };
    function select(name, source = 'user') {
      const item = modules[name];
      if (!item) return;
      stop(); selectionUntil = performance.now() + 520;
      bench.dataset.selection = name;
      bench.querySelectorAll('[data-select]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.select === name)));
      link.href = item.href; link.setAttribute('aria-label', item.label);
      if (name === 'code') { link.target = '_blank'; link.rel = 'noopener noreferrer'; }
      else { link.removeAttribute('target'); link.removeAttribute('rel'); }
      note.textContent = item.note;
      hud.forEach((el, i) => { if (el) el.textContent = item.hud[i]; });
      bench.dispatchEvent(new CustomEvent('benchselect', { detail: { name, source } }));
    }
    bench.querySelectorAll('[data-select]').forEach(button => button.addEventListener('click', () => select(button.dataset.select)));
    bench.addEventListener('benchform', event => select(event.detail?.name, 'scroll'));
    // Back labels come forward first; the front one is a plain link
    bench.querySelectorAll('[data-module]').forEach(card => card.addEventListener('click', event => {
      if (card.dataset.module === bench.dataset.selection || event.metaKey || event.ctrlKey || event.shiftKey) return;
      event.preventDefault(); select(card.dataset.module);
    }));
    bench.querySelector('.scene-switches').addEventListener('keydown', event => {
      if (!['ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(event.key)) return;
      const buttons = [...bench.querySelectorAll('[data-select]')];
      let index = buttons.indexOf(document.activeElement);
      if (index < 0) return;
      event.preventDefault();
      index = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 : (index + (event.key === 'ArrowRight' ? 1 : -1) + buttons.length) % buttons.length;
      buttons[index].focus(); buttons[index].click();
    });
    scene.addEventListener('pointermove', event => {
      if (!mayMove() || event.pointerType === 'touch') return;
      const rect = scene.getBoundingClientRect();
      tx = ((event.clientX - rect.left) / rect.width - 0.5) * 7;
      ty = -((event.clientY - rect.top) / rect.height - 0.5) * 5;
      if (!frame) frame = requestAnimationFrame(tick);
    }, { passive: true });
    scene.addEventListener('pointerleave', () => { tx = ty = 0; if (mayMove() && !frame) frame = requestAnimationFrame(tick); });
    reduced.addEventListener('change', syncMotion); fine.addEventListener('change', syncMotion);
    if ('IntersectionObserver' in window) new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; if (!visible) stop(); }).observe(scene);
    document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); });
    syncMotion();

    // Back from a tool: preselect it. A fresh visit stays on grade.
    let from = '';
    try {
      const a = globalThis.navigation?.activation, url = new URL(a ? a.from?.url : document.referrer);
      if (url.origin === location.origin) from = url.pathname;
    } catch { /* no usable referrer */ }
    const initial = from.includes('/sleepcalculator/') ? 'sleep' : from.includes('/sechserrechner/') ? 'grade' : bench.dataset.selection;
    // Init jumps without label transition (style flushed in between)
    bench.classList.add('is-instant'); select(initial, 'init'); void bench.offsetWidth; bench.classList.remove('is-instant');
  }

  // VT arrival: keep the load choreography off once html.vt-arrival goes (it would replay)
  const html = document.documentElement, is = (c) => html.classList.contains(c);
  const arrived = () => { if (is('vt-arrival') && !is('vt-arrived')) html.classList.add('vt-arrived'); }; // guard: add() re-fires the observer
  arrived(); new MutationObserver(arrived).observe(html, { attributes: true, attributeFilter: ['class'] });
  // Card gauge follows the decorative count-up, so needle, centre value and number agree
  const gauge = document.querySelector('.card-grade .mini-gauge'), mean = gauge && document.querySelector('.card-grade [data-count-to]');
  const follow = () => {
    const n = parseFloat(mean.textContent);
    if (n >= 0) { gauge.style.setProperty('--v', Math.min(1, Math.max(0, (n - 1) / 5)).toFixed(4)); gauge.querySelector('.g-value').textContent = mean.textContent; }
  };
  if (mean) { follow(); new MutationObserver(follow).observe(mean, { childList: true }); }
})();
