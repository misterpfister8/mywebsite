/* Pure, independently testable calculator functions. All times are clock-only. */
(() => {
  'use strict';
  const EPS = 1e-9;
  function decimal(value, precision = 2) {
    const text = String(value ?? '').trim();
    if (!text || !new RegExp(`^(?:\\d+(?:[.,]\\d{0,${precision}})?|[.,]\\d{1,${precision}})$`).test(text)) return NaN;
    return Number(text.replace(',', '.'));
  }
  function round(value, step = 0.01) {
    if (!Number.isFinite(value) || !Number.isFinite(step) || step <= 0) return NaN;
    return Number((Math.round((value + EPS) / step) * step).toFixed(8));
  }
  function summary(entries) {
    let sum = 0, weight = 0, count = 0;
    for (const entry of entries) {
      if (String(entry.grade).trim() === '') continue;
      const grade = decimal(entry.grade), w = decimal(entry.weight);
      if (!Number.isFinite(grade) || grade < 1 || grade > 6) throw new RangeError('grade');
      if (!Number.isFinite(w) || w < 0.01 || w > 100) throw new RangeError('weight');
      sum += grade * w; weight += w; count++;
    }
    return count ? { sum, weight, count, average: sum / weight } : null;
  }
  function neededGrade(current, target, nextWeight, gradeStep, displayStep, basis = 'exact') {
    if (!current || !Number.isFinite(target) || target < 1 || target > 6 || !Number.isFinite(nextWeight) || nextWeight < 0.01 || nextWeight > 100 || ![0.01, 0.1, 0.25, 0.5, 1].includes(gradeStep) || ![0.01, 0.1, 0.5, 1].includes(displayStep) || !['exact', 'display'].includes(basis)) throw new RangeError('planner');
    // For display-based targets, first find the next attainable displayed value.
    const threshold = basis === 'display' ? (Math.ceil((target - EPS) / displayStep) - 0.5) * displayStep : target;
    const raw = (threshold * (current.weight + nextWeight) - current.sum) / nextWeight;
    const stepped = Number((1 + Math.ceil((raw - 1 - EPS) / gradeStep) * gradeStep).toFixed(8));
    return { raw, required: Math.max(1, stepped), secured: raw <= 1 + EPS, possible: stepped <= 6 + EPS };
  }
  function clock(minutes) {
    const value = ((Math.round(minutes) % 1440) + 1440) % 1440;
    return `${String(Math.floor(value / 60)).padStart(2, '0')}:${String(value % 60).padStart(2, '0')}`;
  }
  function duration(minutes) {
    const h = Math.floor(minutes / 60), m = minutes % 60;
    return [h ? `${h} h` : '', m ? `${m} min` : ''].filter(Boolean).join(' ') || '0 min';
  }
  function sleepPlan(mode, time, hours, minutes, latency) {
    if (!['wake', 'bed'].includes(mode) || !/^\d{2}:\d{2}$/.test(time)) throw new RangeError('time');
    const [h, m] = time.split(':').map(Number);
    if (h > 23 || m > 59) throw new RangeError('time');
    if (!Number.isInteger(hours) || !Number.isInteger(minutes) || hours < 0 || minutes < 0 || minutes > 59) throw new RangeError('duration');
    const length = hours * 60 + minutes;
    if (length < 60 || length > 960) throw new RangeError('duration');
    if (!Number.isInteger(latency) || latency < 0 || latency > 180) throw new RangeError('latency');
    const anchor = h * 60 + m;
    const bed = mode === 'wake' ? anchor - length - latency : anchor;
    const onset = bed + latency;
    const wake = onset + length;
    return { bed, onset, wake, length, latency, total: length + latency, result: mode === 'wake' ? bed : wake, day: mode === 'wake' ? (bed < 0 ? 'Am Vorabend' : 'Am selben Tag') : (wake >= 1440 ? 'Am Folgetag' : 'Am selben Tag') };
  }
  function points(earned, maxPoints, low = 1, high = 6) {
    if (![earned, maxPoints, low, high].every(Number.isFinite) || earned < 0 || maxPoints <= 0 || maxPoints > 1e6 || earned > maxPoints || low < 1 || high > 6 || high <= low) return NaN;
    return low + (earned / maxPoints) * (high - low);
  }
  const api = Object.freeze({ decimal, round, summary, neededGrade, clock, duration, sleepPlan, points });
  globalThis.WorkshopMath = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
