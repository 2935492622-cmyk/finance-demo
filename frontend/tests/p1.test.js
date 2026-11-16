import test from 'node:test'
import assert from 'node:assert/strict'
import { createLedger } from '../src/composables/ledger.js'
import { filterParams, transactionPayload, validateFilters } from '../src/utils/filters.js'
import { expenseChartOption } from '../src/utils/chart.js'
import { ApiError, client } from '../src/api/client.js'
import { transactionsApi } from '../src/api/transactions.js'

const expense = { id: 99, amount: '125.50', type: 'expense', category: '餐饮', note: '午餐', transaction_date: '2026-11-16', created_at: '2026-11-16T00:00:00.000000Z', updated_at: '2026-11-16T00:00:00.000000Z' }
const summary = { total_income: '0.00', total_expense: '125.50', balance: '-125.50', transaction_count: 1, expense_by_category: [{ category: '餐饮', amount: '125.50' }] }
const records = { items: [expense], total: 1 }
const reads = { list: async () => records, summary: async () => summary }

test('filters omit empty and unknown parameters, keep only the shared contract keys', () => {
  assert.deepEqual(filterParams({ type: '', category: '餐饮', start_date: '2026-11-01', end_date: '', page: 1 }), { category: '餐饮', start_date: '2026-11-01' })
  assert.deepEqual(validateFilters({ type: '', category: '  餐饮  ', start_date: '', end_date: '' }).value, { category: '餐饮' })
  assert.ok(validateFilters({ start_date: '2026-12-01', end_date: '2026-11-01' }).errors.start_date)
  assert.ok(validateFilters({ start_date: '2026-02-30' }).errors.start_date)
  assert.ok(validateFilters({ category: 'a'.repeat(51) }).errors.category)
})

test('edit/cancel and delete/cancel have no network side effects and do not mutate the snapshot', async () => {
  let writes = 0
  const ledger = createLedger({ ...reads, update: async () => writes++, remove: async () => writes++ })
  await ledger.refresh()
  assert.equal(ledger.startEdit(expense), true)
  ledger.state.editing.note = 'local draft'
  assert.equal(expense.note, '午餐')
  assert.equal(ledger.cancelEdit(), true)
  assert.equal(ledger.state.editing, null)
  ledger.requestDelete(expense)
  assert.equal(ledger.cancelDelete(), true)
  assert.equal(ledger.state.deleteTarget, null)
  assert.equal(writes, 0)
  assert.equal(ledger.state.snapshot.records.items[0].note, '午餐')
})

test('editing performs a full PUT of exactly five writable fields and clears edit after confirmation', async () => {
  let received
  const ledger = createLedger({ ...reads, update: async (id, payload) => { received = { id, payload }; return { ...expense, ...payload } } })
  ledger.startEdit(expense)
  const next = { ...expense, amount: '150.00', category: '购物' }
  assert.equal(await ledger.save(next), true)
  assert.equal(received.id, 99)
  assert.deepEqual(Object.keys(received.payload), ['amount', 'type', 'category', 'note', 'transaction_date'])
  assert.equal(received.payload.amount, '150.00')
  assert.equal(ledger.state.editing, null)
})

test('list and summary receive the same immutable filters and commit them with the snapshot', async () => {
  const requested = []
  const ledger = createLedger({
    list: async ({ filters }) => { requested.push(filters); return records },
    summary: async ({ filters }) => { requested.push(filters); return summary },
  })
  const filters = { type: 'expense', category: '餐饮', start_date: '2026-11-01' }
  await ledger.refresh(filters)
  filters.category = 'changed outside'
  assert.deepEqual(requested[0], requested[1])
  assert.equal(ledger.state.snapshot.filters.category, '餐饮')
  assert.equal(ledger.state.snapshot.filters.type, 'expense')
})

test('a save hidden by filtering is identified from the refreshed server list', async () => {
  const ledger = createLedger({
    list: async () => ({ items: [], total: 0 }), summary: async () => summary,
    create: async () => expense,
  })
  await ledger.refresh({ type: 'income' })
  assert.equal(await ledger.save(expense), true)
  assert.equal(ledger.state.notice.tone, 'success')
  assert.match(ledger.state.notice.message, /不符合当前筛选/)
})

test('server inclusion takes precedence over JavaScript category equality after a save', async () => {
  const ledger = createLedger({ ...reads, create: async () => ({ ...expense, category: 'caf\u00e9' }) })
  await ledger.refresh({ category: 'cafe\u0301' })
  assert.equal(await ledger.save(expense), true)
  assert.doesNotMatch(ledger.state.notice.message, /不符合/)
})

test('confirmed deletion is followed by an atomic refresh and can clear the same edit', async () => {
  let removed
  const ledger = createLedger({ ...reads, remove: async (id) => { removed = id } })
  ledger.startEdit(expense)
  ledger.requestDelete(expense)
  assert.equal(await ledger.confirmDelete(), true)
  assert.equal(removed, 99)
  assert.equal(ledger.state.editing, null)
  assert.equal(ledger.state.deleteTarget, null)
  assert.match(ledger.state.notice.message, /已删除/)
  assert(ledger.state.snapshot)
})

test('uncertain PUT and DELETE lock every subsequent mutation until successful refresh', async () => {
  for (const action of ['update', 'remove']) {
    let calls = 0
    const ledger = createLedger({ ...reads, [action]: async () => { calls++; throw new ApiError('操作结果未确认', { uncertain: true }) } })
    if (action === 'update') ledger.startEdit(expense)
    else ledger.requestDelete(expense)
    const run = () => action === 'update' ? ledger.save(expense) : ledger.confirmDelete()
    assert.equal(await run(), false)
    assert.equal(ledger.state.uncertainWrite, true)
    assert.equal(await run(), false)
    assert.equal(calls, 1)
    assert.equal(ledger.startEdit(expense), false)
    assert.equal(await ledger.refresh(), true)
    assert.equal(ledger.state.uncertainWrite, false)
  }
})

test('readonly transaction fields can never be sent back in API write payloads', () => {
  assert.deepEqual(transactionPayload(expense), { amount: '125.50', type: 'expense', category: '餐饮', note: '午餐', transaction_date: '2026-11-16' })
})

test('API adapter uses exact PUT/DELETE paths and accepts empty 204 without JSON parsing', async () => {
  const oldAdapter = client.defaults.adapter
  const captured = []
  client.defaults.adapter = async (config) => {
    captured.push(config)
    return { config, headers: {}, status: config.method === 'delete' ? 204 : 200, statusText: 'OK', data: config.method === 'delete' ? '' : expense }
  }
  try {
    await transactionsApi.update(99, expense)
    assert.equal(await transactionsApi.remove(99), undefined)
    assert.equal(captured[0].method, 'put')
    assert.equal(captured[0].url, '/transactions/99')
    assert.deepEqual(JSON.parse(captured[0].data), transactionPayload(expense))
    assert.equal(captured[1].method, 'delete')
    assert.equal(captured[1].url, '/transactions/99')
  } finally { client.defaults.adapter = oldAdapter }
})

test('chart uses approximate values only for geometry and rich text preserves exact tooltip money', () => {
  const dangerousName = '<img src=x onerror=alert(1)>'
  const options = expenseChartOption([{ category: dangerousName, amount: '9007199254740993.01' }])
  const data = options.series[0].data[0]
  assert.equal(options.tooltip.renderMode, 'richText')
  assert.equal(data.exactAmount, '9007199254740993.01')
  assert.equal(data.name, dangerousName)
  assert.match(options.tooltip.formatter({ data }), /9,007,199,254,740,993\.01/)
})
