// Independent QA checks of the actual frontend error utility; not E2E persistence evidence.
import assert from 'node:assert/strict'
import { normalizeApiError } from '../frontend/src/api/client.js'

for (const status of [500, 503]) {
  const error = normalizeApiError({ response: { status, data: { error: { message: '测试服务错误', details: [] } } } }, { write: true })
  assert.equal(error.uncertain, true)
  assert.match(error.message, /保存结果尚未确认/)
}
assert.equal(normalizeApiError(new Error('network failure'), { write: true }).uncertain, true)
const validation = normalizeApiError({ response: { status: 422, data: { error: {
  message: '请求参数不合法', details: [{ field: 'body.amount', message: '金额错误' }],
} } } }, { write: true })
assert.equal(validation.uncertain, false)
assert.deepEqual(validation.details, [{ field: 'body.amount', message: '金额错误' }])
const readFailure = normalizeApiError({ response: { status: 503, data: { error: { message: '数据库暂不可用', details: [] } } } })
assert.equal(readFailure.uncertain, false)
assert.equal(readFailure.message, '数据库暂不可用')
console.log('QA client error utility: 500/503/network writes unconfirmed, 422 fields preserved, reads not write-locked: PASS')
