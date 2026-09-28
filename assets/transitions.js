/* Native links stay native; only their visible preview joins the transition. */
(() => {
  'use strict';
  let clicked = null;
  document.addEventListener('click', event => {
    if (!event.metaKey && !event.ctrlKey && !event.shiftKey && event.button === 0) {
      clicked = event.target.closest('a[href]');
    }
  });
  const toolFor = url => {
    if (!url) return null;
    const path = new URL(url, location.href).pathname;
    return path.includes('/sechserrechner/') ? 'grade' : path.includes('/sleepcalculator/') ? 'sleep' : null;
  };
  function namePreview(event, tool, outgoing) {
    if (!event.viewTransition || !tool || !document.querySelector('[data-workbench]')) return;
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) { event.viewTransition.skipTransition(); return; }
    const card = document.querySelector(`[data-transition-card="${tool}"]`);
    const rect = card.getBoundingClientRect();
    const visible = rect.top < innerHeight && rect.bottom > 0;
    // Morph from the element that was actually clicked when it shows this tool.
    const own = outgoing && clicked && (clicked.dataset.transitionCard === tool || clicked.dataset.module === tool) ? clicked : null;
    const source = own || (visible ? card : document.querySelector(`[data-module="${tool}"]`));
    source.style.viewTransitionName = `${tool}-tool`;
    const cleanup = () => source.style.removeProperty('view-transition-name');
    event.viewTransition.finished.then(cleanup, cleanup);
  }
  addEventListener('pageswap', event => namePreview(event, toolFor(event.activation?.entry.url), true));
  addEventListener('pagereveal', event => namePreview(event, toolFor(globalThis.navigation?.activation?.from?.url), false));
})();
