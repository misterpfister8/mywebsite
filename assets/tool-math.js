/* Pure, independently testable calculator functions. All times are clock-only. */
(() => {
  'use strict';
  function decimal(value, precision = 2) {
    const text = String(value ?? '').trim();
    if (!text || !new RegExp(`^(?:\\d+(?:[.,]\\d{0,${precision}})?|[.,]\\d{1,${precision}})$`).test(text)) return NaN;
    return Number(text.replace(',', '.'));
  }
  function round(value, step = 0.01) {
    if (!Number.isFinite(value) || !Number.isFinite(step) || step <= 0) return NaN;
    const scaled = value / step;
    // Correct machine representation error only, not values meaningfully below a tie.
    const tolerance = Number.EPSILON * Math.max(1, Math.abs(scaled)) * 4;
    return Number((Math.floor(scaled + 0.5 + tolerance) * step).toFixed(8));
  }
  function summary(entries) {
    let sum = 0, weight = 0, count = 0;
    for (const entry of entries) {
      if (String(entry.grade).trim() === '') continue;
      const grade = decimal(entry.grade), w = decimal(entry.weight);
      if (!Number.isFinite(grade) || grade < 1 || grade > 6) throw new RangeError('grade');
      if (!Number.isFinite(w) || w < 0.01 || w > 100) throw new RangeError('weight');
      // Hundredths keep all accepted inputs exact while accumulating weights.
      sum += Math.round(grade * 100) * Math.round(w * 100);
      weight += Math.round(w * 100); count++;
    }
    return count ? { sum: sum / 10000, weight: weight / 100, count, average: sum / (weight * 100) } : null;
  }
  function neededGrade(current, target, nextWeight, gradeStep, displayStep, basis = 'exact') {
    if (!current || !Number.isFinite(target) || target < 1 || target > 6 || !Number.isFinite(nextWeight) || nextWeight < 0.01 || nextWeight > 100 || ![0.01, 0.1, 0.25, 0.5, 1].includes(gradeStep) || ![0.01, 0.1, 0.5, 1].includes(displayStep) || !['exact', 'display'].includes(basis)) throw new RangeError('planner');
    // Search the complete finite grade grid (at most 501 grades). Integer
    // cross-products make exact and half-up boundaries independent of float drift.
    const targetCents = Math.round(target * 100), roundingCents = Math.round(displayStep * 100);
    const stepCents = Math.round(gradeStep * 100), nextCents = Math.round(nextWeight * 100);
    const weightCents = Math.round(current.weight * 100), sumUnits = Math.round(current.sum * 10000);
    const thresholdTwice = basis === 'display'
      ? 2 * Math.ceil(targetCents / roundingCents) * roundingCents - roundingCents
      : 2 * targetCents;
    const raw = (thresholdTwice / 200 * (current.weight + nextWeight) - current.sum) / nextWeight;
    let required = null;
    for (let grade = 100; grade <= 600; grade += stepCents) {
      if (2 * (sumUnits + grade * nextCents) >= thresholdTwice * (weightCents + nextCents)) {
        required = grade / 100;
        break;
      }
    }
    return { raw, required, secured: required === 1, possible: required !== null };
  }
  // Lenient 24-hour input: 07:00, 7:00, 7.00, 7,00, 0700, 700 or 7. Returns HH:MM or ''.
  function parseTime(value) {
    const text = String(value ?? '').trim();
    const match = /^(\d{1,2})(?:[:.,](\d{2}))?$/.exec(text) || /^(\d{1,2})(\d{2})$/.exec(text);
    if (!match) return '';
    const h = Number(match[1]), m = Number(match[2] ?? 0);
    return h <= 23 && m <= 59 ? `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}` : '';
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
    // Bed before 17:00 of the previous day is not the evening before (-420 = 17:00 - 24 h).
    const before = bed < -420 ? 'Am Vortag' : 'Am Vorabend';
    return { bed, onset, wake, length, latency, total: length + latency, result: mode === 'wake' ? bed : wake, day: mode === 'wake' ? (bed < 0 ? before : 'Am selben Tag') : (wake >= 1440 ? 'Am Folgetag' : 'Am selben Tag') };
  }
  function points(earned, maxPoints, low = 1, high = 6) {
    if (![earned, maxPoints, low, high].every(Number.isFinite) || earned < 0 || maxPoints <= 0 || maxPoints > 1e6 || earned > maxPoints || low < 1 || high > 6 || high <= low) return NaN;
    return low + (earned / maxPoints) * (high - low);
  }
  function pointsFor(target, maxPoints, low = 1, high = 6) {
    if (![target, maxPoints, low, high].every(Number.isFinite) || maxPoints <= 0 || maxPoints > 1e6 || low < 1 || high > 6 || high <= low || target < low || target > high) return NaN;
    return (target - low) / (high - low) * maxPoints;
  }
  // 24-hour dial: pointer offset from the centre -> degrees (0 = top, clockwise, [0, 360)).
  function pointerAngle(dx, dy) {
    const deg = Math.atan2(dx, -dy) * 180 / Math.PI;
    return (deg + 360) % 360;
  }
  // Dial angle -> clock minutes [0, 1440), snapped to `step` minutes (4 minutes per degree).
  function dialMinutes(angleDeg, step = 5) {
    const a = ((angleDeg % 360) + 360) % 360;
    const m = Math.round(a * 4 / step) * step;
    return ((m % 1440) + 1440) % 1440;
  }
  // Sleep length when the end handle sits at `handle` minutes, clamped to 60..960.
  // wake mode: handle = bed, length = wake - latency - bed; bed mode: handle = wake, length = wake - bed - latency.
  function dialDuration(mode, anchor, handle, latency, previous) {
    const raw = mode === 'wake' ? anchor - latency - handle : handle - anchor - latency;
    const len = ((raw % 1440) + 1440) % 1440;
    if (len >= 60 && len <= 960) return len;
    if (len > 960) return previous <= 510 ? 60 : 960; // wrapped past a bound: stay on the side we came from
    return previous >= 510 ? 960 : 60;
  }
  const api = Object.freeze({ decimal, round, summary, neededGrade, parseTime, clock, duration, sleepPlan, points, pointsFor, pointerAngle, dialMinutes, dialDuration });
  globalThis.WorkshopMath = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
