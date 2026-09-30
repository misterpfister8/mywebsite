/* Fictional SpasstoCSV walkthrough. No files, passwords, or network requests. */
(() => {
  'use strict';
  const demo = document.querySelector('[data-conversion-demo]');
  if (!demo) return;

  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const format = demo.querySelector('[data-conversion-format]');
  const example = demo.querySelector('[data-conversion-example]');
  const status = demo.querySelector('[data-conversion-status]');
  const run = demo.querySelector('[data-conversion-run]');
  const buttons = [...demo.querySelectorAll('[data-format]')];
  const steps = [...demo.querySelectorAll('[data-conversion-step]')];
  const pending = demo.querySelector('[data-conversion-pending]');
  const rows = [
    { name: 'Beispiel 1', url: 'https://example.com/1', username: 'demo.01' },
    { name: 'Beispiel 2', url: 'https://example.com/2', username: 'demo.02' },
  ];
  let selected = 'csv', playing = false, sequence = 0;
  const timers = new Set();

  function cancel() {
    sequence++;
    timers.forEach(clearTimeout); timers.clear();
    format.classList.remove('is-flipping');
  }
  function later(callback, delay) {
    const expected = sequence;
    const timer = setTimeout(() => {
      timers.delete(timer);
      if (sequence === expected) callback();
    }, delay);
    timers.add(timer);
  }
  function output() {
    if (selected === 'json') {
      const items = rows.map(row => ({ name: row.name, login: { username: row.username, uris: [{ uri: row.url }] } }));
      return '{"items":[\n' + items.map(item => '  ' + JSON.stringify(item)).join(',\n') + '\n]}';
    }
    return 'name,url,username\n' + rows.map(row => [row.name, row.url, row.username].join(',')).join('\n');
  }
  function stage(name, announce = true) {
    demo.dataset.conversionStage = name;
    const index = ['export', 'mapping', 'output'].indexOf(name);
    steps.forEach((step, i) => {
      step.dataset.state = i < index ? 'done' : i === index ? 'current' : 'waiting';
      if (i === index) step.setAttribute('aria-current', 'step');
      else step.removeAttribute('aria-current');
    });
    const messages = {
      export: '1 / Export · zwei erfundene Einträge laden.',
      mapping: '2 / Zuordnen · Titel, Adresse und Anmeldung werden Zielfelder.',
      output: `3 / Ausgabe · zwei Beispieldatensätze als ${selected === 'json' ? 'Bitwarden JSON' : 'CSV'}.`,
    };
    pending.textContent = name === 'export' ? 'Beispiel-Export laden …' : 'Felder neu zuordnen …';
    example.setAttribute('aria-hidden', String(name !== 'output'));
    // Initial paint must not generate a live-region announcement.
    if (announce || document.hidden) status.textContent = messages[name];
  }
  function complete(announce = true) {
    playing = false;
    demo.dataset.conversionPlaying = 'false';
    run.textContent = 'Beispiel durchspielen';
    stage('output', announce);
  }
  function play() {
    cancel();
    example.textContent = output();
    if (reduced.matches || document.hidden) { complete(); return; }
    playing = true;
    demo.dataset.conversionPlaying = 'true';
    run.textContent = 'Neu starten';
    stage('export');
    later(() => stage('mapping'), 700);
    later(() => complete(), 1900);
  }
  function select(name) {
    if (!['csv', 'json'].includes(name) || selected === name) return;
    const restart = playing;
    cancel(); selected = name;
    buttons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.format === name)));
    format.replaceChildren(document.createTextNode(name === 'json' ? '.json' : '.csv'));
    const label = document.createElement('small'); label.textContent = 'Dein Format'; format.append(label);
    demo.querySelectorAll('[data-conversion-key]').forEach(key => {
      key.textContent = key.dataset.conversionKey === 'url' && name === 'json' ? 'uri' : key.dataset.conversionKey;
    });
    example.textContent = output();
    if (restart) { play(); return; }
    complete();
    if (!reduced.matches) {
      format.classList.add('is-flipping');
      later(() => format.classList.remove('is-flipping'), 500);
    }
  }

  run.addEventListener('click', play);
  buttons.forEach(button => button.addEventListener('click', () => select(button.dataset.format)));
  demo.querySelector('.demo-tabs').addEventListener('keydown', event => {
    if (!['ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(event.key)) return;
    const focused = buttons.indexOf(document.activeElement);
    if (focused < 0) return;
    event.preventDefault();
    const index = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 : (focused + 1) % buttons.length;
    buttons[index].focus(); select(buttons[index].dataset.format);
  });
  reduced.addEventListener('change', () => {
    if (reduced.matches) { cancel(); complete(); }
  });
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) { cancel(); complete(false); }
  });
  format.addEventListener('animationend', () => format.classList.remove('is-flipping'));
  example.textContent = output();
  complete(false);
})();
