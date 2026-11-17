import test from 'node:test'
import assert from 'node:assert/strict'
import { balanceTrendOption, buildBalanceTrend } from '../src/utils/trend.js'

test('trend groups dates in ascending order and accumulates income minus expenses', () => {
  const items = [
    { transaction_date: '2026-11-17', type: 'expense', amount: '25.50' },
    { transaction_date: '2026-11-15', type: 'expense', amount: '10.00' },
    { transaction_date: '2026-11-15', type: 'income', amount: '100.00' },
    { transaction_date: '2026-11-16', type: 'expense', amount: '100.00' },
  ]
  assert.deepEqual(buildBalanceTrend(items), [
    { date: '2026-11-15', exactAmount: '90.00' },
    { date: '2026-11-16', exactAmount: '-10.00' },
    { date: '2026-11-17', exactAmount: '-35.50' },
  ])
  assert.equal(items[0].transaction_date, '2026-11-17')
})

test('trend retains exact cents beyond Number precision, including negatives and zero', () => {
  const points = buildBalanceTrend([
    { transaction_date: '2026-11-15', type: 'expense', amount: '9007199254740993.01' },
    { transaction_date: '2026-11-16', type: 'income', amount: '9007199254740993.00' },
    { transaction_date: '2026-11-17', type: 'income', amount: '0.01' },
  ])
  assert.deepEqual(points.map((point) => point.exactAmount), ['-9007199254740993.01', '-0.01', '0.00'])
  const option = balanceTrendOption(points)
  assert.match(option.tooltip.formatter({ data: option.series[0].data[0] }), /-9,007,199,254,740,993\.01/)
  assert.equal(option.tooltip.renderMode, 'richText')
})

test('empty trend and one-date data do not invent dates or balances', () => {
  assert.deepEqual(buildBalanceTrend([]), [])
  const points = buildBalanceTrend([{ transaction_date: '1000-01-01', type: 'income', amount: '1.00' }])
  const option = balanceTrendOption(points)
  assert.deepEqual(option.xAxis.data, ['1000-01-01'])
  assert.equal(option.series[0].data.length, 1)
  assert.equal(option.series[0].showSymbol, true)
})
