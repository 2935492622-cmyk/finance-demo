import axios from 'axios'

export const client = axios.create({ baseURL: '/api', timeout: 12000 })

export class ApiError extends Error {
  constructor(message, { details = [], uncertain = false, canceled = false } = {}) {
    super(message)
    this.name = 'ApiError'
    this.details = details
    this.uncertain = uncertain
    this.canceled = canceled
  }
}

export function normalizeApiError(error, { write = false, action = '保存' } = {}) {
  if (error instanceof ApiError) return error
  if (axios.isCancel(error) || error?.name === 'AbortError') {
    return new ApiError('请求已取消', { canceled: true })
  }
  // A 5xx can be returned after a commit whose acknowledgement was lost.
  // Avoid suggesting an immediate duplicate POST even if the server responded.
  const uncertain = write && (!error?.response || error.response.status >= 500)
  if (uncertain) {
    return new ApiError(`${action}结果尚未确认，请先刷新核对记录，再决定是否重试。`, { uncertain: true })
  }
  const payload = error?.response?.data?.error
  const details = Array.isArray(payload?.details)
    ? payload.details.filter((item) => typeof item?.field === 'string' && typeof item?.message === 'string')
    : []
  const message = typeof payload?.message === 'string'
    ? payload.message
    : write ? '暂时无法保存记录，请检查输入和服务连接。' : '暂时无法读取账本，请检查服务连接后重试。'
  return new ApiError(message, { details })
}
