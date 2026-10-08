/* Wisperpfister page: a finite dictation sample (listen → clean → done). Timers only, no rAF, nothing stored. */
(() => {
  'use strict';
  const demo = document.querySelector('[data-wisper-demo]');
  if (!demo) return;
  const words = [...demo.querySelectorAll('[data-word]')];
  const play = demo.querySelector('[data-wisper-play]'), status = demo.querySelector('[data-wisper-status]');
  const lines = {
    mac: { listen: 'Rechte ⌘ gehalten · Wisperpfister hört zu …', clean: 'Losgelassen · wird bereinigt …' },
    iphone: { listen: 'Mikrofon getippt · Wisperpfister hört zu …', clean: '«Fertig» getippt · wird bereinigt …' },
  };
  const done = 'Im Feld: Der Termin ist am Mittwoch.';
  const WORD = 190, START = 240, RELEASE = 260, CLEAN = 900;
  let timers = [];
  const later = (ms, fn) => timers.push(setTimeout(fn, ms));
  const stop = () => { timers.forEach(clearTimeout); timers = []; };
  const platform = () => (demo.querySelector('input[name=platform]:checked')?.value === 'iphone' ? 'iphone' : 'mac');
  const phase = (name, text) => { demo.dataset.phase = name; status.textContent = text; };

  function finish() {
    stop();
    words.forEach((w) => { w.dataset.on = ''; });
    phase('done', done);
  }

  function run() {
    stop();
    if (globalThis.Motion?.reduced() ?? matchMedia('(prefers-reduced-motion: reduce)').matches) { finish(); return; }
    const text = lines[platform()], spoken = START + words.length * WORD;
    words.forEach((w) => { delete w.dataset.on; });
    phase('listen', text.listen);
    words.forEach((w, i) => later(START + i * WORD, () => { w.dataset.on = ''; }));
    later(spoken + RELEASE, () => phase('clean', text.clean));
    later(spoken + RELEASE + CLEAN, finish);
  }

  play.addEventListener('click', run);
  // A platform switch mid-sample restarts it with that device's steps.
  demo.addEventListener('change', () => { if (demo.dataset.phase !== 'done') run(); });
  // Leaving the page (bfcache) settles the sample instead of resuming half-way.
  addEventListener('pagehide', () => { if (demo.dataset.phase !== 'done') finish(); });
})();
