<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { init, use } from 'echarts/core'
import { PieChart } from 'echarts/charts'
import { TooltipComponent } from 'echarts/components'
import { SVGRenderer } from 'echarts/renderers'
import { expenseChartOption, categoryColors } from '../utils/chart.js'
import { formatMoney } from '../utils/money.js'
import AppIcon from './AppIcon.vue'

use([PieChart, TooltipComponent, SVGRenderer])
const props = defineProps({ summary: { type: Object, default: null }, stale: Boolean, filtered: Boolean })
const categories = computed(() => props.summary?.expense_by_category || [])
const container = ref(null)
let chart
let observer
let disposed = false

async function draw() {
  await nextTick()
  if (disposed) return
  if (!container.value || !categories.value.length) {
    observer?.disconnect()
    chart?.dispose()
    chart = null
    return
  }
  if (!chart) {
    chart = init(container.value, null, { renderer: 'svg' })
    observer = new ResizeObserver(() => chart?.resize())
    observer.observe(container.value)
  }
  chart.setOption(expenseChartOption(categories.value), { notMerge: true })
  chart.resize()
}
watch(() => props.summary, draw, { flush: 'post' })
onMounted(draw)
onBeforeUnmount(() => { disposed = true; observer?.disconnect(); chart?.dispose() })
</script>

<template>
  <section id="analysis" class="panel expense-panel" aria-labelledby="chart-title">
    <div class="panel-heading"><span class="section-icon"><AppIcon name="chart" /></span><div><h2 id="chart-title">支出分类</h2><p>{{ stale ? '当前为上次同步结果' : filtered ? '当前筛选范围内的支出分布' : '看看每一笔，花在了哪里' }}</p></div></div>
    <div v-if="!summary" class="chart-empty">{{ stale ? '统计暂未同步，请重新同步账本。' : '正在等待支出统计。' }}</div>
    <div v-else-if="!categories.length" class="chart-empty"><AppIcon name="leaf" /><strong>暂无支出</strong><span>{{ filtered ? '当前筛选范围内没有支出记录' : '记录一笔支出后，这里会呈现分类分布' }}</span></div>
    <div v-else class="chart-content"><div class="donut-wrap"><div ref="container" class="expense-chart" role="img" :aria-label="`支出分类占比图，共 ${categories.length} 个分类，详细金额见下方列表`" /><div class="donut-center"><p class="chart-total-label">支出合计</p><p class="chart-total">¥{{ formatMoney(summary.total_expense) }}</p></div></div><ul class="chart-legend" aria-label="支出分类金额"><li v-for="(item, index) in categories" :key="item.category"><span class="legend-dot" :style="{ background: categoryColors[index % categoryColors.length] }" /><span class="chart-category">{{ item.category }}</span><strong>¥{{ formatMoney(item.amount) }}</strong></li></ul></div>
  </section>
</template>
