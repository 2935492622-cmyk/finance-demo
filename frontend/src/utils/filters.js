import { isValidDate } from './date.js'

export const FILTER_KEYS = ['type', 'category', 'start_date', 'end_date']

export function filterParams(filters = {}) {
  return Object.fromEntries(FILTER_KEYS
    .filter((key) => typeof filters[key] === 'string' && filters[key] !== '')
    .map((key) => [key, filters[key]]))
}

export function validateFilters(draft) {
  const value = filterParams({ ...draft, category: (draft.category || '').trim() })
  const errors = {}
  if (value.type && !['income', 'expense'].includes(value.type)) errors.type = '请选择有效类型'
  if (value.category && [...value.category].length > 50) errors.category = '分类最多 50 个字符'
  for (const key of ['start_date', 'end_date']) {
    if (value[key] && !isValidDate(value[key])) errors[key] = '请选择有效日期'
  }
  if (!errors.start_date && !errors.end_date && value.start_date && value.end_date && value.start_date > value.end_date) {
    errors.start_date = '开始日期不能晚于结束日期'
  }
  return { errors, value: Object.keys(errors).length ? null : value }
}

export function transactionPayload(record) {
  return {
    amount: record.amount,
    type: record.type,
    category: record.category,
    note: record.note ?? '',
    transaction_date: record.transaction_date,
  }
}
