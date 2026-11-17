import { formatMoney } from './money.js'

// Keep aggregation in integer cents; Number is used only by the chart renderer.
export function buildBalanceTrend(items) {
  const daily = new Map()
  for (const item of items) {
    const cents = BigInt(item.amount.replace('.', ''))
    const delta = item.type === 'income' ? cents : -cents
    daily.set(item.transaction_date, (daily.get(item.transaction_date) || 0n) + delta)
  }
  let balance = 0n
  return [...daily].sort(([left], [right]) => left.localeCompare(right)).map(([date, delta]) => {
    balance += delta
    const absolute = balance < 0n ? -balance : balance
    const exactAmount = `${balance < 0n ? '-' : ''}${absolute / 100n}.${String(absolute % 100n).padStart(2, '0')}`
    return { date, exactAmount }
  })
}

export function balanceTrendOption(points) {
  return {
    animation: false,
    grid: { top: 24, right: 20, bottom: 28, left: 64 },
    tooltip: {
      trigger: 'item', renderMode: 'richText', confine: true,
      formatter: (item) => `${item.data.date}\n累计结余 ¥${formatMoney(item.data.exactAmount)}`,
    },
    xAxis: {
      type: 'category', boundaryGap: points.length === 1, data: points.map((point) => point.date),
      axisLine: { lineStyle: { color: '#e9ece7' } }, axisTick: { show: false },
      axisLabel: { color: '#879085', fontSize: 10, margin: 14, formatter: (date) => date.slice(5).replace('-', '/') },
    },
    yAxis: {
      type: 'value', splitNumber: 4,
      splitLine: { lineStyle: { color: '#e9ece7', type: 'dashed' } },
      axisLabel: { color: '#879085', fontSize: 10, formatter: (value) => {
        const absolute = Math.abs(value)
        return absolute >= 10000 ? `${+(value / 10000).toFixed(1)}万` : absolute >= 1000 ? `${+(value / 1000).toFixed(1)}k` : value
      } },
    },
    series: [{
      name: '累计结余', type: 'line', smooth: false, symbol: 'circle', symbolSize: 7,
      showSymbol: points.length <= 10, lineStyle: { color: '#596d90', width: 2 },
      itemStyle: { color: '#596d90', borderColor: '#ffffff', borderWidth: 2 },
      areaStyle: { color: '#eef1f7', opacity: 0.55 },
      data: points.map((point) => ({ ...point, value: Number(point.exactAmount) })),
    }],
  }
}
