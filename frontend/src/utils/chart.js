import { formatMoney } from './money.js'

export const categoryColors = ['#2b9d90', '#d9b86b', '#9c9bc6', '#cd8b70', '#779b6a', '#789eaf', '#c58da5']

export function expenseChartOption(categories) {
  return {
    animation: false,
    color: categoryColors,
    tooltip: {
      trigger: 'item',
      renderMode: 'richText',
      confine: true,
      formatter: (item) => `${item.data.name}\n¥${formatMoney(item.data.exactAmount)}`,
    },
    series: [{
      name: '支出分类', type: 'pie', radius: ['70%', '88%'], center: ['50%', '50%'],
      avoidLabelOverlap: true,
      itemStyle: { borderRadius: 5, borderColor: '#ffffff', borderWidth: 3 },
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
