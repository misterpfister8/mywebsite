/* Local-only grade workspace. User strings are inserted with textContent/value. */
(() => {
  'use strict';
  if (!document.querySelector('[data-grade-app]')) return;
  const M = globalThis.WorkshopMath;
  const $ = id => document.getElementById(id);
  const KEY = 'misterpfister-grades-v2', PREF = 'misterpfister-grades-saving';
  const MAX_SUBJECTS = 30, MAX_ROWS = 100;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const clone = object => JSON.parse(JSON.stringify(object));
  const emptyRow = () => ({ name: '', grade: '', weight: '1' });
  const newSubject = (name = 'Allgemein') => ({ name, entries: [emptyRow(), emptyRow()], rounding: '0.01', gradeStep: '0.01', target: '4.00', nextWeight: '1', scenario: '5.00', scenarioWeight: '1', basis: 'exact' });
  let model = { type: 'misterpfister-grades', version: 1, active: 0, subjects: [newSubject()] };
  let current = null, undo = null, undoAfter = null, persistent = true;
  function validateImport(data, drafts = false) {
    if (!data || data.type !== 'misterpfister-grades' || data.version !== 1 || !Array.isArray(data.subjects) || !data.subjects.length || data.subjects.length > MAX_SUBJECTS) throw new Error('Keine gültige Noten-Sicherungsdatei.');
    const subjects = data.subjects.map(s => {
      if (!s || typeof s.name !== 'string' || !s.name.trim() || s.name.length > 60 || !Array.isArray(s.entries) || !s.entries.length || s.entries.length > MAX_ROWS) throw new Error('Ungültiges Fach oder zu viele Noten.');
      const result = newSubject(s.name.trim());
      result.entries = s.entries.map(row => {
        if (!row || typeof row.name !== 'string' || row.name.length > 120 || typeof row.grade !== 'string' || typeof row.weight !== 'string' || row.grade.length > 20 || row.weight.length > 20) throw new Error('Ungültige Notenzeile.');
        if (!drafts && row.grade.trim() && (!Number.isFinite(M.decimal(row.grade)) || M.decimal(row.grade) < 1 || M.decimal(row.grade) > 6)) throw new Error('Noten müssen zwischen 1 und 6 liegen.');
        const w = M.decimal(row.weight);
        if (!drafts && (!Number.isFinite(w) || w < .01 || w > 100)) throw new Error('Ungültiges Gewicht in der Sicherung.');
        return { name: row.name, grade: row.grade, weight: row.weight };
      });
      if (!['0.01', '0.1', '0.5', '1'].includes(s.rounding) || !['0.01', '0.1', '0.25', '0.5', '1'].includes(s.gradeStep) || !['exact', 'display'].includes(s.basis)) throw new Error('Ungültige Rundungsregel.');
      for (const [key, max] of [['target', 6], ['nextWeight', 100], ['scenario', 6], ['scenarioWeight', 100]]) {
        const input = key === 'scenarioWeight' ? (s[key] ?? s.nextWeight) : s[key];
        const value = M.decimal(input);
        if (typeof input !== 'string' || input.length > 20 || (!drafts && (!Number.isFinite(value) || value < (key.endsWith('Weight') ? .01 : 1) || value > max))) throw new Error('Ungültige Planungseinstellung.');
        result[key] = input;
      }
      result.rounding = s.rounding; result.gradeStep = s.gradeStep; result.basis = s.basis;
      return result;
    });
    return { type: 'misterpfister-grades', version: 1, active: Number.isInteger(data.active) && data.active >= 0 && data.active < subjects.length ? data.active : 0, subjects };
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
  function text(id, value) {
    const el = $(id);
    el.textContent = value;
    // Results stay fully opaque and stable while typing; only the scale moves.
  }
  function toast(message, canUndo = false) {
    $('toastMessage').textContent = message;
    $('undoAction').hidden = !canUndo;
    if (canUndo) undoAfter = JSON.stringify(model);
    $('gradeToast').hidden = false;
  }
  function checkpoint() { undo = clone(model); }
  function renderSubjects() {
    $('subjectSelect').replaceChildren(...model.subjects.map((subject, index) => {
      const option = document.createElement('option'); option.value = String(index); option.textContent = subject.name; return option;
    }));
    $('subjectSelect').value = String(model.active);
    $('renameSubject').value = active().name;
  }
  function renderRows(focusIndex = null) {
    const entries = $('gradeEntries'); entries.replaceChildren();
    active().entries.forEach((entry, index) => {
      const row = document.createElement('div'); row.className = 'grade-row';
      for (const [key, label, placeholder] of [['name', `Prüfung ${index + 1} (optional)`, 'Prüfung'], ['grade', `Note ${index + 1}`, '–'], ['weight', `Gewicht ${index + 1}`, '1']]) {
        const input = document.createElement('input'); input.type = 'text'; input.className = `grade-${key}`;
        input.value = entry[key]; input.placeholder = placeholder; input.autocomplete = 'off';
        input.maxLength = key === 'name' ? 120 : 20;
        input.setAttribute('aria-label', label);
        if (key !== 'name') input.inputMode = 'decimal';
        input.addEventListener('input', () => { entry[key] = input.value; compute(); persist(); });
        row.append(input);
      }
      const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'icon-button'; remove.setAttribute('aria-label', `Note ${index + 1} entfernen`);
      remove.innerHTML = '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" aria-hidden="true"><path d="m6 6 12 12M6 18 18 6"/></svg>';
      remove.addEventListener('click', () => {
        checkpoint(); active().entries.splice(index, 1);
        if (!active().entries.length) active().entries.push(emptyRow());
        renderRows(Math.min(index, active().entries.length - 1)); compute(); persist(); toast('Note entfernt.', true);
      });
      row.append(remove); entries.append(row);
    });
    if (focusIndex !== null) entries.children[focusIndex]?.querySelector('.grade-grade').focus();
    $('addEntry').disabled = active().entries.length >= MAX_ROWS;
  }
  function populate() {
    renderSubjects(); renderRows();
    const s = active();
    for (const [id, key] of [['rounding', 'rounding'], ['gradeStep', 'gradeStep'], ['targetAverage', 'target'], ['nextWeight', 'nextWeight'], ['scenarioGrade', 'scenario'], ['scenarioWeight', 'scenarioWeight'], ['targetBasis', 'basis']]) $(id).value = s[key];
    $('scenarioSlider').step = s.gradeStep; $('scenarioSlider').value = s.scenario;
    compute();
  }
  function compute() {
    const s = active(); let invalid = false;
    [...$('gradeEntries').children].forEach((row, index) => {
      const e = s.entries[index], grade = M.decimal(e.grade), weight = M.decimal(e.weight), filled = e.grade.trim() !== '';
      const badGrade = filled && (!Number.isFinite(grade) || grade < 1 || grade > 6);
      const badWeight = filled && (!Number.isFinite(weight) || weight < .01 || weight > 100);
      row.querySelector('.grade-grade').setAttribute('aria-invalid', String(badGrade));
      row.querySelector('.grade-weight').setAttribute('aria-invalid', String(badWeight));
      if (badGrade || badWeight) invalid = true;
    });
    $('gradeError').textContent = invalid ? 'Noten: 1–6. Gewicht: 0.01–100. Jeweils höchstens zwei Dezimalstellen.' : '';
    try { current = invalid ? null : M.summary(s.entries); } catch { current = null; }
    $('scalePointer').hidden = !current;
    $('scenarioPointer').hidden = true;
    if (!current) {
      text('average', '—'); text('averageDetail', invalid ? 'Bitte Eingaben prüfen.' : 'Trage deine erste Note ein.');
      text('averageExact', ''); text('gradeCount', invalid ? 'Eingabe prüfen' : 'Noch keine Noten');
      $('scaleFill').style.width = '0%';
      $('gradeScale').setAttribute('aria-label', 'Notenskala von 1 bis 6. Noch kein gültiges Ergebnis.');
    } else {
      text('average', M.round(current.average, Number(s.rounding)).toFixed(2));
      text('averageDetail', `Gewicht ${new Intl.NumberFormat('de-CH', { maximumFractionDigits: 2 }).format(current.weight)} · Rundung ${s.rounding}`);
      text('averageExact', `Rechenwert ≈ ${current.average.toFixed(4)}`);
      text('gradeCount', `${current.count} ${current.count === 1 ? 'Note' : 'Noten'}`);
      const pos = `${(current.average - 1) / 5 * 100}%`;
      $('scaleFill').style.width = pos; $('scalePointer').style.left = pos;
      $('gradeScale').setAttribute('aria-label', `Notenskala 1 bis 6. Ungerundeter Schnitt ${current.average.toFixed(4)}.`);
    }
    updatePlan();
    $('compactAverage').textContent = current ? `Schnitt ${M.round(current.average, Number(s.rounding)).toFixed(2)} · ${current.count} Noten` : 'Noch kein gültiger Schnitt';
  }
  function updatePlan() {
    const s = active(), next = M.decimal(s.nextWeight), simulationWeight = M.decimal(s.scenarioWeight), simulated = M.decimal(s.scenario), target = M.decimal(s.target);
    const validWeight = Number.isFinite(next) && next >= .01 && next <= 100;
    const validSimulationWeight = Number.isFinite(simulationWeight) && simulationWeight >= .01 && simulationWeight <= 100;
    const step = Number(s.gradeStep);
    const validSim = Number.isFinite(simulated) && simulated >= 1 && simulated <= 6 && Math.abs((simulated - 1) / step - Math.round((simulated - 1) / step)) < 1e-7;
    const validTarget = Number.isFinite(target) && target >= 1 && target <= 6;
    $('scenarioWeight').setAttribute('aria-invalid', String(!validSimulationWeight));
    $('nextWeight').setAttribute('aria-invalid', String(!validWeight));
    $('scenarioGrade').setAttribute('aria-invalid', String(!validSim));
    $('targetAverage').setAttribute('aria-invalid', String(!validTarget));
    $('scenarioPointer').hidden = true;
    text('scenarioWeightLabel', validSimulationWeight ? `mit Gewicht ${s.scenarioWeight}` : 'Gewicht prüfen');
    if (current && validSimulationWeight && validSim) {
      const projected = (current.sum + simulated * simulationWeight) / (current.weight + simulationWeight);
      text('scenarioResult', M.round(projected, Number(s.rounding)).toFixed(2));
      text('scenarioHint', `Rechenwert ≈ ${projected.toFixed(4)}. Simulation, keine gespeicherte Prüfung.`);
      $('gradeScale').setAttribute('aria-label', `Skala 1 bis 6. Aktuell ${current.average.toFixed(4)}, simuliert ${projected.toFixed(4)}. 4 ist eine Orientierung, keine Bestehensgarantie.`);
      $('scenarioPointer').hidden = false; $('scenarioPointer').style.left = `${(projected - 1) / 5 * 100}%`;
    } else {
      text('scenarioResult', '—'); text('scenarioHint', current ? `Nächste Note in ${s.gradeStep}er-Schritten und gültiges Gewicht eingeben.` : 'Mindestens eine gültige aktuelle Note eingeben.');
    }
    $('targetResult').removeAttribute('data-tone');
    if (!current) {
      text('targetResult', 'Zuerst eine gültige aktuelle Note eingeben.'); text('targetDetail', 'Der Planer berücksichtigt deine gewählten Notenschritte.'); return;
    }
    if (!validWeight || !validTarget) {
      text('targetResult', 'Zielschnitt oder Gewicht prüfen.'); text('targetDetail', 'Ziel: 1–6. Gewicht: 0.01–100.'); $('targetResult').dataset.tone = 'danger'; return;
    }
    const plan = M.neededGrade(current, target, next, Number(s.gradeStep), Number(s.rounding), s.basis);
    if (!plan.possible) { text('targetResult', 'Selbst eine 6.00 reicht als nächste Note nicht.'); $('targetResult').dataset.tone = 'danger'; }
    else if (plan.secured) text('targetResult', `Mit jeder nächsten Note ab 1.00 erreicht.`);
    else text('targetResult', `Du brauchst mindestens eine ${plan.required.toFixed(2)}.`);
    text('targetDetail', `${plan.secured ? 'Ziel auch mit der Mindestnote erreicht' : `Rechnerisch ${plan.raw.toFixed(3)}`} · ${s.gradeStep}er-Schritte · Ziel für ${s.basis === 'display' ? 'die gerundete Anzeige' : 'den ungerundeten Schnitt'}.`);
  }
  $('addEntry').addEventListener('click', () => {
    if (active().entries.length >= MAX_ROWS) return;
    active().entries.push(emptyRow()); renderRows(active().entries.length - 1); compute(); persist();
    const row = $('gradeEntries').lastElementChild;
    if (!reduced.matches && row.animate) row.animate([{ opacity: 0, transform: 'translateY(-8px)' }, { opacity: 1, transform: 'translateY(0)' }], { duration: 220, easing: 'ease-out' });
  });
  $('gradeForm').addEventListener('submit', event => { event.preventDefault(); compute(); });
  $('subjectSelect').addEventListener('change', () => { model.active = Number($('subjectSelect').value); populate(); persist(); });
  $('addSubject').addEventListener('click', () => {
    if (model.subjects.length >= MAX_SUBJECTS) { toast(`Höchstens ${MAX_SUBJECTS} Fächer möglich.`); return; }
    $('subjectForm').hidden = false; $('subjectName').focus();
  });
  $('cancelSubject').addEventListener('click', () => { $('subjectForm').hidden = true; $('addSubject').focus(); });
  $('subjectForm').addEventListener('submit', event => {
    event.preventDefault(); const name = $('subjectName').value.trim();
    if (!name || model.subjects.length >= MAX_SUBJECTS) { $('subjectName').focus(); return; }
    model.subjects.push(newSubject(name.slice(0, 60))); model.active = model.subjects.length - 1;
    $('subjectName').value = ''; $('subjectForm').hidden = true; populate(); persist(); $('gradeEntries').querySelector('.grade-grade').focus();
  });
  $('renameSubject').addEventListener('change', () => {
    const name = $('renameSubject').value.trim(); if (name) active().name = name.slice(0, 60); renderSubjects(); persist();
  });
  $('deleteSubject').addEventListener('click', () => {
    checkpoint(); model.subjects.splice(model.active, 1);
    if (!model.subjects.length) model.subjects.push(newSubject());
    model.active = Math.min(model.active, model.subjects.length - 1); populate(); persist(); toast('Fach gelöscht.', true);
  });
  $('loadExample').addEventListener('click', () => {
    checkpoint(); active().entries = [{ name: 'Prüfung 1', grade: '4.5', weight: '1' }, { name: 'Prüfung 2', grade: '5.5', weight: '1' }, { name: 'Prüfung 3', grade: '5', weight: '1' }, { name: 'Prüfung 4', grade: '6', weight: '1' }];
    renderRows(); compute(); persist(); toast('Beispielnoten eingesetzt.', true);
  });
  $('undoAction').addEventListener('click', () => {
    if (undo) {
      if (undoAfter !== JSON.stringify(model) && !confirm('Inzwischen hast du weitere Eingaben geändert. Rückgängig setzt auch diese auf den vorherigen Stand zurück. Trotzdem rückgängig machen?')) return;
      model = undo; undo = null; undoAfter = null; populate(); persist();
    }
    $('gradeToast').hidden = true;
    $('gradeEntries').querySelector('.grade-grade')?.focus();
  });
  $('closeToast').addEventListener('click', () => { $('gradeToast').hidden = true; });
  $('saveGrades').addEventListener('change', () => { persistent = $('saveGrades').checked; persist(); });
  for (const [id, key] of [['rounding', 'rounding'], ['gradeStep', 'gradeStep'], ['targetAverage', 'target'], ['nextWeight', 'nextWeight'], ['scenarioGrade', 'scenario'], ['scenarioWeight', 'scenarioWeight'], ['targetBasis', 'basis']]) {
    $(id).addEventListener('input', () => {
      active()[key] = $(id).value;
      if (key === 'gradeStep' && Number.isFinite(M.decimal(active().scenario))) {
        active().scenario = Math.max(1, Math.min(6, M.round(M.decimal(active().scenario), Number(active().gradeStep)))).toFixed(2);
        $('scenarioGrade').value = active().scenario;
      }
      $('scenarioSlider').step = active().gradeStep;
      if (Number.isFinite(M.decimal(active().scenario))) $('scenarioSlider').value = active().scenario;
      compute(); persist();
    });
  }
  $('scenarioSlider').addEventListener('input', () => {
    active().scenario = Number($('scenarioSlider').value).toFixed(2); $('scenarioGrade').value = active().scenario; updatePlan(); persist();
  });
  $('exportGrades').addEventListener('click', () => {
    try { validateImport(model); } catch { toast('Vor dem Export bitte alle ungültigen Eingaben korrigieren.'); return; }
    const url = URL.createObjectURL(new Blob([JSON.stringify(model, null, 2)], { type: 'application/json' }));
    const a = document.createElement('a'); a.href = url; a.download = 'misterpfister-noten.json'; document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  $('importGrades').addEventListener('click', () => $('importFile').click());
  $('importFile').addEventListener('change', async () => {
    const file = $('importFile').files[0]; $('importFile').value = ''; if (!file) return;
    if (file.size > 512 * 1024) { toast('Die Sicherung darf höchstens 512 KB gross sein.'); return; }
    try {
      const imported = validateImport(JSON.parse(await file.text()));
      if (!confirm(`${imported.subjects.length} Fächer importieren und die aktuellen Fächer ersetzen?`)) return;
      checkpoint(); model = imported; populate(); persist(); toast('Sicherung importiert.', true);
    } catch (error) { toast(error instanceof SyntaxError ? 'Die Datei enthält kein gültiges JSON.' : error.message); }
  });
  function computePoints() {
    const ids = ['pointsEarned', 'pointsMax', 'pointsMinGrade', 'pointsMaxGrade'];
    const result = M.points(...ids.map(id => M.decimal($(id).value)));
    text('pointsResult', Number.isFinite(result) ? M.round(result).toFixed(2) : '—');
    $('pointsResult').previousElementSibling.textContent = Number.isFinite(result) ? 'Rechnerische Note (2 Dezimalstellen)' : 'Punkte und Notengrenzen prüfen';
    $('pointsError').textContent = Number.isFinite(result) ? '' : 'Punkte: 0 bis Maximum. Maximum: grösser 0, höchstens 1 000 000. Notenskala: 1–6, Mindestnote kleiner als Höchstnote.';
    ids.forEach(id => $(id).setAttribute('aria-invalid', String(!Number.isFinite(result))));
  }
  ['pointsEarned', 'pointsMax', 'pointsMinGrade', 'pointsMaxGrade'].forEach(id => $(id).addEventListener('input', computePoints));
  populate(); computePoints();
  persist();
  // A compact summary occupies its own space and hides while an input has focus.
  if ('IntersectionObserver' in window) new IntersectionObserver(([entry]) => {
    $('compactResult').hidden = entry.isIntersecting || entry.boundingClientRect.top > 0;
  }).observe(document.querySelector('.result-panel'));
})();
