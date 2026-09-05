/* Progressive enhancement only: links and content remain normal HTML. */
(() => {
  'use strict';
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const fine = matchMedia('(hover: hover) and (pointer: fine)');
  const bench = document.querySelector('[data-workbench]');
  if (bench) {
    const stage = bench.querySelector('.scene-stage');
    const scene = bench.querySelector('.scene');
    const toggle = bench.querySelector('[data-motion-toggle]');
    const link = bench.querySelector('[data-scene-link]');
    const note = bench.querySelector('[data-scene-note]');
    const modules = {
      grade: { href: './sechserrechner/', label: 'Notenrechner öffnen', note: 'Beispiel: (4.5 + 5.5 + 5 + 6) ÷ 4 = 5.25.' },
      sleep: { href: './sleepcalculator/', label: 'Schlafrechner öffnen', note: 'Beispiel: 22:45 ins Bett, 15 min Einschlafen, 8 h Schlaf bis 07:00.' },
      code: { href: 'https://github.com/misterpfister8/spasstocsv', label: 'SpasstoCSV auf GitHub öffnen', note: 'Formatbeispiel: .spass zu CSV oder Bitwarden JSON. Der Konverter läuft lokal.' },
    };
    let paused = false, visible = true, frame = 0, selectionUntil = 0;
    let x = 0, y = 0, tx = 0, ty = 0;
    const mayMove = () => !paused && !reduced.matches && fine.matches && visible && !document.hidden && performance.now() >= selectionUntil;
    function stop() {
      if (frame) cancelAnimationFrame(frame);
      frame = 0; x = y = tx = ty = 0;
      stage.style.willChange = 'auto';
      stage.style.removeProperty('--tilt-x'); stage.style.removeProperty('--tilt-y');
    }
    function tick() {
      frame = 0;
      if (!mayMove()) { stop(); return; }
      x += (tx - x) * 0.15; y += (ty - y) * 0.15;
      stage.style.willChange = 'transform';
      stage.style.setProperty('--tilt-x', `${x.toFixed(3)}deg`);
      stage.style.setProperty('--tilt-y', `${y.toFixed(3)}deg`);
      if (Math.abs(tx - x) + Math.abs(ty - y) > 0.015) frame = requestAnimationFrame(tick);
      else stage.style.willChange = 'auto';
    }
    function syncMotion() {
      bench.classList.toggle('motion-paused', paused || reduced.matches);
      toggle.hidden = reduced.matches;
      toggle.setAttribute('aria-pressed', String(paused));
      toggle.textContent = paused ? 'Bewegung starten' : 'Bewegung pausieren';
      if (!mayMove()) stop();
    }
    function select(name) {
      if (!modules[name]) return;
      stop(); selectionUntil = performance.now() + 520;
      bench.dataset.selection = name;
      bench.querySelectorAll('[data-module],[data-select]').forEach(button => button.setAttribute('aria-pressed', String((button.dataset.module || button.dataset.select) === name)));
      link.href = modules[name].href; link.setAttribute('aria-label', modules[name].label);
      if (name === 'code') { link.target = '_blank'; link.rel = 'noopener noreferrer'; }
      else { link.removeAttribute('target'); link.removeAttribute('rel'); }
      note.textContent = modules[name].note;
    }
    bench.querySelectorAll('[data-module],[data-select]').forEach(button => button.addEventListener('click', () => select(button.dataset.module || button.dataset.select)));
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
    toggle.addEventListener('click', () => { paused = !paused; syncMotion(); });
    reduced.addEventListener('change', syncMotion); fine.addEventListener('change', syncMotion);
    if ('IntersectionObserver' in window) new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; if (!visible) stop(); }).observe(scene);
    document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); });
    syncMotion();
  }
  document.querySelectorAll('[data-format]').forEach(button => button.addEventListener('click', () => {
    const json = button.dataset.format === 'json';
    document.querySelectorAll('[data-format]').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
    const format = document.querySelector('[data-conversion-format]');
    format.replaceChildren(document.createTextNode(json ? '.json' : '.csv'));
    const small = document.createElement('small'); small.textContent = 'Dein Format'; format.append(small);
    document.querySelector('[data-conversion-example]').textContent = json ? '{"name":"Beispiel","login":{"username":"demo"}}' : 'name,url,username\nBeispiel,https://example.com,demo';
  }));
})();
