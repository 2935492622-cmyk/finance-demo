import test from 'node:test'
import assert from 'node:assert/strict'
import { createLedger } from '../src/composables/ledger.js'
import { ApiError, normalizeApiError } from '../src/api/client.js'

const summary = { total_income: '1000.00', total_expense: '125.50', balance: '874.50', transaction_count: 2, expense_by_category: [] }
const records = { items: [], total: 0 }
function deferred() {
  let resolve, reject
  const promise = new Promise((ok, fail) => { resolve = ok; reject = fail })
  return { promise, resolve, reject }
}

test('paired reads commit together; a partial failure keeps previous data marked stale', async () => {
  let fail = false
  const ledger = createLedger({
    list: async () => ({ ...records, total: fail ? 100 : 0 }),
    summary: async () => { if (fail) throw new ApiError('数据库不可用'); return summary },
  })
  assert.equal(await ledger.refresh(), true)
  const snapshot = ledger.state.snapshot
  fail = true
  assert.equal(await ledger.refresh(), false)
  assert.equal(ledger.state.snapshot, snapshot)
  assert.equal(ledger.state.snapshot.records.total, 0)
  assert.equal(ledger.state.error, '数据库不可用')
  assert.equal(ledger.state.loading, false)
})

test('an older request cannot overwrite the most recent complete pair', async () => {
  const oldList = deferred(), oldSummary = deferred()
  let listCalls = 0, summaryCalls = 0
  const ledger = createLedger({
    list: () => ++listCalls === 1 ? oldList.promise : Promise.resolve({ items: [], total: 2 }),
    summary: () => ++summaryCalls === 1 ? oldSummary.promise : Promise.resolve({ ...summary, transaction_count: 2 }),
  })
  const first = ledger.refresh()
  const latest = ledger.refresh()
  assert.equal(await latest, true)
  oldList.resolve({ items: [], total: 1 })
  oldSummary.resolve({ ...summary, transaction_count: 1 })
  assert.equal(await first, false)
  assert.equal(ledger.state.snapshot.records.total, 2)
  assert.equal(ledger.state.snapshot.summary.transaction_count, 2)
})

test('duplicate save clicks send only one POST', async () => {
  const pending = deferred()
  let posts = 0
  const ledger = createLedger({ list: async () => records, summary: async () => summary, create: () => { posts++; return pending.promise } })
  const first = ledger.save({ amount: '1.00' })
  assert.equal(await ledger.save({ amount: '1.00' }), false)
  assert.equal(posts, 1)
  pending.resolve({ id: 1 })
  assert.equal(await first, true)
  assert.equal(ledger.state.submitting, false)
  assert.equal(ledger.state.notice.tone, 'success')
})

test('successful save with failed refresh remains a confirmed save', async () => {
  const ledger = createLedger({ create: async () => ({ id: 1 }), list: async () => { throw new ApiError('读取失败') }, summary: async () => summary })
  assert.equal(await ledger.save({ amount: '1.00' }), true)
  assert.equal(ledger.state.notice.tone, 'warning')
  assert.match(ledger.state.notice.message, /已保存/)
  assert.match(ledger.state.notice.message, /不要重复提交/)
  assert.equal(ledger.state.snapshot, null)
})

test('uncertain writes block new POSTs until a successful refresh, and preserve failure state', async () => {
  let readsFail = true, posts = 0
  const ledger = createLedger({
    create: async () => { posts++; throw new ApiError('结果未确认', { uncertain: true }) },
    list: async () => { if (readsFail) throw new ApiError('读取失败'); return records },
    summary: async () => summary,
  })
  assert.equal(await ledger.save({}), false)
  assert.equal(ledger.state.uncertainWrite, true)
  assert.equal(await ledger.save({}), false)
  assert.equal(posts, 1)
  assert.equal(await ledger.refresh(), false)
  assert.equal(ledger.state.uncertainWrite, true)
  readsFail = false
  assert.equal(await ledger.refresh(), true)
  assert.equal(ledger.state.uncertainWrite, false)
  assert.match(ledger.state.notice.message, /核对明细/)
})

test('server field errors are retained without rendering raw payloads', async () => {
  const ledger = createLedger({ create: async () => { throw new ApiError('请求参数不合法', { details: [{ field: 'body.amount', message: '金额无效' }] }) } })
  assert.equal(await ledger.save({}), false)
  assert.deepEqual(ledger.state.fieldErrors, { amount: '金额无效' })
  assert.equal(ledger.state.notice.tone, 'error')
})

test('request error handling distinguishes network uncertainty, known failures and cancellation', () => {
  assert.equal(normalizeApiError({ code: 'ECONNABORTED' }, { write: true }).uncertain, true)
  assert.equal(normalizeApiError({ name: 'AbortError' }).canceled, true)
  const error = normalizeApiError({ response: { status: 422, data: { error: { code: 'VALIDATION_ERROR', message: '请求参数不合法', details: [] } } } }, { write: true })
  assert.equal(error.uncertain, false)
  assert.equal(error.message, '请求参数不合法')
})

test('POST 500/503 responses conservatively require refresh before retrying', () => {
  for (const status of [500, 503]) {
    const response = { status, data: { error: { code: 'DATABASE_UNAVAILABLE', message: '数据库不可用', details: [] } } }
    const writeError = normalizeApiError({ response }, { write: true })
    assert.equal(writeError.uncertain, true)
    assert.match(writeError.message, /刷新核对/)
    const readError = normalizeApiError({ response })
    assert.equal(readError.uncertain, false)
    assert.equal(readError.message, '数据库不可用')
  }
})

test('dispose prevents late network responses from committing', async () => {
  const pending = deferred()
  const ledger = createLedger({ list: () => pending.promise, summary: async () => summary })
  const request = ledger.refresh()
  ledger.dispose()
  pending.resolve(records)
  assert.equal(await request, false)
  assert.equal(ledger.state.snapshot, null)
})
