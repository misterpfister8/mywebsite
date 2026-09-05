/* Clock-only planning. No calendar, alarm, network requests, or sleep-stage claims. */
(() => {
  'use strict';
  if (!document.querySelector('[data-sleep-app]')) return;
  const M = globalThis.WorkshopMath, $ = id => document.getElementById(id);
  const KEY = 'misterpfister-sleep-v2', PREF = 'misterpfister-sleep-saving';
  const defaults = () => ({ mode: 'wake', time: '07:00', hours: 8, minutes: 0, latency: 15 });
  let state = defaults(), persistent = true, lastValidState = defaults(), undoPresets = null, undoPresetsAfter = null;
  let presets = [
    { name: 'Früh raus', mode: 'wake', time: '06:30', hours: 8, minutes: 0, latency: 15 },
    { name: 'Später Start', mode: 'wake', time: '09:00', hours: 8, minutes: 0, latency: 15 },
  ];
  let validPlan = null;
  // Decorative half-hour ticks. The clock remains usable without this detail.
  for (let i = 0; i < 48; i++) {
    const a = i / 48 * Math.PI * 2, inner = i % 2 === 0 ? 144 : 149;
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    for (const [key, value] of Object.entries({ x1: 180 + Math.sin(a) * inner, y1: 180 - Math.cos(a) * inner, x2: 180 + Math.sin(a) * 154, y2: 180 - Math.cos(a) * 154 })) line.setAttribute(key, value.toFixed(2));
    $('clockTicks').append(line);
  }
  function validState(value) {
    if (!value || typeof value.time !== 'string') throw new Error('Ungültige gespeicherte Uhrzeit');
    M.sleepPlan(value.mode, value.time, value.hours, value.minutes, value.latency);
    return { mode: value.mode, time: value.time, hours: value.hours, minutes: value.minutes, latency: value.latency };
  }
  function validateBackup(data) {
    if (!data || data.version !== 1 || !Array.isArray(data.presets) || data.presets.length > 10) throw new Error('Ungültige Sicherung');
    return {
      state: validState(data.state),
      presets: data.presets.map(preset => {
        if (!preset || typeof preset.name !== 'string' || !preset.name.trim() || preset.name.length > 30) throw new Error('Ungültiges Preset');
        return { name: preset.name, ...validState(preset) };
      }),
    };
  }
  const storage = globalThis.WorkshopStorage(KEY, PREF, validateBackup);
  const restored = storage.load();
  persistent = restored.enabled;
  if (restored.data) { state = restored.data.state; presets = restored.data.presets; }
  lastValidState = { ...state };
  $('saveSleep').checked = persistent;
  function persist() {
    const result = storage.save(persistent, { version: 1, state: lastValidState, presets });
    $('sleepSaveStatus').textContent = result.text + (persistent && !result.error && !validPlan ? ' Letzte gültige Zeiten beibehalten.' : '');
    $('sleepSaveStatus').dataset.error = String(result.error);
  }
  function populate() {
    document.querySelector(`input[name="sleepMode"][value="${state.mode}"]`).checked = true;
    $('anchorTime').value = state.time; $('sleepHours').value = String(state.hours);
    $('sleepMinutes').value = String(state.minutes); $('sleepLatency').value = String(state.latency);
    $('durationSlider').value = String(state.hours * 60 + state.minutes);
  }
  function readInteger(id) { return $(id).value.trim() === '' ? NaN : Number($(id).value); }
  function read() {
    return { mode: document.querySelector('input[name="sleepMode"]:checked').value, time: $('anchorTime').value, hours: readInteger('sleepHours'), minutes: readInteger('sleepMinutes'), latency: readInteger('sleepLatency') };
  }
  const angles = new Map();
  function rotate(id, minutes) {
    const element = $(id), target = minutes / 4;
    const previous = angles.get(id);
    const angle = previous === undefined ? target : previous + ((target - previous + 180) % 360 + 360) % 360 - 180;
    angles.set(id, angle);
    element.style.transform = `rotate(${angle}deg)`;
  }
  function render() {
    state = read();
    $('anchorTimeLabel').textContent = state.mode === 'wake' ? 'Ich möchte aufstehen um' : 'Ich gehe ins Bett um';
    $('sleepResultLabel').textContent = state.mode === 'wake' ? 'INS BETT' : 'AUFSTEHEN';
    const ids = ['anchorTime', 'sleepHours', 'sleepMinutes', 'sleepLatency'];
    ids.forEach(id => $(id).setAttribute('aria-invalid', 'false'));
    try {
      validPlan = M.sleepPlan(state.mode, state.time, state.hours, state.minutes, state.latency);
    } catch (error) {
      validPlan = null;
      const errorFields = error.message === 'time' ? ['anchorTime'] : error.message === 'latency' ? ['sleepLatency'] : ['sleepHours', 'sleepMinutes'];
      errorFields.forEach(id => $(id).setAttribute('aria-invalid', 'true'));
      $('sleepError').textContent = error.message === 'time' ? 'Bitte eine gültige Uhrzeit wählen.' : error.message === 'latency' ? 'Einschlafdauer: 0–180 ganze Minuten.' : 'Schlafdauer: 1–16 Stunden. Minuten: 0–59, jeweils ganze Zahlen.';
      document.querySelector('.sleep-visual').dataset.invalid = 'true';
      $('sleepResultTime').textContent = '—:—'; $('sleepDayLabel').textContent = 'Eingaben prüfen';
      $('durationLabel').textContent = '—'; $('legendDuration').textContent = 'Schlafdauer'; $('legendLatency').textContent = 'Einschlafdauer';
      ['bedDay', 'onsetDay', 'wakeDay'].forEach(id => $(id).textContent = '—');
      ['bedTimeDisplay', 'onsetTimeDisplay', 'wakeTimeDisplay'].forEach(id => $(id).textContent = '—:—');
      $('sleepSummary').textContent = 'Kein gültiges Ergebnis. Bitte Eingaben prüfen.';
      $('sleepClock').setAttribute('aria-label', '24-Stunden-Uhr. Noch kein gültiger Zeitplan.');
      return;
    }
    const p = validPlan;
    lastValidState = { ...state };
    $('sleepError').textContent = ''; document.querySelector('.sleep-visual').dataset.invalid = 'false';
    $('sleepResultTime').textContent = M.clock(p.result); $('sleepDayLabel').textContent = p.day;
    $('durationLabel').textContent = M.duration(p.length); $('durationSlider').value = String(p.length);
    $('legendDuration').textContent = `${M.duration(p.length)} Schlaf`; $('legendLatency').textContent = `${p.latency} min Einschlafen`;
    const day = minutes => minutes < 0 ? 'Vorabend' : minutes >= 1440 ? 'Folgetag' : 'Derselbe Tag';
    $('bedDay').textContent = day(p.bed); $('onsetDay').textContent = day(p.onset); $('wakeDay').textContent = day(p.wake);
    $('bedTimeDisplay').textContent = M.clock(p.bed); $('onsetTimeDisplay').textContent = M.clock(p.onset); $('wakeTimeDisplay').textContent = M.clock(p.wake);
    $('sleepSummary').textContent = `${p.day} ${state.mode === 'wake' ? 'ins Bett' : 'aufstehen'} · ${M.duration(p.total)} eingeplant.`;
    $('sleepArc').setAttribute('stroke-dasharray', `${p.length} ${1440 - p.length}`);
    $('latencyArc').setAttribute('stroke-dasharray', `${p.latency} ${1440 - p.latency}`);
    rotate('sleepArcRotation', p.onset); rotate('latencyArcRotation', p.bed);
    $('sleepClock').setAttribute('aria-label', `24-Stunden-Uhr: ${M.clock(p.bed)} ins Bett, ${M.clock(p.onset)} einschlafen, ${M.clock(p.wake)} aufstehen. ${M.duration(p.length)} Schlaf und ${p.latency} Minuten zum Einschlafen.`);
  }
  function renderPresets() {
    $('presetList').replaceChildren(...presets.map((preset, index) => {
      const chip = document.createElement('div'); chip.className = 'preset-chip';
      const use = document.createElement('button'); use.type = 'button';
      use.append(document.createTextNode(preset.name));
      const time = document.createElement('span'); time.textContent = preset.time; use.append(time);
      use.setAttribute('aria-label', `${preset.name}: ${preset.mode === 'wake' ? 'aufstehen' : 'ins Bett'} um ${preset.time}`);
      use.addEventListener('click', () => { state = validState(preset); populate(); render(); persist(); });
      const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'preset-delete'; remove.innerHTML = '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="m6 6 12 12M6 18 18 6"/></svg>';
      remove.setAttribute('aria-label', `Preset ${preset.name} löschen`);
      remove.addEventListener('click', () => {
        undoPresets = presets.map(p => ({ ...p })); presets.splice(index, 1);
        undoPresetsAfter = JSON.stringify(presets);
        renderPresets(); persist(); $('presetHint').textContent = 'Preset gelöscht.';
        $('undoPreset').hidden = false; $('undoPreset').focus();
      });
      chip.append(use, remove); return chip;
    }));
  }
  document.querySelectorAll('input[name="sleepMode"]').forEach(input => input.addEventListener('change', () => { render(); persist(); }));
  ['anchorTime', 'sleepHours', 'sleepMinutes', 'sleepLatency'].forEach(id => $(id).addEventListener('input', () => {
    if (id === 'anchorTime' && /^\d{4}$/.test($(id).value)) $(id).value = $(id).value.slice(0, 2) + ':' + $(id).value.slice(2);
    render(); persist();
  }));
  $('durationSlider').addEventListener('input', () => {
    const minutes = Number($('durationSlider').value); $('sleepHours').value = String(Math.floor(minutes / 60)); $('sleepMinutes').value = String(minutes % 60); render(); persist();
  });
  $('sleepForm').addEventListener('submit', event => { event.preventDefault(); render(); persist(); });
  $('sleepNow').addEventListener('click', () => {
    const now = new Date(); document.querySelector('input[name="sleepMode"][value="bed"]').checked = true;
    $('anchorTime').value = M.clock(now.getHours() * 60 + now.getMinutes()); render(); persist();
  });
  $('showPresetForm').addEventListener('click', () => {
    $('presetForm').hidden = !$('presetForm').hidden;
    if (!$('presetForm').hidden) $('presetName').focus();
  });
  $('presetForm').addEventListener('submit', event => {
    event.preventDefault(); const name = $('presetName').value.trim();
    if (!name) { $('presetName').focus(); return; }
    if (!validPlan) { $('presetHint').textContent = 'Bitte zuerst gültige Zeiten einstellen.'; return; }
    const existing = presets.findIndex(preset => preset.name.toLocaleLowerCase('de-CH') === name.toLocaleLowerCase('de-CH'));
    const preset = { name: name.slice(0, 30), ...validState(state) };
    if (existing >= 0) { undoPresets = presets.map(p => ({ ...p })); presets[existing] = preset; undoPresetsAfter = JSON.stringify(presets); $('undoPreset').hidden = false; }
    else if (presets.length < 10) presets.push(preset);
    else { $('presetHint').textContent = 'Höchstens zehn Presets. Bitte zuerst eines löschen.'; return; }
    $('presetForm').hidden = true; $('presetName').value = ''; renderPresets(); persist();
    $('presetHint').textContent = existing >= 0 ? 'Gleichnamiges Preset ersetzt. Rückgängig ist möglich.' : 'Preset gemerkt. Speicherstatus siehe unten.';
    $('showPresetForm').focus();
  });
  $('undoPreset').addEventListener('click', () => {
    if (undoPresets && undoPresetsAfter !== JSON.stringify(presets) && !confirm('Rückgängig setzt auch inzwischen hinzugefügte Presets zurück. Trotzdem fortfahren?')) return;
    if (undoPresets) { presets = undoPresets; undoPresets = null; renderPresets(); persist(); }
    $('undoPreset').hidden = true; $('presetHint').textContent = 'Preset-Änderung rückgängig gemacht.';
    $('showPresetForm').focus();
  });
  $('saveSleep').addEventListener('change', () => { persistent = $('saveSleep').checked; persist(); });
  populate(); render(); renderPresets();
  persist();
})();
