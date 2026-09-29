/* Theme: set synchronously in <head>, persist the choice, reveal the new palette as a circle
   from the toggle (View Transitions) and announce it via the `themechange` event. */
(() => {
  'use strict';
  const root = document.documentElement;
  const storageKey = 'misterpfister-theme';
  const themeColors = { dark: '#0B0D0F', light: '#F2F3EE' };
  // Keyed by the theme the button switches to: sun means "go light", moon means "go dark".
  const themeIcons = {
    light: '<circle cx="12" cy="12" r="4.1"/><path d="M12 2.5v2.4M12 19.1v2.4M4.9 4.9l1.7 1.7M17.4 17.4l1.7 1.7M2.5 12h2.4M19.1 12h2.4M4.9 19.1l1.7-1.7M17.4 6.6l1.7-1.7"/>',
    dark: '<path d="M20 13a8.1 8.1 0 0 1-9-9 8.5 8.5 0 1 0 9 9Z"/>',
  };

  root.classList.add('js');
  let stored = null;
  try { stored = localStorage.getItem(storageKey); } catch { stored = null; }
  root.dataset.theme = stored === 'light' || stored === 'dark'
    ? stored
    : (matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');

  const current = () => (root.dataset.theme === 'light' ? 'light' : 'dark');
  const syncMeta = () => {
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = themeColors[current()];
  };
  syncMeta();

  function syncControls() {
    const next = current() === 'light' ? 'dark' : 'light';
    const label = next === 'light' ? 'Helles Farbschema verwenden' : 'Dunkles Farbschema verwenden';
    syncMeta();
    document.querySelectorAll('[data-theme-toggle]').forEach((button) => {
      button.setAttribute('aria-label', label);
      button.setAttribute('title', label);
      const text = button.querySelector('[data-theme-label]');
      if (text) text.textContent = next === 'light' ? 'Hell' : 'Dunkel';
      const icon = button.querySelector('[data-theme-icon]');
      if (icon) icon.innerHTML = themeIcons[next];
    });
  }

  // Sets the theme, persists it, syncs the controls, then dispatches `themechange` synchronously.
  function apply(theme) {
    root.classList.add('changing-theme'); // palette switches at once, no per-element cross-fades
    root.dataset.theme = theme;
    requestAnimationFrame(() => requestAnimationFrame(() => root.classList.remove('changing-theme')));
    try { localStorage.setItem(storageKey, theme); } catch { /* still applies for this page view */ }
    syncControls();
    document.dispatchEvent(new CustomEvent('themechange', { detail: { theme } }));
  }

  let running = null, pending = null, sequence = 0;
  function toggle(event) {
    // A second click while the circle runs ends it and flips from the pending theme.
    const next = (pending || current()) === 'light' ? 'dark' : 'light';
    const id = ++sequence;
    if (running || typeof document.startViewTransition !== 'function'
      || matchMedia('(prefers-reduced-motion: reduce)').matches || document.visibilityState !== 'visible') {
      running?.skipTransition();
      pending = null;
      apply(next);
      return;
    }
    const r = event.currentTarget.getBoundingClientRect();
    root.style.setProperty('--vt-x', `${Math.round(r.left + r.width / 2)}px`);
    root.style.setProperty('--vt-y', `${Math.round(r.top + r.height / 2)}px`);
    root.classList.add('theme-vt');
    pending = next;
    let vt;
    try {
      vt = document.startViewTransition(() => {
        if (id !== sequence) return;
        pending = null;
        apply(next);
      });
    } catch {
      pending = null;
      root.classList.remove('theme-vt');
      apply(next);
      return;
    }
    vt.ready.catch(() => {}); // a skipped circle rejects `ready`; expected
    running = vt;
    const done = () => {
      if (running === vt) running = null;
      root.classList.remove('theme-vt');
    };
    vt.finished.then(done, done);
  }

  function init() {
    syncControls();
    document.querySelectorAll('[data-theme-toggle]').forEach((button) => button.addEventListener('click', toggle));
    root.classList.add('theme-enabled');
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();
})();
