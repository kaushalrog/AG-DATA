import { test } from 'node:test';
import assert from 'node:assert/strict';
import { interpolate, fmtRupees, fmtPct, fmtDate, fmtNumber, freshnessKey, coveragePer100, loc } from '../js/format.js';

test('interpolate replaces tokens and leaves unknown ones visible', () => {
  assert.equal(interpolate('{price} / quintal', { price: '₹2,000' }), '₹2,000 / quintal');
  assert.equal(interpolate('{a} {b}', { a: 1 }), '1 {b}');
  assert.equal(interpolate('{n} days', { n: 0 }), '0 days');
});

test('locale tag is <lang>-IN', () => { assert.equal(loc('ta'), 'ta-IN'); assert.equal(loc(), 'en-IN'); });

test('rupees use Indian grouping and no decimals', () => {
  assert.equal(fmtRupees('en', 2000), '₹2,000');
  assert.equal(fmtRupees('en', 150000), '₹1,50,000');
  assert.equal(fmtRupees('en', 1999.6), '₹2,000');
  assert.equal(fmtRupees('en', null), '–');
  for (const l of ['ta', 'te', 'ml', 'hi', 'kn']) {
    const s = fmtRupees(l, 150000);
    assert.match(s, /₹/, `${l}: ${s}`);
    assert.match(s.replace(/[^\d,]/g, ''), /1,50,000/, `${l}: ${s}`);
  }
});

test('percent is signed and localised', () => {
  assert.equal(fmtPct('en', 4.2), '+4.2%');
  assert.equal(fmtPct('en', -4.2), '-4.2%');
  assert.equal(fmtPct('en', 0), '0%');
  assert.equal(fmtPct('en', 9.8, false), '9.8%');
  assert.equal(fmtPct('en', undefined), '–');
  for (const l of ['ta', 'te', 'ml', 'hi', 'kn']) assert.match(fmtPct(l, 12.5), /12\.5/);
});

test('dates are calendar dates (no timezone shift) and localised', () => {
  assert.equal(fmtDate('en', '2026-04-17'), '17 Apr 2026');
  for (const l of ['ta', 'te', 'ml', 'hi', 'kn']) {
    const s = fmtDate(l, '2026-04-17');
    assert.match(s, /17/); assert.match(s, /2026/);
    assert.notEqual(s, '17 Apr 2026', `${l} should use localised month: ${s}`);
  }
  assert.equal(fmtDate('en', ''), '–');
});

test('numbers', () => {
  assert.equal(fmtNumber('en', 1234567), '12,34,567');
  assert.equal(fmtNumber('en', 0.934, 2), '0.93');
});

test('freshness wording is relative to the dataset when the data itself is old', () => {
  assert.deepEqual(freshnessKey(4, 1), { key: 'fresh.age_days', n: 4 });
  assert.deepEqual(freshnessKey(1, 0), { key: 'fresh.age_one', n: 1 });
  assert.deepEqual(freshnessKey(4, 184), { key: 'fresh.age_rel_days', n: 4 });
  assert.deepEqual(freshnessKey(1, 184), { key: 'fresh.age_rel_one', n: 1 });
  assert.deepEqual(freshnessKey(0, 184), { key: 'fresh.age_zero', n: 0 });
});

test('coverage expressed as times out of 100', () => {
  assert.equal(coveragePer100(0.79), 79);
  assert.equal(coveragePer100(null), null);
});
