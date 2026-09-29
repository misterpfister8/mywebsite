/* Cross-document view transitions; links stay native. */
(() => {
  'use strict';
  const root = document.documentElement, order = { home: 0, grade: 1, sleep: 2 };
  let clicked = null;
  document.addEventListener('click', (e) => {
    if (!(e.metaKey || e.ctrlKey || e.shiftKey || e.button)) clicked = e.target.closest?.('a[href]');
  }, true);
  const pageOf = (url) => {
    try {
      const { origin, pathname: p } = new URL(url, location.href);
      if (!url || origin !== location.origin) return null;
      return p.includes('/sechserrechner/') ? 'grade' : p.includes('/sleepcalculator/') ? 'sleep' : 'home';
    } catch { return null; }
  };
  const inView = (el) => {
    const r = el?.getClientRects().length && el.getBoundingClientRect();
    return !!r && r.bottom > 0 && r.top < innerHeight;
  };
  // Resize aborts reject ready. Reduced motion skips (false).
  function prepare(vt, from, to) {
    vt.ready.catch(() => {});
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) { vt.skipTransition(); return false; }
    if (from && to && from !== to) try { vt.types?.add(order[to] > order[from] ? 'forward' : 'back'); } catch {}
    return true;
  }
  // Home: card/label -> result panel, stage -> glyph.
  function nameHome(vt, tool, outgoing) {
    const $ = (s) => document.querySelector(s), bench = $('[data-workbench]'), stage = $('.glass-stage');
    const card = $(`[data-transition-card=${tool}]`), module = $(`[data-module=${tool}]`);
    const benchShown = !!bench?.getClientRects().length;
    let source;
    if (outgoing && clicked) {
      if (clicked.dataset.transitionCard === tool || clicked.dataset.module === tool) source = clicked;
      else if (clicked.matches('[data-scene-link]')) source = benchShown && inView(module) ? module : card;
    }
    source ||= inView(card) ? card : module;
    const form = benchShown ? bench.dataset.selection : $('.hero-visual')?.dataset.glassForm;
    const named = [[source, `${tool}-tool`], [inView(stage) && (!outgoing || form === tool) && stage, 'glass-core']].filter(([el]) => el);
    for (const [el, name] of named) el.style.viewTransitionName = name;
    const clean = () => named.forEach(([el]) => { el.style.viewTransitionName = ''; });
    vt.finished.then(clean, clean);
  }
  addEventListener('pageswap', (e) => {
    const vt = e.viewTransition, from = pageOf(location.href), to = pageOf(e.activation?.entry?.url);
    // vt-out: capture without hover chrome; cleared on reveal (bfcache return)
    if (vt && prepare(vt, from, to)) {
      root.classList.add('vt-out');
      if (from === 'home' && order[to] > 0) nameHome(vt, to, true);
    }
    clicked = null;
  });
  addEventListener('pagereveal', (e) => {
    root.classList.remove('vt-out');
    const vt = e.viewTransition, to = pageOf(location.href), from = pageOf(globalThis.navigation?.activation?.from?.url || document.referrer);
    if (!vt || !prepare(vt, from, to)) return;
    root.classList.add('vt-arrival');
    const done = () => root.classList.replace('vt-arrival', 'vt-arrived');
    vt.finished.then(done, done);
    if (to === 'home' && order[from] > 0) nameHome(vt, from, false);
  });
})();
