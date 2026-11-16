import test from 'node:test'
import assert from 'node:assert/strict'
import { normalizeAmount, formatMoney } from '../src/utils/money.js'
import { shanghaiDate, isValidDate } from '../src/utils/date.js'
import { validateTransaction } from '../src/utils/validation.js'

test('decimal input is padded as text without floating-point rounding', () => {
  assert.equal(normalizeAmount('12'), '12.00')
  assert.equal(normalizeAmount('12.3'), '12.30')
  assert.equal(normalizeAmount('0.01'), '0.01')
  assert.equal(normalizeAmount('99999999.99'), '99999999.99')
})

test('invalid, nonpositive, noncanonical and overprecision input is rejected', () => {
  for (const value of ['0', '0.00', '-1', '12.345', '100000000', '1e2', 'NaN', '', ' 1', '1 ', '01', '+1', '.5', '1.', null, 12, true]) {
    assert.throws(() => normalizeAmount(value), Error, String(value))
  }
})

test('server summary values keep precision beyond JavaScript safe integers', () => {
  assert.equal(formatMoney('9007199254740993.01'), '9,007,199,254,740,993.01')
  assert.equal(formatMoney('-125.50'), '-125.50')
  assert.equal(formatMoney('0.00'), '0.00')
  assert.equal(formatMoney(null), '—')
})

test('default ledger date uses Asia/Shanghai even across UTC day boundaries', () => {
  assert.equal(shanghaiDate(new Date('2026-11-15T17:00:00Z')), '2026-11-16')
  assert.equal(shanghaiDate(new Date('2026-11-15T01:00:00Z')), '2026-11-15')
})

test('calendar dates enforce actual days and the MySQL date range', () => {
  for (const value of ['1000-01-01', '9999-12-31', '2024-02-29']) assert.equal(isValidDate(value), true, value)
  for (const value of ['0999-12-31', '2026-02-29', '2026-02-30', '2026-1-01', '', '2026-11-15T00:00:00Z']) assert.equal(isValidDate(value), false, value)
})

test('form validates normalized Unicode lengths and only emits contract fields', () => {
  const form = { amount: '12.3', type: 'expense', category: ` ${'🍵'.repeat(50)} `, note: ' 午餐 ', transaction_date: '2026-11-16' }
  const valid = validateTransaction(form)
  assert.deepEqual(valid.errors, {})
  assert.equal(valid.value.amount, '12.30')
  assert.equal(valid.value.note, '午餐')
  assert.equal([...valid.value.category].length, 50)
  assert.deepEqual(Object.keys(valid.value), ['amount', 'type', 'category', 'note', 'transaction_date'])
  const invalid = validateTransaction({ ...form, category: '🍵'.repeat(51), note: 'a'.repeat(501) })
  assert.ok(invalid.errors.category)
  assert.ok(invalid.errors.note)
  assert.equal(invalid.value, null)
})
