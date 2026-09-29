/* Clock-only sleep planner (no alarm, network or sleep stages). The inputs stay the source of truth; the dial writes them. */
(() => {
'use strict';
if (!document.querySelector('[data-sleep-app]')) return;
const M = globalThis.WorkshopMath, $ = id => document.getElementById(id), doc = document;
const defaults = () => ({ mode: 'wake', time: '07:00', hours: 8, minutes: 0, latency: 10 });
const mod = m => ((m % 1440) + 1440) % 1440;
const text = (id, value) => { $(id).textContent = value; };
const attr = (el, values) => { for (const k in values) el.setAttribute(k, values[k]); };
const make = (tag, className, content = '') => Object.assign(doc.createElement(tag), { className, textContent: content });
const on = (el, type, fn) => el.addEventListener(type, fn);
const frame = fn => requestAnimationFrame(fn);
const update = () => { render(); persist(); };
// "8 h", "7 h 30": the compact form of the quick chips.
const short = minutes => `${Math.floor(minutes / 60)} h${minutes % 60 ? ' ' + String(minutes % 60).padStart(2, '0') : ''}`;
const asleep = minutes => minutes ? `${M.duration(minutes)} Einschlafen` : 'Sofort eingeschlafen';
// Each input on its own (the plan reports only the first problem).
const fails = (hours, minutes, latency) => { try { M.sleepPlan('wake', '12:00', hours, minutes, latency); return false; } catch { return true; } };
const wide = matchMedia('(min-width: 901px)');
let state = defaults(), persistent = true, lastValidState = defaults(), undoPresets = null, undoPresetsAfter = null, validPlan = null, drag = null;
let ringPx = 0, beadPx = 22, summaryTimer = 0, rendered = false;
let presets = [
  { name: 'Früh raus', mode: 'wake', time: '06:30', hours: 8, minutes: 0, latency: 10 },
  { name: 'Später Start', mode: 'wake', time: '09:00', hours: 8, minutes: 0, latency: 10 },
];
const visual = doc.querySelector('.sleep-visual'), wrap = visual.querySelector('.sleep-clock-wrap');
const bar = visual.querySelector('.night-bar'), midnight = bar.querySelector('.midnight');
const anchor = $('dialAnchor'), end = $('dialEnd'), handles = [anchor, end], compact = $('sleepCompact');
function validState(value) {
  if (!value || typeof value.time !== 'string') throw new Error('Ungültige Uhrzeit');
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
const storage = globalThis.WorkshopStorage('misterpfister-sleep-v2', 'misterpfister-sleep-saving', validateBackup);
const restored = storage.load();
persistent = restored.enabled;
if (restored.data) { state = restored.data.state; presets = restored.data.presets; }
lastValidState = { ...state };
$('saveSleep').checked = persistent;
function persist() {
  const result = storage.save(persistent, { version: 1, state: lastValidState, presets });
  text('sleepSaveStatus', result.text + (persistent && !result.error && !validPlan ? ' Letzte gültige Zeiten beibehalten.' : ''));
  $('sleepSaveStatus').dataset.error = String(result.error);
}
function populate() {
  doc.querySelector(`input[name="sleepMode"][value="${state.mode}"]`).checked = true;
  $('anchorTime').value = state.time; $('sleepHours').value = String(state.hours);
  $('sleepMinutes').value = String(state.minutes); $('sleepLatency').value = String(state.latency);
  $('durationSlider').value = String(state.hours * 60 + state.minutes);
}
const readInteger = id => $(id).value.trim() === '' ? NaN : Number($(id).value);
const read = () => ({ mode: doc.querySelector('input[name="sleepMode"]:checked').value, time: M.parseTime($('anchorTime').value), hours: readInteger('sleepHours'), minutes: readInteger('sleepMinutes'), latency: readInteger('sleepLatency') });
// While typing, a value that can still become a time waits ('1' → 12, '233' → 23:30, '7:' → 7:30) instead of flashing an error.
function unfinished(value) {
  const v = value.trim();
  if (/^[0-2]$|^([01]\d|2[0-3])[0-5]$/.test(v)) return true;
  if (M.parseTime(v)) return false;
  return v === '' || /^([01]?\d|2[0-3])[:.,][0-5]?$/.test(v) || /^\d\d$/.test(v) && [...'012345'].some(d => M.parseTime(v + d));
}
function setLength(minutes) {
  $('sleepHours').value = String(Math.floor(minutes / 60)); $('sleepMinutes').value = String(minutes % 60);
  $('durationSlider').value = String(minutes);
}
// Shortest path: nothing spins the long way round.
const angles = new Map();
function turn(key, minutes) {
  const target = minutes / 4, previous = angles.get(key);
  const angle = previous === undefined ? target : previous + ((target - previous + 180) % 360 + 360) % 360 - 180;
  angles.set(key, angle);
  return angle;
}
// Anchor = typed time; end = the other end of the night.
const plan = () => { const wake = state.mode === 'wake', p = validPlan; return { wake, anchor: mod(wake ? p.wake : p.bed), end: mod(wake ? p.bed : p.wake) }; };
// Short nights: the beads would cover each other and the arc, so they step off the ring (CSS).
const syncClose = () => { const p = validPlan; wrap.toggleAttribute('data-close', !!p && Math.min(p.total, 1440 - p.total) / 1440 * 2 * Math.PI * ringPx < beadPx * 1.9); };
// Screen readers get one calm summary: never per drag frame, keys and typing settle first.
function announce(message) {
  clearTimeout(summaryTimer);
  if (drag) return;
  if (!rendered) text('sleepSummary', message);
  else summaryTimer = setTimeout(() => text('sleepSummary', message), 400);
}

function syncDial(p) {
  const wake = state.mode === 'wake';
  anchor.setAttribute('aria-label', `${wake ? 'Aufstehzeit' : 'Bettzeit'} am Zifferblatt`);
  end.setAttribute('aria-label', `Schlafdauer, Ende bei der ${wake ? 'Bettzeit' : 'Aufstehzeit'}`);
  anchor.firstElementChild.dataset.icon = wake ? 'sun' : 'moon';
  end.firstElementChild.dataset.icon = wake ? 'moon' : 'sun';
  handles.forEach(h => attr(h, p ? { 'aria-disabled': 'false' } : { 'aria-disabled': 'true', 'aria-valuetext': 'Eingaben prüfen' }));
  if (compact) {
    compact.dataset.mode = state.mode;
    compact.querySelector('span').textContent = `${wake ? 'Ins Bett' : 'Aufstehen'} ${p ? M.clock(p.result) : '—:—'} · ${p ? p.day : 'Eingaben prüfen'}`;
  }
  if (!p) return;
  const at = plan();
  attr(anchor, { 'aria-valuenow': at.anchor, 'aria-valuetext': `${M.clock(at.anchor)} ${wake ? 'Aufstehen' : 'Ins Bett'}` });
  attr(end, { 'aria-valuenow': p.length, 'aria-valuetext': `${M.duration(p.length)} Schlaf, ${wake ? 'ins Bett' : 'aufstehen'} um ${M.clock(at.end)}` });
  // The readout already shows the end time, so its tip shows only the length.
  anchor.lastElementChild.textContent = M.clock(at.anchor);
  end.lastElementChild.textContent = short(p.length);
  anchor.style.setProperty('--a', `${turn('a', at.anchor)}deg`);
  end.style.setProperty('--a', `${turn('e', at.end)}deg`);
  syncClose();
  // Night bar; midnight tick only when crossing 00:00.
  const bed = mod(p.bed), crosses = bed > 0 && bed + p.total > 1440, mid = (1440 - bed) / p.total;
  bar.style.cssText = `--lat:${p.latency};--len:${p.length};--mid:${mid.toFixed(4)}`;
  bar.toggleAttribute('data-nolat', !p.latency);
  bar.dataset.edge = mid < .12 ? 'start' : mid > .88 ? 'end' : '';
  midnight.hidden = !crosses;
}
function syncLength(length) {
  $('durationSlider').value = String(length);
  $('durationSlider').style.setProperty('--p', ((length - 60) / 900).toFixed(4));
}

function render() {
  state = read();
  const wake = state.mode === 'wake';
  text('anchorTimeLabel', wake ? 'Ich möchte aufstehen um' : 'Ich gehe ins Bett um');
  text('sleepResultLabel', wake ? 'INS BETT' : 'AUFSTEHEN');
  ['anchorTime', 'sleepHours', 'sleepMinutes', 'sleepLatency'].forEach(id => $(id).setAttribute('aria-invalid', 'false'));
  try {
    validPlan = M.sleepPlan(state.mode, state.time, state.hours, state.minutes, state.latency);
  } catch (error) {
    validPlan = null;
    // Mark every bad input, but keep what is still valid (a bad time leaves the duration alone).
    const kind = error.message, length = state.hours * 60 + state.minutes, lengthBad = fails(state.hours, state.minutes, 0), latencyBad = fails(8, 0, state.latency);
    [[!state.time, ['anchorTime']], [lengthBad, ['sleepHours', 'sleepMinutes']], [latencyBad, ['sleepLatency']]].forEach(([bad, ids]) => bad && ids.forEach(id => $(id).setAttribute('aria-invalid', 'true')));
    text('sleepError', kind === 'time' ? 'Ungültige Uhrzeit, z. B. 07:00.' : kind === 'latency' ? 'Einschlafen: 0–180 Minuten.' : 'Schlaf: 1–16 h, Minuten 0–59.');
    visual.dataset.invalid = 'true';
    text('sleepResultTime', '—:—'); text('sleepDayLabel', 'Eingaben prüfen');
    text('durationLabel', lengthBad ? '—' : M.duration(length)); text('legendDuration', lengthBad ? 'Schlafdauer' : `${M.duration(length)} Schlaf`);
    text('legendLatency', latencyBad ? 'Einschlafdauer' : asleep(state.latency)); visual.toggleAttribute('data-nolat', !latencyBad && !state.latency);
    if (!lengthBad) syncLength(length);
    ['bed', 'onset', 'wake'].forEach(id => { text(id + 'Day', '—'); text(id + 'TimeDisplay', '—:—'); });
    syncDurationPresets(lengthBad ? null : length);
    announce('Kein gültiges Ergebnis. Bitte Eingaben prüfen.');
    $('sleepClock').setAttribute('aria-label', '24-Stunden-Uhr. Noch kein gültiger Zeitplan.');
    syncDial(null); syncPresets();
    return;
  }
  const p = validPlan;
  lastValidState = { ...state };
  text('sleepError', ''); visual.dataset.invalid = 'false';
  visual.toggleAttribute('data-nolat', !p.latency);
  // Touch drags: the handle is under the finger, so the readout shows the value being dragged.
  const at = plan(), reading = drag?.readout ? drag.handle : null;
  if (reading === anchor) {
    text('sleepResultLabel', wake ? 'AUFSTEHEN' : 'INS BETT'); text('sleepResultTime', M.clock(at.anchor));
    text('sleepDayLabel', `${wake ? 'Ins Bett' : 'Aufstehen'} ${M.clock(p.result)}`);
  } else {
    text('sleepResultTime', M.clock(p.result)); text('sleepDayLabel', reading ? `${M.duration(p.length)} Schlaf` : p.day);
  }
  text('durationLabel', M.duration(p.length)); syncLength(p.length);
  text('legendDuration', `${M.duration(p.length)} Schlaf`); text('legendLatency', asleep(p.latency));
  // Only times that cross midnight get a day label.
  ['bed', 'onset', 'wake'].forEach(id => { text(id + 'Day', p[id] < -420 ? 'Vortag' : p[id] < 0 ? 'Vorabend' : p[id] >= 1440 ? 'Folgetag' : ''); text(id + 'TimeDisplay', M.clock(p[id])); });
  announce(`${wake ? 'Ins Bett' : 'Aufstehen'} um ${M.clock(p.result)} (${p.day}) · ${M.duration(p.length)} Schlaf${p.latency ? `, ${M.duration(p.latency)} Einschlafen` : ''}.`);
  syncDurationPresets(p.length);
  $('sleepArc').setAttribute('stroke-dasharray', `${p.length} ${1440 - p.length}`);
  $('latencyArc').setAttribute('stroke-dasharray', `${p.latency} ${1440 - p.latency}`);
  $('sleepArcRotation').style.transform = `rotate(${turn('sleep', p.onset)}deg)`;
  $('latencyArcRotation').style.transform = `rotate(${turn('latency', p.bed)}deg)`;
  $('sleepClock').setAttribute('aria-label', `24-Stunden-Uhr: ${M.clock(p.bed)} ins Bett, ${M.clock(p.onset)} einschlafen, ${M.clock(p.wake)} aufstehen. ${M.duration(p.length)} Schlaf und ${p.latency} Minuten zum Einschlafen.`);
  syncDial(p); syncPresets();
}
function syncDurationPresets(length) {
  doc.querySelectorAll('[data-duration]').forEach(button => button.setAttribute('aria-pressed', String(Number(button.dataset.duration) === length)));
}
// The preset that matches the current plan is pressed.
function syncPresets() {
  const same = preset => !!validPlan && ['mode', 'time', 'hours', 'minutes', 'latency'].every(key => preset[key] === state[key]);
  $('presetList').querySelectorAll('.preset-chip').forEach((chip, index) => {
    const active = !!presets[index] && same(presets[index]);
    chip.toggleAttribute('data-active', active); chip.firstElementChild.setAttribute('aria-pressed', String(active));
  });
}
function normaliseTime() {
  const time = M.parseTime($('anchorTime').value);
  if (time) $('anchorTime').value = time;
}
function renderPresets() {
  $('presetList').replaceChildren(...presets.map((preset, index) => {
    const chip = make('div', 'preset-chip'), use = make('button', ''), remove = make('button', 'preset-delete');
    const length = preset.hours * 60 + preset.minutes, about = make('span', 'sr-only', `${M.duration(length)} Schlaf, ${preset.latency ? `${M.duration(preset.latency)} Einschlafen` : 'ohne Einschlafzeit'}`);
    chip.dataset.mode = preset.mode; use.type = remove.type = 'button'; about.id = `presetAbout${index}`;
    use.append(make('i', 'preset-icon'), make('span', 'preset-name', preset.name), make('span', 'preset-time', preset.time), make('span', 'preset-length', short(length)));
    use.setAttribute('aria-label', `${preset.name}: ${preset.mode === 'wake' ? 'aufstehen' : 'ins Bett'} um ${preset.time}`);
    use.setAttribute('aria-describedby', about.id);
    on(use, 'click', () => { state = validState(preset); populate(); update(); });
    remove.innerHTML = '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="m6 6 12 12M6 18 18 6"/></svg>';
    remove.setAttribute('aria-label', `Preset ${preset.name} löschen`);
    on(remove, 'click', () => {
      undoPresets = presets.map(p => ({ ...p })); presets.splice(index, 1);
      undoPresetsAfter = JSON.stringify(presets);
      renderPresets(); persist(); text('presetHint', 'Preset gelöscht.');
      $('undoConfirm').hidden = true; $('undoPreset').hidden = false; $('undoPreset').focus();
    });
    chip.append(use, remove, about); return chip;
  }));
  syncPresets();
}

// Anchor writes #anchorTime, end writes the duration. While dragging (hold), a value changes only once the pointer is clearly past it.
function moveTo(handle, minutes, step = 5, hold = false) {
  const at = plan(), p = validPlan;
  if (handle === anchor) {
    if (hold && Math.min(mod(minutes - at.anchor), mod(at.anchor - minutes)) <= step * .6) return;
    $('anchorTime').value = M.clock(mod(Math.round(minutes / step) * step));
    return;
  }
  const raw = mod(at.wake ? at.anchor - p.latency - minutes : minutes - at.anchor - p.latency);
  // A clamped drag stays on its bound until the pointer comes back to it; after a lap round the dial, only right at the bead.
  if (drag?.clamped) {
    const off = raw < 60 || raw > 960 ? Infinity : Math.abs(raw - drag.clamped);
    if (off > 120 && off < Infinity) drag.far = true;
    if (off > (drag.far ? 20 : 120)) return;
    drag.clamped = 0; drag.far = false;
  }
  if (raw < 60 || raw > 960) {
    const bound = M.dialDuration(state.mode, at.anchor, minutes, p.latency, p.length);
    if (drag) drag.clamped = bound;
    setLength(bound); nudge();
    return;
  }
  if (hold && Math.abs(raw - p.length) <= step * .6) return;
  setLength(Math.min(960, Math.max(60, Math.round(raw / step) * step)));
}
// 2px nudge when the duration hits 1 h or 16 h.
const nudge = () => matchMedia('(prefers-reduced-motion: reduce)').matches || end.firstElementChild.animate({ translate: ['0 0', '2px 0', '-2px 0', '0 0'] }, 120);
function dragStart(event) {
  if (drag || event.button) return;
  const handle = event.currentTarget;
  event.preventDefault();
  // Pointer focus: no keyboard ring (focusVisible where supported, data-pointer elsewhere).
  handle.dataset.pointer = ''; handle.focus({ preventScroll: true, focusVisible: false });
  if (!validPlan) return;
  // Fingers get coarse steps; finger and pen hide the handle, so the readout shows its value.
  drag = { id: event.pointerId, handle, touch: event.pointerType === 'touch', readout: event.pointerType !== 'mouse' || !wide.matches, rest: { x: event.clientX, y: event.clientY },
    saved: [$('anchorTime').value, $('sleepHours').value, $('sleepMinutes').value] };
  try { handle.setPointerCapture(event.pointerId); } catch { /* synthetic */ }
  wrap.classList.add('is-dragging'); handle.classList.add('is-dragging'); wrap.toggleAttribute('data-readout', drag.readout);
  render();
}
function dragFrame() {
  if (!drag) return;
  const point = drag.point;
  drag.frame = 0; drag.point = null;
  if (!point || !validPlan) return;
  // Measured per frame: a scroll during the drag must not skew the angle.
  const r = wrap.getBoundingClientRect(), dx = point.x - r.left - r.width / 2, dy = point.y - r.top - r.height / 2;
  if (Math.hypot(dx, dy) < r.width * 127 / 360 * .35) return; // the angle is meaningless near the centre
  // Fingers: 15-minute steps, 5 after a pause; Shift or Alt: 1 minute.
  moveTo(drag.handle, M.pointerAngle(dx, dy) * 4, point.fine ? 1 : drag.touch && !drag.slow ? 15 : 5, true);
  render();
}
function dragMove(event) {
  if (event.pointerId !== drag?.id) return;
  const point = { x: event.clientX, y: event.clientY, fine: event.shiftKey || event.altKey };
  if (drag.touch && Math.hypot(point.x - drag.rest.x, point.y - drag.rest.y) > 4) {
    drag.rest = point; clearTimeout(drag.timer);
    drag.timer = setTimeout(() => { if (drag) drag.slow = true; }, 400);
  }
  drag.point = point;
  drag.frame ||= frame(dragFrame); // one render per frame
}
function dragEnd(event) {
  if (event.pointerId !== drag?.id) return;
  const current = drag;
  cancelAnimationFrame(current.frame); clearTimeout(current.timer);
  if (event.type === 'pointercancel') [$('anchorTime').value, $('sleepHours').value, $('sleepMinutes').value] = current.saved;
  else dragFrame();
  drag = null;
  wrap.classList.remove('is-dragging'); current.handle.classList.remove('is-dragging'); wrap.removeAttribute('data-readout');
  render();
  if (event.type !== 'pointercancel') persist(); // one write per drag
}
function dialKey(event) {
  delete event.currentTarget.dataset.pointer;
  const key = event.key, step = event.shiftKey ? 1 : 5;
  const delta = { ArrowRight: step, ArrowUp: step, ArrowLeft: -step, ArrowDown: -step, PageUp: 60, PageDown: -60 }[key];
  if ((delta === undefined && key !== 'Home' && key !== 'End') || !validPlan || drag) return;
  event.preventDefault();
  const at = plan();
  if (event.currentTarget === end) setLength(key === 'Home' ? 60 : key === 'End' ? 960 : Math.min(960, Math.max(60, validPlan.length + delta)));
  else $('anchorTime').value = M.clock(key === 'Home' ? 0 : key === 'End' ? 1435 : mod(at.anchor + delta));
  update();
}
for (const handle of handles) {
  for (const [type, fn] of [['pointerdown', dragStart], ['pointermove', dragMove], ['pointerup', dragEnd], ['pointercancel', dragEnd], ['keydown', dialKey]]) on(handle, type, fn);
  on(handle, 'blur', () => delete handle.dataset.pointer);
}
// Ring tap: the nearest handle moves there.
on($('sleepClock'), 'click', event => {
  const r = event.currentTarget.getBoundingClientRect(), dx = event.clientX - r.left - r.width / 2, dy = event.clientY - r.top - r.height / 2;
  const ratio = Math.hypot(dx, dy) / (r.width / 2);
  if (!validPlan || ratio < .55 || ratio > 1) return;
  const minutes = M.dialMinutes(M.pointerAngle(dx, dy), 5), at = plan(), gap = to => Math.min(Math.abs(minutes - to), 1440 - Math.abs(minutes - to));
  moveTo(gap(at.anchor) <= gap(at.end) ? anchor : end, minutes);
  update();
});
// Label scale, radius fallback; resizing snaps the handles.
const cqi = CSS.supports('width: 1cqi');
let settle = 0;
const snap = () => { wrap.classList.add('is-resizing'); cancelAnimationFrame(settle); settle = frame(() => { settle = frame(() => wrap.classList.remove('is-resizing')); }); };
if ('ResizeObserver' in window) new ResizeObserver(([entry]) => {
  const width = entry.contentRect.width;
  if (!width) return;
  snap(); ringPx = width * 127 / 360; beadPx = anchor.firstElementChild.offsetWidth || beadPx; syncClose();
  wrap.style.setProperty('--k', (360 / width).toFixed(4));
  if (!cqi) wrap.style.setProperty('--ring', `${ringPx.toFixed(2)}px`);
}).observe(wrap);
// Wide screens keep the night panel under the header while it fits; otherwise the compact bar repeats the result.
const header = doc.querySelector('.site-header');
let away = false;
const syncCompact = () => { if (compact) compact.hidden = !(away && !visual.classList.contains('fits-viewport')); };
const fit = () => { visual.classList.toggle('fits-viewport', wide.matches && visual.offsetHeight + header.offsetHeight + 32 <= innerHeight); syncCompact(); };
if ('ResizeObserver' in window) new ResizeObserver(fit).observe(visual);
on(window, 'resize', fit); wide.addEventListener?.('change', fit);
if (compact && 'IntersectionObserver' in window) {
  new IntersectionObserver(([entry]) => { away = !entry.isIntersecting && entry.boundingClientRect.top < 76; syncCompact(); }, { rootMargin: '-76px 0px 0px' }).observe(wrap);
}

doc.querySelectorAll('input[name="sleepMode"]').forEach(input => on(input, 'change', () => {
  // Same night, other end fixed: the typed time becomes the previous result; the beads swap roles in place.
  if (validPlan) { $('anchorTime').value = M.clock(validPlan.result); snap(); }
  update();
}));
['anchorTime', 'sleepHours', 'sleepMinutes', 'sleepLatency'].forEach(id => on($(id), 'input', () => {
  if (id === 'anchorTime') {
    if (/^\d{4}$/.test($(id).value)) $(id).value = $(id).value.slice(0, 2) + ':' + $(id).value.slice(2);
    if (unfinished($(id).value)) return; // decided on blur or Enter
  }
  update();
}));
on($('anchorTime'), 'change', () => { normaliseTime(); update(); });
doc.querySelectorAll('[data-duration]').forEach(button => on(button, 'click', () => { setLength(Number(button.dataset.duration)); update(); }));
on($('durationSlider'), 'input', () => { setLength(Number($('durationSlider').value)); update(); });
on($('sleepForm'), 'submit', event => { event.preventDefault(); normaliseTime(); update(); });
on($('sleepNow'), 'click', () => {
  const now = new Date(); doc.querySelector('input[name="sleepMode"][value="bed"]').checked = true;
  $('anchorTime').value = M.clock(now.getHours() * 60 + now.getMinutes()); update();
});
// Preset form: a disclosure (Escape closes it); a full list still allows replacing a preset by its name.
function presetForm(open) {
  $('presetForm').hidden = !open;
  $('showPresetForm').setAttribute('aria-expanded', String(open));
  $('showPresetForm').querySelector('span').textContent = open ? 'Abbrechen' : 'Merken';
  $('presetName').removeAttribute('aria-invalid');
}
on($('showPresetForm'), 'click', () => {
  const open = $('presetForm').hidden;
  presetForm(open);
  if (!open) return;
  if (presets.length >= 10) text('presetHint', 'Zehn Presets gespeichert. Ein gleicher Name ersetzt das bestehende.');
  $('presetName').focus();
});
on($('presetForm'), 'keydown', event => {
  if (event.key !== 'Escape') return;
  event.preventDefault(); presetForm(false); $('showPresetForm').focus();
});
on($('presetName'), 'input', () => $('presetName').removeAttribute('aria-invalid'));
on($('presetForm'), 'submit', event => {
  event.preventDefault(); const name = $('presetName').value.trim();
  if (!name) { text('presetHint', 'Bitte einen Namen eingeben.'); $('presetName').setAttribute('aria-invalid', 'true'); $('presetName').focus(); return; }
  if (!validPlan) { text('presetHint', 'Bitte zuerst gültige Zeiten einstellen.'); return; }
  const existing = presets.findIndex(preset => preset.name.toLocaleLowerCase('de-CH') === name.toLocaleLowerCase('de-CH'));
  const preset = { name: name.slice(0, 30), ...validState(state) };
  if (existing >= 0) { undoPresets = presets.map(p => ({ ...p })); presets[existing] = preset; undoPresetsAfter = JSON.stringify(presets); $('undoConfirm').hidden = true; $('undoPreset').hidden = false; }
  else if (presets.length < 10) presets.push(preset);
  else { text('presetHint', 'Höchstens zehn Presets. Bitte zuerst eines löschen oder einen bestehenden Namen verwenden.'); return; }
  presetForm(false); $('presetName').value = ''; renderPresets(); persist();
  text('presetHint', existing >= 0 ? 'Gleichnamiges Preset ersetzt. Rückgängig ist möglich.' : 'Preset gemerkt. Speicherstatus siehe unten.');
  $('showPresetForm').focus();
});
// Undo after later additions asks inline instead of a native dialog.
function undoPresetChange() {
  if (undoPresets) { presets = undoPresets; undoPresets = null; renderPresets(); persist(); }
  $('undoPreset').hidden = true; $('undoConfirm').hidden = true; text('presetHint', 'Preset-Änderung rückgängig gemacht.');
  $('showPresetForm').focus();
}
on($('undoPreset'), 'click', () => {
  if (!undoPresets || undoPresetsAfter === JSON.stringify(presets)) { undoPresetChange(); return; }
  $('undoPreset').hidden = true; $('undoConfirm').hidden = false;
  text('presetHint', 'Rückgängig setzt auch die später hinzugefügten Presets zurück. Trotzdem?');
  $('undoYes').focus();
});
on($('undoYes'), 'click', undoPresetChange);
on($('undoNo'), 'click', () => { $('undoConfirm').hidden = true; $('undoPreset').hidden = false; text('presetHint', 'Presets unverändert.'); $('undoPreset').focus(); });
on($('saveSleep'), 'change', () => { persistent = $('saveSleep').checked; persist(); });
populate(); render(); renderPresets();
persist(); rendered = true; fit();
// Transitions start after the first frames.
frame(() => frame(() => wrap.setAttribute('data-ready', '')));
})();
