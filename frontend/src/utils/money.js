export function normalizeAmount(value) {
  if (typeof value !== 'string' || !/^(0|[1-9][0-9]{0,7})(\.[0-9]{1,2})?$/.test(value)) {
    throw new Error('请输入有效金额，最多 8 位整数、2 位小数')
  }
  const [whole, fraction = ''] = value.split('.')
  const normalized = `${whole}.${fraction.padEnd(2, '0')}`
  if (normalized === '0.00') throw new Error('金额必须大于 0')
  return normalized
}

// Format server-provided decimal text without converting to floating point.
export function formatMoney(value) {
  if (typeof value !== 'string' || !/^-?[0-9]+\.[0-9]{2}$/.test(value)) return '—'
  const [whole, fraction] = value.split('.')
  return `${whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}.${fraction}`
}
