import { normalizeAmount } from './money.js'
import { isValidDate } from './date.js'

export function validateTransaction(form) {
  const errors = {}
  let amount
  try { amount = normalizeAmount(form.amount) } catch (error) { errors.amount = error.message }
  if (!['income', 'expense'].includes(form.type)) errors.type = '请选择收入或支出'
  const category = typeof form.category === 'string' ? form.category.trim() : ''
  const note = typeof form.note === 'string' ? form.note.trim() : ''
  if (!category || [...category].length > 50) errors.category = '分类需要 1～50 个字符'
  if ([...note].length > 500) errors.note = '备注最多 500 个字符'
  if (!isValidDate(form.transaction_date)) errors.transaction_date = '请选择有效的记账日期'
  return {
    errors,
    value: Object.keys(errors).length ? null : {
      amount, type: form.type, category, note, transaction_date: form.transaction_date,
    },
  }
}
