/* Local-only grade workspace. User strings are inserted with textContent/value. */
(() => {
  'use strict';
  const q = selector => document.querySelector(selector);
  if (!q('[data-grade-app]')) return;
  const M = globalThis.WorkshopMath;
  const $ = id => document.getElementById(id);
  const KEY = 'misterpfister-grades-v2', PREF = 'misterpfister-grades-saving';
  const MAX_SUBJECTS = 30, MAX_ROWS = 100;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)'), wide = matchMedia('(min-width: 901px)');
  const smooth = () => (reduced.matches ? 'auto' : 'smooth');
  const clone = object => JSON.parse(JSON.stringify(object));
  const inRange = (value, low, high) => Number.isFinite(value) && value >= low && value <= high;
  const num = new Intl.NumberFormat('de-CH', { maximumFractionDigits: 2 }).format;
  const make = (tag, className = '', content = null) => Object.assign(document.createElement(tag), className && { className }, content !== null && { textContent: content });
  const setVar = (el, name, value) => el.style.setProperty(name, Number(value).toFixed(4));
  const emptyRow = () => ({ name: '', grade: '', weight: '1' });
  const newSubject = (name = 'Allgemein') => ({ name, entries: [emptyRow(), emptyRow()], rounding: '0.01', gradeStep: '0.01', target: '4.00', nextWeight: '1', scenario: '5.00', basis: 'exact' });
  const FIELDS = [['rounding', 'rounding'], ['gradeStep', 'gradeStep'], ['targetAverage', 'target'], ['nextWeight', 'nextWeight'], ['scenarioGrade', 'scenario'], ['targetBasis', 'basis']];
  const scale = $('gradeScale'), chart = $('entryChart'), bars = chart.querySelector('.chart-bars'), pool = [];
  const metric = q('.grade-metric'), wrap = q('.gauge-wrap'), slider = $('scenarioSlider'), list = $('gradeEntries');
  const chips = document.querySelectorAll('[data-next-weight]');
  const toastBox = $('gradeToast'), select = $('subjectSelect'), arc = $('scenarioArc').style;
  const flag = (el, bad) => el.setAttribute('aria-invalid', String(bad));
  const label = value => scale.setAttribute('aria-label', value);
  const twoFrames = fn => requestAnimationFrame(() => requestAnimationFrame(fn));
  const EMPTY_MODEL = { type: 'misterpfister-grades', version: 1 };
  let model = { ...EMPTY_MODEL, active: 0, subjects: [newSubject()] };
  let current = null, undo = null, undoAfter = null, persistent = true, lastGrade = null;
  function validateImport(data, drafts = false) {
    const fail = message => { throw new Error(message); };
    if (!data || data.type !== 'misterpfister-grades' || data.version !== 1 || !Array.isArray(data.subjects) || !data.subjects.length || data.subjects.length > MAX_SUBJECTS) fail('Keine gültige Noten-Sicherungsdatei.');
    const subjects = data.subjects.map(s => {
      if (!s || typeof s.name !== 'string' || !s.name.trim() || s.name.length > 60 || !Array.isArray(s.entries) || !s.entries.length || s.entries.length > MAX_ROWS) fail('Ungültiges Fach oder zu viele Noten.');
      const result = newSubject(s.name.trim());
      result.entries = s.entries.map(row => {
        if (!row || ['name', 'grade', 'weight'].some(k => typeof row[k] !== 'string' || row[k].length > (k === 'name' ? 120 : 20))) fail('Ungültige Notenzeile.');
        if (!drafts && row.grade.trim() && !inRange(M.decimal(row.grade), 1, 6)) fail('Noten müssen zwischen 1 und 6 liegen.');
        if (!drafts && !inRange(M.decimal(row.weight), .01, 100)) fail('Ungültiges Gewicht in der Sicherung.');
        return { name: row.name, grade: row.grade, weight: row.weight };
      });
      if (!['0.01', '0.1', '0.5', '1'].includes(s.rounding) || !['0.01', '0.1', '0.25', '0.5', '1'].includes(s.gradeStep) || !['exact', 'display'].includes(s.basis)) fail('Ungültige Rundungsregel.');
      // Older saves carry scenarioWeight; the simulation now uses the next grade's weight.
      for (const [key, max] of [['target', 6], ['nextWeight', 100], ['scenario', 6]]) {
        const input = s[key];
        if (typeof input !== 'string' || input.length > 20 || (!drafts && !inRange(M.decimal(input), key === 'nextWeight' ? .01 : 1, max))) fail('Ungültige Planungseinstellung.');
        result[key] = input;
      }
      result.rounding = s.rounding; result.gradeStep = s.gradeStep; result.basis = s.basis;
      return result;
    });
    return { ...EMPTY_MODEL, active: Number.isInteger(data.active) && data.active >= 0 && data.active < subjects.length ? data.active : 0, subjects };
  }
  const storage = globalThis.WorkshopStorage(KEY, PREF, data => validateImport(data, true));
  const restored = storage.load();
  persistent = restored.enabled;
  if (restored.data) model = restored.data;
  $('saveGrades').checked = persistent;
  const active = () => model.subjects[model.active];
  function persist() {
    const result = storage.save(persistent, model);
    $('saveStatus').textContent = result.text;
    $('saveStatus').dataset.error = String(result.error);
  }
  const text = (id, value) => { $(id).textContent = value; };
  function result(id, value, placeholder = '-.--') {
    text(id, value ?? placeholder);
    $(id).dataset.state = value === null ? 'empty' : '';
  }
  function glint() {
    if (reduced.matches) return;
    metric.classList.remove('is-glint'); void metric.offsetWidth; metric.classList.add('is-glint');
  }
  metric.addEventListener('animationend', () => metric.classList.remove('is-glint'));
  let toastTimer = 0;
  const toastFixed = () => getComputedStyle(toastBox).position === 'fixed';
  function toastLater(delay = 10000) {
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      if (toastBox.hidden || !toastFixed()) return;
      if (toastBox.matches(':hover, :focus-within')) toastLater(3000); else toastBox.hidden = true;
    }, delay);
  }
  function toast(message, canUndo = false) {
    text('toastMessage', message); toastLater();
    $('undoAction').hidden = !canUndo;
    if (canUndo) undoAfter = JSON.stringify(model);
    toastBox.hidden = false;
    // Phones: the notice sits in the panel flow, so bring it into view.
    const box = toastBox.getBoundingClientRect();
    if (box.top < 0 || box.bottom > innerHeight) toastBox.scrollIntoView({ block: 'nearest', behavior: smooth() });
  }
  function checkpoint() { undo = clone(model); }
  function renderSubjects() {
    select.replaceChildren(...model.subjects.map((subject, index) => {
      const option = make('option', '', subject.name); option.value = String(index); return option;
    }));
    select.value = String(model.active);
    $('renameSubject').value = active().name;
    text('resultSubject', active().name);
  }
  const closeIcon = $('cancelSubject').querySelector('svg');
  function renderRows(focusIndex = null) {
    list.replaceChildren();
    active().entries.forEach((entry, index) => {
      const row = make('div', 'grade-row');
      for (const [key, label, placeholder] of [['name', `Prüfung ${index + 1} (optional)`, 'Prüfung'], ['grade', `Note ${index + 1}`, 'Note'], ['weight', `Gewicht ${index + 1}`, '1']]) {
        const input = Object.assign(make('input', `grade-${key}`), { type: 'text', value: entry[key], placeholder, autocomplete: 'off', maxLength: key === 'name' ? 120 : 20, enterKeyHint: 'next' });
        input.setAttribute('aria-label', label);
        if (key !== 'name') input.inputMode = 'decimal';
        input.addEventListener('input', () => { entry[key] = input.value; compute(); persist(); });
        if (key === 'weight') {
          const cell = make('span', 'weight-cell'), sign = make('span', '', '×');
          sign.setAttribute('aria-hidden', 'true'); cell.append(sign, input); row.append(cell);
        } else row.append(input);
      }
      const remove = Object.assign(make('button', 'icon-button'), { type: 'button' }); remove.setAttribute('aria-label', `Note ${index + 1} entfernen`);
      remove.append(closeIcon.cloneNode(true));
      remove.addEventListener('click', event => {
        checkpoint(); active().entries.splice(index, 1);
        if (!active().entries.length) active().entries.push(emptyRow());
        // Keyboard: next row. Tap: "Rückgängig", so the phone keyboard stays closed.
        renderRows(event.detail === 0 ? Math.min(index, active().entries.length - 1) : null); compute(); persist(); toast('Note entfernt.', true);
        if (event.detail !== 0) $('undoAction').focus({ preventScroll: true });
      });
      row.append(remove); list.append(row);
    });
    if (focusIndex !== null) list.children[focusIndex]?.querySelector('.grade-grade').focus();
    $('addEntry').disabled = active().entries.length >= MAX_ROWS;
  }
  const syncSlider = () => setVar(slider, '--p', (Number(slider.value) - 1) / 5);
  function populate() {
    renderSubjects(); renderRows();
    const s = active();
    for (const [id, key] of FIELDS) $(id).value = s[key];
    slider.step = s.gradeStep; slider.value = s.scenario; syncSlider();
    compute();
  }
  function compute() {
    const s = active(); let invalid = false;
    [...list.children].forEach((row, index) => {
      const e = s.entries[index], filled = e.grade.trim() !== '';
      const badGrade = filled && !inRange(M.decimal(e.grade), 1, 6), badWeight = filled && !inRange(M.decimal(e.weight), .01, 100);
      flag(row.querySelector('.grade-grade'), badGrade); flag(row.querySelector('.grade-weight'), badWeight);
      if (badGrade || badWeight) invalid = true;
    });
    text('gradeError', invalid ? 'Noten: 1–6. Gewicht: 0.01–100. Jeweils höchstens zwei Dezimalstellen.' : '');
    try { current = invalid ? null : M.summary(s.entries); } catch { current = null; }
    const shown = current && M.round(current.average, Number(s.rounding)).toFixed(2);
    $('resultExample').hidden = Boolean(current) || invalid;
    $('scalePointer').hidden = !current;
    if (!current) {
      result('average', null); text('averageDetail', invalid ? 'Bitte Eingaben prüfen.' : 'Trage deine erste Note ein.');
      text('averageExact', ''); text('gradeCount', invalid ? 'Eingabe prüfen' : 'Noch keine Noten');
      $('gradeCount').dataset.state = invalid ? 'invalid' : 'empty';
      label('Notenskala von 1 bis 6. Noch kein gültiges Ergebnis.');
    } else {
      result('average', shown);
      text('averageDetail', `Gewicht ${num(current.weight)} · Rundung ${s.rounding}`);
      text('averageExact', `Rechenwert ≈ ${current.average.toFixed(4)}`);
      text('gradeCount', `${current.count} ${current.count === 1 ? 'Note' : 'Noten'}`);
      $('gradeCount').dataset.state = '';
      label(`Notenskala 1 bis 6. Ungerundeter Schnitt ${current.average.toFixed(4)}.`);
    }
    // Gauge fill and bead share t in 0..1.
    const t = current ? (current.average - 1) / 5 : 0;
    setVar(scale, '--avg', t);
    $('scaleFill').style.strokeDasharray = `${(t * 75).toFixed(3)} 100`;
    wrap.classList.toggle('is-empty', !current);
    updatePlan();
    renderOverview();
  }
  function updatePlan() {
    const s = active(), next = M.decimal(s.nextWeight), simulated = M.decimal(s.scenario), target = M.decimal(s.target), r = Number(s.rounding), step = Number(s.gradeStep);
    const validWeight = inRange(next, .01, 100), validTarget = inRange(target, 1, 6);
    const validSim = inRange(simulated, 1, 6) && Math.abs((simulated - 1) / step - Math.round((simulated - 1) / step)) < 1e-7;
    flag($('nextWeight'), !validWeight); flag($('scenarioGrade'), !validSim); flag($('targetAverage'), !validTarget);
    text('scenarioWeightLabel', validWeight ? `mit Gewicht ${s.nextWeight}` : 'Gewicht prüfen');
    chips.forEach(chip => chip.setAttribute('aria-pressed', String(validWeight && Number(chip.dataset.nextWeight) === next)));
    let sim = null, need = null, delta = null;
    $('scenarioPointer').hidden = !(current && validWeight && validSim);
    if (current && validWeight && validSim) {
      const projected = (current.sum + simulated * next) / (current.weight + next), t = (current.average - 1) / 5, p = (projected - 1) / 5;
      result('scenarioResult', M.round(projected, r).toFixed(2));
      text('scenarioHint', `Rechenwert ≈ ${projected.toFixed(4)}. Simulation, keine gespeicherte Prüfung.`);
      label(`Skala 1 bis 6. Aktuell ${current.average.toFixed(4)}, simuliert ${projected.toFixed(4)}. 4 ist eine Orientierung, keine Bestehensgarantie.`);
      setVar(scale, '--sim', p);
      arc.strokeDasharray = `0 ${(Math.min(t, p) * 75).toFixed(3)} ${(Math.abs(p - t) * 75).toFixed(3)} 100`;
      delta = M.round(projected, r) - M.round(current.average, r); sim = [simulated, next];
    } else {
      result('scenarioResult', null); text('scenarioHint', current ? `Nächste Note in ${s.gradeStep}er-Schritten und gültiges Gewicht eingeben.` : 'Mindestens eine gültige aktuelle Note eingeben.');
      arc.strokeDasharray = '0 0 0 100';
    }
    const dir = delta === null ? 'none' : Math.abs(delta) < .005 ? 'flat' : delta > 0 ? 'up' : 'down';
    $('scenarioDelta').dataset.dir = dir;
    text('scenarioDelta', dir === 'none' ? '' : `${{ up: '▲ +', down: '▼ −', flat: '= ' }[dir]}${Math.abs(delta).toFixed(2)} ggü. jetzt`);
    $('targetPointer').hidden = !validTarget;
    if (validTarget) setVar(scale, '--target', (target - 1) / 5);
    let say = ['Zuerst eine gültige aktuelle Note eingeben.', '', 'Der Planer berücksichtigt deine gewählten Notenschritte.'];
    if (current && !(validWeight && validTarget)) {
      say = [!validTarget && !validWeight ? 'Zielschnitt und Gewicht prüfen.' : !validTarget ? 'Zielschnitt prüfen.' : 'Gewicht der nächsten Note prüfen.', 'danger',
        [!validTarget && 'Zielschnitt: 1–6.', !validWeight && 'Gewicht: 0.01–100.'].filter(Boolean).join(' ') + ' Höchstens 2 Dezimalstellen.'];
    } else if (current) {
      const plan = M.neededGrade(current, target, next, step, r, s.basis);
      say = !plan.possible ? ['Selbst eine 6.00 reicht als nächste Note nicht.', 'danger'] : plan.secured ? ['Mit jeder nächsten Note ab 1.00 erreicht.', 'secured'] : [`Du brauchst mindestens eine ${plan.required.toFixed(2)}.`, ''];
      if (plan.possible && !plan.secured) need = plan.required;
      const best = (current.sum + 6 * next) / (current.weight + next);
      const how = plan.secured ? 'Ziel auch mit der Mindestnote erreicht' : !plan.possible
        ? `Mit einer 6.00 höchstens ${s.basis === 'display' ? M.round(best, r).toFixed(2) : `≈ ${best.toFixed(4)}`}` : `Rechnerisch ${plan.raw.toFixed(3)}`;
      say[2] = `${how} · ${s.gradeStep}er-Schritte · Ziel für ${s.basis === 'display' ? 'die gerundete Anzeige' : 'den ungerundeten Schnitt'}.`;
    }
    text('targetResult', say[0]); text('targetDetail', say[2]);
    if (say[1]) $('targetResult').dataset.tone = say[1]; else $('targetResult').removeAttribute('data-tone');
    renderChart(sim, need);
    // Compact bar: the average, plus the simulation where the bar has room for it.
    const compact = $('compactAverage');
    compact.textContent = current ? `Schnitt ${M.round(current.average, r).toFixed(2)}` : 'Noch kein gültiger Schnitt';
    if (current) compact.append(make('span', 'compact-count', ` · ${current.count} ${current.count === 1 ? 'Note' : 'Noten'}`));
    if (sim) compact.append(make('span', 'compact-sim', ` · Simulation ${$('scenarioResult').textContent}`));
  }
  // Bars: width = weight, height = grade; dashed ghost = simulation.
  function renderChart(sim, need) {
    const s = active(), data = [];
    for (const e of s.entries) {
      const g = M.decimal(e.grade), w = M.decimal(e.weight);
      if (e.grade.trim() && inRange(g, 1, 6) && inRange(w, .01, 100)) data.push([g, w, '']);
    }
    const real = data.length;
    if (sim && real) data.push([...sim, 'is-ghost']);
    while (pool.length < data.length) pool.push(make('i'));
    pool.forEach((bar, index) => {
      const d = data[index];
      if (!d) { bar.remove(); return; }
      bar.className = d[2]; setVar(bar, '--h', (d[0] - 1) / 5); bar.style.setProperty('--w', d[1]);
      if (!bar.isConnected) bars.append(bar);
    });
    chart.dataset.empty = String(!real);
    chart.dataset.invalid = String(!current && real > 0);
    chart.toggleAttribute('data-dense', data.length > 30);
    for (const [name, value] of [['is-avg', current && M.round(current.average, Number(s.rounding))], ['is-need', need]]) {
      const line = chart.querySelector(`.${name}`);
      line.hidden = !value;
      if (value) setVar(line, '--h', (value - 1) / 5);
      if (value && name === 'is-avg') line.dataset.label = `Ø ${value.toFixed(2)}`;
    }
  }
  function renderOverview() {
    const link = $('subjectSummary'), n = model.subjects.length, rounded = [];
    $('overviewPanel').hidden = link.hidden = n < 2;
    delete document.documentElement.dataset.gradeMulti;
    if (n < 2) return;
    $('overviewRows').replaceChildren(...model.subjects.map((subject, index) => {
      let summary = null, invalid = false;
      try { summary = M.summary(subject.entries); } catch { invalid = true; }
      const value = summary ? M.round(summary.average, Number(subject.rounding)) : null;
      if (value !== null) rounded.push(value);
      const row = make('tr'), name = make('th'), open = make('button', 'text-button', subject.name), bar = make('span', 'ov-bar'), average = make('td');
      name.scope = 'row'; open.type = 'button'; bar.setAttribute('aria-hidden', 'true');
      open.addEventListener('click', event => {
        model.active = index; populate(); persist(); glint();
        q('.calculator-layout').scrollIntoView({ block: 'start', behavior: smooth() });
        if (event.detail === 0) select.focus();
      });
      name.append(open);
      if (index === model.active) { row.setAttribute('aria-current', 'true'); name.append(make('small', 'tag', 'Aktiv')); }
      if (value !== null) setVar(bar, '--v', (value - 1) / 5);
      average.append(bar, invalid ? 'prüfen' : value === null ? '–' : value.toFixed(2));
      row.append(name, make('td', '', String(summary ? summary.count : 0)), average);
      return row;
    }));
    const mean = rounded.length ? M.round(rounded.reduce((sum, value) => sum + value, 0) / rounded.length, .01).toFixed(2) : null;
    text('overviewAverage', mean ?? '–');
    text('overviewCount', `${rounded.length} von ${n} mit Noten`);
    link.textContent = mean ? `${n} Fächer · Gesamt ${mean} ↓` : `${n} Fächer ↓`;
  }
  $('addEntry').addEventListener('click', () => {
    if (active().entries.length >= MAX_ROWS) return;
    active().entries.push(emptyRow()); renderRows(active().entries.length - 1); compute(); persist();
    const row = list.lastElementChild;
    if (!reduced.matches && row.animate) row.animate([{ opacity: 0, transform: 'translateY(-8px)' }, { opacity: 1, transform: 'translateY(0)' }], { duration: 220, easing: 'ease-out' });
  });
  // Enter: name → its grade; grade or weight → next row's grade.
  $('gradeForm').addEventListener('submit', event => {
    event.preventDefault(); compute();
    const input = document.activeElement, row = input?.closest?.('.grade-row');
    if (!row) return;
    const rows = [...list.children], index = rows.indexOf(row);
    if (input.classList.contains('grade-name')) row.querySelector('.grade-grade').focus();
    else if (index < rows.length - 1) rows[index + 1].querySelector('.grade-grade').focus();
    else if (active().entries[index].grade.trim() && active().entries.length < MAX_ROWS) $('addEntry').click();
  });
  list.addEventListener('focusin', ({ target }) => { if (target.matches('.grade-grade')) lastGrade = [...list.children].indexOf(target.closest('.grade-row')); });
  select.addEventListener('change', () => { model.active = Number(select.value); populate(); persist(); glint(); });
  $('addSubject').addEventListener('click', () => {
    if (model.subjects.length >= MAX_SUBJECTS) { toast(`Höchstens ${MAX_SUBJECTS} Fächer möglich.`); return; }
    $('subjectForm').hidden = false; $('subjectName').focus();
  });
  $('cancelSubject').addEventListener('click', () => { $('subjectForm').hidden = true; $('addSubject').focus(); });
  $('subjectForm').addEventListener('keydown', event => { if (event.key === 'Escape') { event.preventDefault(); $('cancelSubject').click(); } });
  $('subjectForm').addEventListener('submit', event => {
    event.preventDefault(); const name = $('subjectName').value.trim();
    if (!name || model.subjects.length >= MAX_SUBJECTS) { $('subjectName').focus(); return; }
    model.subjects.push(newSubject(name.slice(0, 60))); model.active = model.subjects.length - 1;
    $('subjectName').value = ''; $('subjectForm').hidden = true; populate(); persist(); list.querySelector('.grade-grade').focus();
  });
  // Opens "Fach & Datensicherung" instantly and focuses it.
  $('openSubjectSettings').addEventListener('click', () => {
    const details = $('subjectSettings');
    details.classList.add('is-instant'); details.open = true;
    details.scrollIntoView({ block: 'nearest', behavior: smooth() });
    details.querySelector('summary').focus({ preventScroll: true });
    twoFrames(() => details.classList.remove('is-instant'));
  });
  $('renameSubject').addEventListener('change', () => {
    const name = $('renameSubject').value.trim(); if (name) active().name = name.slice(0, 60); renderSubjects(); renderOverview(); persist();
  });
  $('deleteSubject').addEventListener('click', () => {
    const count = active().entries.filter(entry => entry.grade.trim()).length;
    if (!confirm(`Fach «${active().name}»${count ? ` mit ${count} ${count === 1 ? 'Note' : 'Noten'}` : ''} löschen?`)) return;
    checkpoint(); model.subjects.splice(model.active, 1);
    if (!model.subjects.length) model.subjects.push(newSubject());
    model.active = Math.min(model.active, model.subjects.length - 1); populate(); persist(); toast('Fach gelöscht.', true);
  });
  const EXAMPLE = ['4.5', '5.5', '5', '6'].map((grade, i) => ({ name: `Prüfung ${i + 1}`, grade, weight: '1' }));
  $('loadExample').addEventListener('click', () => {
    const own = active().entries.some(entry => entry.grade.trim()) && JSON.stringify(active().entries) !== JSON.stringify(EXAMPLE);
    if (own && model.subjects.length >= MAX_SUBJECTS) { toast(`Höchstens ${MAX_SUBJECTS} Fächer: für das Beispiel zuerst ein Fach löschen.`); return; }
    checkpoint();
    // Own grades stay untouched: the example opens as its own subject.
    if (own) { model.subjects.push(newSubject('Beispiel')); model.active = model.subjects.length - 1; }
    active().entries = clone(EXAMPLE);
    if (own) populate(); else { renderRows(); compute(); }
    persist(); toast(own ? 'Beispiel als neues Fach «Beispiel» geöffnet.' : 'Beispielnoten eingesetzt.', true); glint();
  });
  $('resultExample').addEventListener('click', () => {
    $('loadExample').click();
    // The entry action disappears after loading; focus moves to a visible result.
    $('result-title').setAttribute('tabindex', '-1'); $('result-title').focus({preventScroll: true});
  });
  // Focus never falls back to <body>: keyboard → a grade, pointer → "Note hinzufügen".
  function afterToast(event, index = lastGrade) {
    const grade = event.detail === 0 && index !== null && list.children[index]?.querySelector('.grade-grade');
    if (grade) grade.focus(); else $('addEntry').focus({ preventScroll: true });
  }
  $('undoAction').addEventListener('click', event => {
    if (undo) {
      if (undoAfter !== JSON.stringify(model) && !confirm('Inzwischen hast du weitere Eingaben geändert. Rückgängig setzt auch diese auf den vorherigen Stand zurück. Trotzdem rückgängig machen?')) return;
      model = undo; undo = null; undoAfter = null; populate(); persist(); glint();
    }
    toastBox.hidden = true;
    afterToast(event, 0);
  });
  $('closeToast').addEventListener('click', event => { toastBox.hidden = true; afterToast(event); });
  $('saveGrades').addEventListener('change', () => { persistent = $('saveGrades').checked; persist(); });
  for (const [id, key] of FIELDS) {
    $(id).addEventListener('input', () => {
      const s = active();
      s[key] = $(id).value;
      const known = Number.isFinite(M.decimal(s.scenario));
      if (key === 'gradeStep' && known) {
        s.scenario = Math.max(1, Math.min(6, M.round(M.decimal(s.scenario), Number(s.gradeStep)))).toFixed(2);
        $('scenarioGrade').value = s.scenario;
      }
      slider.step = s.gradeStep;
      if (known) slider.value = s.scenario;
      syncSlider(); compute(); persist();
    });
  }
  chips.forEach(chip => chip.addEventListener('click', () => {
    $('nextWeight').value = chip.dataset.nextWeight; $('nextWeight').dispatchEvent(new Event('input'));
  }));
  slider.addEventListener('input', () => {
    active().scenario = Number(slider.value).toFixed(2); $('scenarioGrade').value = active().scenario; syncSlider(); updatePlan(); persist();
  });
  $('exportGrades').addEventListener('click', () => {
    try { validateImport(model); } catch { toast('Vor dem Export bitte alle ungültigen Eingaben korrigieren.'); return; }
    const url = URL.createObjectURL(new Blob([JSON.stringify(model, null, 2)], { type: 'application/json' }));
    const a = make('a'); a.href = url; a.download = 'misterpfister-noten.json'; document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  $('importGrades').addEventListener('click', () => $('importFile').click());
  $('importFile').addEventListener('change', async () => {
    const file = $('importFile').files[0]; $('importFile').value = ''; if (!file) return;
    if (file.size > 512 * 1024) { toast('Die Sicherung darf höchstens 512 KB gross sein.'); return; }
    try {
      const imported = validateImport(JSON.parse(await file.text()));
      const n = imported.subjects.length;
      if (!confirm(`${n} ${n === 1 ? 'Fach' : 'Fächer'} importieren und die aktuellen Fächer ersetzen?`)) return;
      checkpoint(); model = imported; populate(); persist(); toast('Sicherung importiert.', true); glint();
    } catch (error) { toast(error instanceof SyntaxError ? 'Die Datei enthält kein gültiges JSON.' : error.message); }
  });
  const POINTS = ['pointsEarned', 'pointsMax', 'pointsMinGrade', 'pointsMaxGrade'];
  const [meterA, meterB] = document.querySelectorAll('.points-meter');
  function computePoints() {
    const [earned, max, low, high] = POINTS.map(id => M.decimal($(id).value));
    const grade = M.points(earned, max, low, high), valid = Number.isFinite(grade), span = num(M.round(high - low, .01));
    // Each field is judged on its own; the message names what is wrong.
    const badMax = !inRange(max, 1e-9, 1e6), badLow = !inRange(low, 1, 6), badHigh = !inRange(high, 1, 6), badOrder = !badLow && !badHigh && low >= high;
    const bad = valid ? [] : [!inRange(earned, 0, badMax ? Infinity : max), badMax, badLow || badOrder, badHigh || badOrder];
    if (!valid && !bad.includes(true)) bad.fill(true);
    const precise = POINTS.some((id, i) => bad[i] && /[.,]\d{3,}/.test($(id).value));
    result('pointsResult', valid ? M.round(grade).toFixed(2) : null);
    $('pointsResult').previousElementSibling.textContent = valid ? 'Rechnerische Note' : 'Punkte und Notengrenzen prüfen';
    text('pointsError', valid ? '' : [bad[0] && `Erreichte Punkte: 0 bis ${badMax ? 'Maximum' : num(max)}.`, bad[1] && `Maximale Punkte: mehr als 0, höchstens ${num(1e6)}.`,
      (bad[2] || bad[3]) && 'Notenskala: 1–6, Mindestnote kleiner als Höchstnote.', precise && 'Höchstens 2 Dezimalstellen.'].filter(Boolean).join(' '));
    POINTS.forEach((id, i) => flag($(id), !!bad[i]));
    text('pointsFormula', valid ? `${num(low)} + (${num(earned)} ÷ ${num(max)}) × ${span} = ${M.round(grade).toFixed(2)}` : '–');
    // Inverse: minimum points for a wished grade, independent of the points earned.
    const target = M.decimal($('pointsTarget').value), needed = M.pointsFor(target, max, low, high), found = Number.isFinite(needed);
    flag($('pointsTarget'), Number.isFinite(M.points(0, max, low, high)) && !found);
    text('pointsNeededLabel', found ? `Nötig für eine ${target.toFixed(2)}` : 'Wunschnote prüfen');
    result('pointsNeeded', found ? `${num(M.round(needed, .01))} von ${num(max)}` : null, '–');
    text('pointsNeededFormula', found ? `(${num(target)} − ${num(low)}) ÷ ${span} × ${num(max)} = ${num(M.round(needed, .01))}` : '–');
    setVar(meterA, '--p', valid ? earned / max : 0);
    setVar(meterB, '--p', found ? needed / max : 0);
  }
  [...POINTS, 'pointsTarget'].forEach(id => $(id).addEventListener('input', computePoints));
  // Invalid fields shake once on leave, never while typing.
  const SHAKE = '.grade-grade, .grade-weight, #targetAverage, #scenarioGrade, #nextWeight, .points-panel input';
  document.addEventListener('focusout', ({ target: field }) => {
    if (reduced.matches || !field.matches?.(SHAKE) || field.getAttribute('aria-invalid') !== 'true') return;
    field.classList.remove('is-shake'); void field.offsetWidth; field.classList.add('is-shake');
  });
  document.addEventListener('animationend', event => event.target.classList?.remove('is-shake'));
  populate(); computePoints();
  persist();
  // The head script's layout reservation has done its job; the live DOM decides from here.
  delete document.documentElement.dataset.gradeFilled; document.documentElement.style.removeProperty('--grade-rows');
  // Intro: sweep from 1 to the restored value.
  if (reduced.matches) wrap.removeAttribute('data-intro');
  else twoFrames(() => wrap.removeAttribute('data-intro'));
  // Compact bar once the result panel is behind the header.
  const resultPanel = q('.result-panel'), inputPanel = q('.input-panel'), header = q('.site-header');
  if ('IntersectionObserver' in window) new IntersectionObserver(([entry]) => {
    $('compactResult').hidden = entry.isIntersecting || entry.boundingClientRect.top > 0;
  }, { rootMargin: '-76px 0px 0px' }).observe(resultPanel);
  // Sticky result while it fits; the input-panel class is a legacy hook.
  const fitPanel = () => {
    inputPanel.classList.toggle('fits-viewport', inputPanel.offsetHeight + 32 <= innerHeight);
    resultPanel.classList.toggle('fits-viewport', wide.matches && resultPanel.offsetHeight + header.offsetHeight + 32 <= innerHeight);
  };
  if ('ResizeObserver' in window) { const ro = new ResizeObserver(fitPanel); ro.observe(inputPanel); ro.observe(resultPanel); }
  addEventListener('resize', fitPanel); fitPanel();
})();
