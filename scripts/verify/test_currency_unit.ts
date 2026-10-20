import { formatINR, formatINRCompact, formatCountIN, formatDateIN, formatDateTimeIN } from '../../frontend/src/utils/currency.ts';

const r1 = formatINR(1234567.5);
const r2 = formatINRCompact(15000000);
const r3 = formatINRCompact(250000);
const r4 = formatINRCompact(85000);
const r5 = formatCountIN(1234567);
const r6 = formatDateIN('2026-03-15T00:00:00Z');

console.log('formatINR(1234567.5) =', r1);
console.log('formatINRCompact(15000000) =', r2);
console.log('formatINRCompact(250000) =', r3);
console.log('formatINRCompact(85000) =', r4);
console.log('formatCountIN(1234567) =', r5);
console.log('formatDateIN(2026-03-15) =', r6);

assert(r1 === '₹12,34,567.50', `Expected ₹12,34,567.50, got ${r1}`);
assert(r2 === '₹1.5Cr', `Expected ₹1.5Cr, got ${r2}`);
assert(r3 === '₹2.5L', `Expected ₹2.5L, got ${r3}`);
console.log('ALL UNIT CHECKS PASSED!');

function assert(cond: boolean, msg: string) {
  if (!cond) throw new Error(msg);
}
