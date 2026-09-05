'use strict';
const assert = require('node:assert/strict');
const M = require('../assets/tool-math.js');
let checks = 0;
const eq = (a, b) => { assert.deepEqual(a, b); checks++; };
const near = (a, b) => { assert.ok(Math.abs(a - b) < 1e-7, `${a} ≠ ${b}`); checks++; };
const throws = fn => { assert.throws(fn, RangeError); checks++; };
for (const [input, expected] of [['4,5', 4.5], [' 5.25 ', 5.25], ['.5', .5], ['0.01', .01]]) eq(M.decimal(input), expected);
for (const input of ['', 'abc', '4.555', '1e1', '0x10', 'Infinity', '-1', '4,5.2']) { assert.ok(Number.isNaN(M.decimal(input))); checks++; }
eq(M.summary([{ grade: '', weight: '1' }]), null);
const current = M.summary([{ grade: '4.5', weight: '1' }, { grade: '6', weight: '2' }]);
near(current.average, 5.5); eq(current.count, 2); eq(current.weight, 3);
throws(() => M.summary([{ grade: '0', weight: '1' }]));
throws(() => M.summary([{ grade: '6.01', weight: '1' }]));
throws(() => M.summary([{ grade: '4', weight: '0' }]));
throws(() => M.summary([{ grade: '4', weight: '101' }]));
near(M.round(3.995), 4); near(M.round(5.25, .1), 5.3); near(M.round(5.25, .5), 5.5);
near(M.neededGrade(current, 5.5, 1, .01, .01, 'exact').required, 5.5);
near(M.neededGrade(current, 5.5, 1, .01, .01, 'display').required, 5.48);
near(M.neededGrade(current, 5.5, 1, .5, .01, 'display').required, 5.5);
eq(M.neededGrade(current, 3, 1, .5, .01).secured, true);
eq(M.neededGrade(current, 6, 1, .5, .01).possible, false);
// Compare the algebraic planner against brute force over every attainable grade.
for (let i = 0; i < 16; i++) {
  const c = M.summary([{ grade: (1 + ((i * 37) % 501) / 100).toFixed(2), weight: '1.25' }, { grade: (1 + ((i * 79) % 501) / 100).toFixed(2), weight: '2' }]);
  for (const target of [3.5, 4, 4.17, 5, 5.5, 6]) for (const step of [.01, .1, .25, .5, 1]) for (const rounding of [.01, .1, .5, 1]) for (const basis of ['exact', 'display']) {
    const plan = M.neededGrade(c, target, 1.5, step, rounding, basis);
    let brute = null;
    for (let j = 0; j <= Math.round(5 / step); j++) {
      const grade = 1 + j * step, mean = (c.sum + grade * 1.5) / (c.weight + 1.5);
      const tested = basis === 'exact' ? mean : Math.floor(mean / rounding + .5 + 1e-9) * rounding;
      if (tested + 1e-9 >= target) { brute = grade; break; }
    }
    eq(plan.possible, brute !== null);
    if (brute !== null) near(plan.required, brute);
  }
}
const p = M.sleepPlan('wake', '06:45', 8, 0, 15);
eq(M.clock(p.bed), '22:30'); eq(M.clock(p.onset), '22:45'); eq(p.day, 'Am Vorabend');
const q = M.sleepPlan('bed', '23:30', 8, 0, 15);
eq(M.clock(q.wake), '07:45'); eq(q.day, 'Am Folgetag');
eq(M.clock(M.sleepPlan('wake', '07:00', 7, 15, 15).bed), '23:30');
eq(M.clock(M.sleepPlan('wake', '07:00', 16, 0, 180).bed), '12:00');
for (let t = 0; t < 1440; t += 17) for (const h of [1, 7, 8, 16]) for (const latency of [0, 15, 180]) for (const mode of ['wake', 'bed']) {
  const a = M.sleepPlan(mode, M.clock(t), h, 0, latency);
  eq(a.wake - a.bed, h * 60 + latency); eq(a.onset - a.bed, latency);
  eq(mode === 'wake' ? a.wake : a.bed, t);
}
for (const args of [['wake', '', 8, 0, 15], ['wake', '24:00', 8, 0, 15], ['wake', '12:60', 8, 0, 15], ['bed', '12:00', 0, 0, 0], ['bed', '12:00', 16, 1, 15], ['bed', '12:00', 8, 60, 15], ['bed', '12:00', 8, 0, 181]]) throws(() => M.sleepPlan(...args));
eq(M.duration(495), '8 h 15 min'); eq(M.duration(0), '0 min');
near(M.points(45, 60), 4.75); near(M.points(0, 60), 1); near(M.points(60, 60), 6); near(M.points(30, 60, 2, 6), 4);
for (const args of [[61, 60], [-1, 60], [10, 0], [10, 20, 6, 6], [NaN, 60]]) { assert.ok(Number.isNaN(M.points(...args))); checks++; }
// Independent BigInt reference: round the resulting rational mean, then compare
// to the target. Include tiny/large next weights, ties and off-grid display goals.
for (const entries of [
  [{ grade: '4.5', weight: '1' }, { grade: '6', weight: '2' }],
  [{ grade: '5.49', weight: '100' }, { grade: '5.5', weight: '0.01' }],
  [{ grade: '1', weight: '0.01' }], [{ grade: '6', weight: '100' }],
  [{ grade: '3.99', weight: '2.13' }, { grade: '5.27', weight: '1.37' }],
]) {
  const c = M.summary(entries);
  let n = 0n, d = 0n;
  for (const e of entries) {
    const g = BigInt(Math.round(Number(e.grade) * 100)), w = BigInt(Math.round(Number(e.weight) * 100));
    n += g * w; d += w;
  }
  for (const weight of [.01, 1, 100]) for (const target of [1, 3.99, 4, 4.17, 5.49, 5.5, 5.51, 6])
    for (const step of [.01, .1, .25, .5, 1]) for (const rounding of [.01, .1, .5, 1]) for (const basis of ['exact', 'display']) {
      const w = BigInt(Math.round(weight * 100)), t = BigInt(Math.round(target * 100)), r = BigInt(Math.round(rounding * 100));
      let expected = null;
      for (let g = 100; g <= 600; g += Math.round(step * 100)) {
        const numerator = n + BigInt(g) * w, denominator = d + w;
        const meets = basis === 'exact' ? numerator >= t * denominator
          : ((2n * numerator + denominator * r) / (2n * denominator * r)) * r >= t;
        if (meets) { expected = g / 100; break; }
      }
      const plan = M.neededGrade(c, target, weight, step, rounding, basis);
      eq(plan.required, expected); eq(plan.possible, expected !== null); eq(plan.secured, expected === 1);
    }
}
eq(M.round(5.495 - 1e-10, .01), 5.49);
eq(M.round(5.495, .01), 5.5);
eq(M.round(4.25 - 1e-10, .5), 4);
eq(M.clock(M.sleepPlan('bed', '23:37', 7, 23, 0).wake), '07:00');
eq(M.sleepPlan('bed', '22:00', 2, 0, 0).day, 'Am Folgetag');
eq(M.sleepPlan('wake', '08:15', 8, 0, 15).day, 'Am selben Tag');
eq(M.clock(M.sleepPlan('wake', '00:00', 1, 0, 0).bed), '23:00');
for (const args of [['bed', '00:00', 0, 59, 0], ['bed', '00:00', 8.1, 0, 0], ['bed', '00:00', 8, 0, -1], ['wake', '00:00', 8, NaN, 0]]) throws(() => M.sleepPlan(...args));
console.log(`PASS: ${checks} mathematical assertions (including exhaustive grade-step comparisons).`);
