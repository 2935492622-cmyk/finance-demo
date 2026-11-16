import { formatMoney } from './money.js'

export function expenseChartOption(categories) {
  return {
    animation: false,
    color: ['#416f52', '#8aa784', '#b4be8a', '#d4be8e', '#b9876a', '#83989b', '#a0a6c0'],
    tooltip: {
      trigger: 'item',
      renderMode: 'richText',
      confine: true,
      formatter: (item) => `${item.data.name}\n¥${formatMoney(item.data.exactAmount)}`,
    },
    series: [{
      name: '支出分类', type: 'pie', radius: ['54%', '78%'], center: ['50%', '50%'],
      avoidLabelOverlap: true,
      itemStyle: { borderRadius: 4, borderColor: '#fffefa', borderWidth: 3 },
      label: { show: false },
      emphasis: { scale: true, scaleSize: 5 },
      data: categories.map((item) => ({
        name: item.category,
        value: Number(item.amount), // Approximate geometry only; no accounting calculations.
        exactAmount: item.amount,
      })),
    }],
  }
}
