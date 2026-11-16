import { client, ApiError, normalizeApiError } from './client.js'
import { filterParams, transactionPayload } from '../utils/filters.js'

export const transactionsApi = {
  async list({ signal, filters } = {}) {
    try {
      const { data } = await client.get('/transactions', { signal, params: filterParams(filters) })
      if (!Array.isArray(data?.items) || data.total !== data.items.length) {
        throw new ApiError('账本响应格式异常，请重新同步。')
      }
      return data
    } catch (error) { throw normalizeApiError(error) }
  },
  async summary({ signal, filters } = {}) {
    try {
      const { data } = await client.get('/summary', { signal, params: filterParams(filters) })
      if (!['total_income', 'total_expense', 'balance'].every((key) => typeof data?.[key] === 'string')) {
        throw new ApiError('统计响应格式异常，请重新同步。')
      }
      return data
    } catch (error) { throw normalizeApiError(error) }
  },
  async create(payload) {
    try {
      const { data, status } = await client.post('/transactions', transactionPayload(payload))
      if (status !== 201 || !Number.isInteger(data?.id)) {
        throw new ApiError('保存结果尚未确认，请先刷新核对记录，再决定是否重试。', { uncertain: true })
      }
      return data
    } catch (error) { throw normalizeApiError(error, { write: true }) }
  },
  async update(id, payload) {
    try {
      const { data, status } = await client.put(`/transactions/${id}`, transactionPayload(payload))
      if (status !== 200 || data?.id !== id) {
        throw new ApiError('保存结果尚未确认，请先刷新核对记录，再决定是否重试。', { uncertain: true })
      }
      return data
    } catch (error) { throw normalizeApiError(error, { write: true }) }
  },
  async remove(id) {
    try {
      const response = await client.delete(`/transactions/${id}`)
      // A successful DELETE is deliberately not parsed as a JSON document.
      if (response.status !== 204) {
        throw new ApiError('删除结果尚未确认，请先刷新核对记录，再决定是否重试。', { uncertain: true })
      }
    } catch (error) { throw normalizeApiError(error, { write: true, action: '删除' }) }
  },
}
