/* Motion: reveal fallback, magnet, spotlight, decorative count-up. No rAF while idle. */
(() => {
  'use strict';
  const doc = document;
  const rm = matchMedia('(prefers-reduced-motion: reduce)'), fq = matchMedia('(hover: hover) and (pointer: fine)');
  const reduced = () => rm.matches;
  const fine = (e) => fq.matches && !reduced() && e.pointerType !== 'touch';
  const passive = { passive: true };
  const clamp = (v, max) => Math.max(-max, Math.min(max, v)).toFixed(2);
  const hasIO = 'IntersectionObserver' in window;
  const runs = new WeakMap();
  let epoch = 0; // scroll/resize invalidate cached rects

  // Decorative numbers only (inside aria-hidden). Real results never animate.
  function countUp(el, { from = 0, to, decimals = 2, duration = 700 } = {}) {
    if (!el?.closest('[aria-hidden="true"]')) return false;
    const end = Number(to), start = Number(from);
    if (!Number.isFinite(end) || !Number.isFinite(start)) return false;
    cancelAnimationFrame(runs.get(el));
    if (reduced() || !(duration > 0)) { el.textContent = end.toFixed(decimals); return true; }
    const began = performance.now();
    const step = (now) => {
      const t = Math.min(1, Math.max(0, (now - began) / duration));
      el.textContent = (start + (end - start) * (t < 1 ? 1 - 2 ** (-10 * t) : 1)).toFixed(decimals);
      if (t < 1) runs.set(el, requestAnimationFrame(step)); else runs.delete(el);
    };
    runs.set(el, requestAnimationFrame(step));
    return true;
  }

  // One rect read per gesture; moves only write custom properties.
  function track(el, move, leave) {
    let rect = null, seen = -1;
    el.addEventListener('pointermove', (e) => {
      if (!fine(e)) return;
      if (!rect || seen !== epoch) { rect = el.getBoundingClientRect(); seen = epoch; }
      move(e.clientX - rect.left, e.clientY - rect.top, rect);
    }, passive);
    el.addEventListener('pointerleave', () => { rect = null; leave?.(); }, passive);
  }
  const set = (el, props) => { for (const k in props) el.style.setProperty(k, props[k]); };

  const bindMagnetic = (el) => track(el, (x, y, r) => {
    if (el.matches(':focus-visible')) return;
    set(el, { '--mag-x': `${clamp((x - r.width / 2) * 0.25, 8)}px`, '--mag-y': `${clamp((y - r.height / 2) * 0.3, 6)}px`, '--mx': `${x.toFixed(1)}px`, '--my': `${y.toFixed(1)}px` });
  }, () => { el.style.removeProperty('--mag-x'); el.style.removeProperty('--mag-y'); });

  // px on HTML elements; % of the box on SVG (footer wordmark).
  const bindSpotlight = (el) => {
    const pct = el instanceof SVGElement;
    track(el, (x, y, r) => set(el, pct
      ? { '--mx': `${(x / r.width * 100).toFixed(2)}%`, '--my': `${(y / r.height * 100).toFixed(2)}%` }
      : { '--mx': `${x.toFixed(1)}px`, '--my': `${y.toFixed(1)}px` }));
  };

  // No scroll-driven animations: html.no-sda, then .is-in once in view.
  function initReveals() {
    const items = [...doc.querySelectorAll('.reveal')];
    if (!items.length || CSS.supports?.('animation-timeline: view()')) return;
    const show = (el) => el.classList.add('is-in');
    if (hasIO) {
      const io = new IntersectionObserver((entries) => entries.forEach((e) => {
        if (e.isIntersecting) { show(e.target); io.unobserve(e.target); }
      }), { threshold: 0.15, rootMargin: '99999px 0px -8% 0px' }); // passed by a jump = seen
      // On screen or above already: stays put.
      items.forEach((el) => { if (el.getBoundingClientRect().top < innerHeight) show(el); else io.observe(el); });
    } else items.forEach(show);
    doc.documentElement.classList.add('no-sda');
  }

  function initCounters() {
    const items = [...doc.querySelectorAll('[data-count-to]')].filter((el) => el.closest('[aria-hidden="true"]'));
    if (!items.length || reduced() || !hasIO) return;
    const places = (el) => {
      const n = parseInt(el.dataset.countDecimals, 10);
      return n >= 0 ? Math.min(6, n) : (el.dataset.countTo.split('.')[1] || '').length;
    };
    const io = new IntersectionObserver((entries) => entries.forEach(({ target: el, intersectionRatio }) => {
      if (intersectionRatio < 0.6) return;
      io.unobserve(el);
      countUp(el, { from: Number(el.dataset.countFrom) || 0, to: el.dataset.countTo, decimals: places(el) });
    }), { threshold: 0.6 });
    items.forEach((el) => { el.textContent = (Number(el.dataset.countFrom) || 0).toFixed(places(el)); io.observe(el); });
  }

  function init() {
    initReveals();
    const magnets = doc.querySelectorAll('[data-magnetic]'), spots = doc.querySelectorAll('[data-spotlight]');
    if (magnets.length || spots.length) {
      const bump = () => { epoch++; };
      addEventListener('scroll', bump, { passive: true, capture: true });
      addEventListener('resize', bump, passive);
      magnets.forEach(bindMagnetic);
      spots.forEach(bindSpotlight);
    }
    initCounters();
  }

  globalThis.Motion = Object.freeze({ reduced, countUp });
  if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', init, { once: true }); else init();
})();
